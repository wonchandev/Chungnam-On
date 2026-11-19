from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ServiceError
from apps.core.services import blocked_user_ids, notify

from .models import Comment, CompanionParticipant, CompanionPost, Post, PostLike
from .serializers import (
    CommentCreateSerializer, CommentSerializer, CompanionSerializer, ParticipantSerializer,
    PostDetailSerializer, PostListSerializer, PostWriteSerializer, CompanionWriteSerializer, author_lang,
)

PARSERS = [JSONParser, MultiPartParser, FormParser]


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or obj.author_id == request.user.id


def visible_posts(request):
    qs = Post.objects.filter(is_hidden=False)
    blocked = blocked_user_ids(request.user)
    return qs.exclude(author_id__in=blocked) if blocked else qs


class PostCtxMixin:
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        u = self.request.user
        ctx["liked_ids"] = set(PostLike.objects.filter(user=u).values_list("post_id", flat=True)) if u.is_authenticated else set()
        return ctx


class PostListCreateView(PostCtxMixin, generics.ListCreateAPIView):
    """지역 커뮤니티 글 목록/작성. `?region=44130&category=review&q=키워드&mine=true&job=ID`. 제목/본문은 요청 언어로 자동 번역."""

    parser_classes = PARSERS
    filterset_fields = ["category"]
    ordering_fields = ["created_at"]

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.request.method == "POST" else [permissions.AllowAny()]

    def get_serializer_class(self):
        return PostWriteSerializer if self.request.method == "POST" else PostListSerializer

    def get_queryset(self):
        qs = visible_posts(self.request).select_related("author", "region").annotate(
            like_count_ann=Count("likes", distinct=True),
            comment_count_ann=Count("comments", filter=Q(comments__is_hidden=False), distinct=True),
        ).order_by("-created_at", "-id")
        p = self.request.query_params
        if p.get("region"):
            qs = qs.filter(region__code=p["region"])
        if p.get("job"):
            qs = qs.filter(job_id=p["job"])
        if p.get("q"):
            qs = qs.filter(Q(title__icontains=p["q"]) | Q(body__icontains=p["q"]))
        if p.get("mine") in ("1", "true") and self.request.user.is_authenticated:
            qs = qs.filter(author=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        ser = PostWriteSerializer(data=request.data, context=self.get_serializer_context())
        ser.is_valid(raise_exception=True)
        post = ser.save(author=request.user, source_lang=author_lang(request.user))
        return Response(PostDetailSerializer(post, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)


class PostDetailView(PostCtxMixin, generics.RetrieveUpdateDestroyAPIView):
    parser_classes = PARSERS
    permission_classes = [IsAuthorOrReadOnly]

    def get_permissions(self):
        return [IsAuthorOrReadOnly()] if self.request.method not in permissions.SAFE_METHODS else [permissions.AllowAny()]

    def get_queryset(self):
        return visible_posts(self.request).select_related("author", "region")

    def get_serializer_class(self):
        return PostDetailSerializer if self.request.method == "GET" else PostWriteSerializer

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and not request.user.is_authenticated:
            self.permission_denied(request)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        ser = PostWriteSerializer(post, data=request.data, partial=True, context=self.get_serializer_context())
        ser.is_valid(raise_exception=True)
        ser.save(source_lang=author_lang(request.user))
        return Response(PostDetailSerializer(post, context=self.get_serializer_context()).data)


class PostLikeView(APIView):
    """POST: 좋아요 · DELETE: 취소 (멱등)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        PostLike.objects.get_or_create(post=get_object_or_404(visible_posts(request), pk=pk), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        PostLike.objects.filter(post_id=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentListCreateView(generics.ListCreateAPIView):
    """댓글 목록/작성 (요청 언어로 자동 번역)"""

    filter_backends: list = []

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.request.method == "POST" else [permissions.AllowAny()]

    def get_serializer_class(self):
        return CommentCreateSerializer if self.request.method == "POST" else CommentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comment.objects.none()
        post = get_object_or_404(visible_posts(self.request), pk=self.kwargs["pk"])
        qs = post.comments.filter(is_hidden=False).select_related("author")
        blocked = blocked_user_ids(self.request.user)
        return qs.exclude(author_id__in=blocked) if blocked else qs

    @extend_schema(request=CommentCreateSerializer, responses={201: CommentSerializer})
    def post(self, request, pk):
        post = get_object_or_404(visible_posts(request), pk=pk)
        ser = CommentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        c = Comment.objects.create(post=post, author=request.user, body=ser.validated_data["body"], source_lang=author_lang(request.user))
        if post.author_id != request.user.id:
            notify(post.author, "comment", "내 글에 새 댓글이 달렸어요", c.body[:100], post_id=post.id)
        return Response(CommentSerializer(c, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CommentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        deleted, _ = Comment.objects.filter(pk=pk, author=request.user).delete()
        if not deleted:
            raise ServiceError("not_found", "댓글을 찾을 수 없습니다.", 404)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────── 동행 모집 ─────────
class CompanionListCreateView(generics.ListCreateAPIView):
    """함께 일하러 갈 동료 모집. `?region=&job=&status=open`"""

    serializer_class = CompanionSerializer
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "meet_at"]

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.request.method == "POST" else [permissions.AllowAny()]

    def get_queryset(self):
        qs = CompanionPost.objects.filter(is_hidden=False).select_related("author", "job", "region").prefetch_related("participants")
        blocked = blocked_user_ids(self.request.user)
        if blocked:
            qs = qs.exclude(author_id__in=blocked)
        p = self.request.query_params
        if p.get("region"):
            qs = qs.filter(region__code=p["region"])
        if p.get("job"):
            qs = qs.filter(job_id=p["job"])
        return qs

    @extend_schema(request=CompanionWriteSerializer, responses={201: CompanionSerializer})
    def create(self, request, *args, **kwargs):
        serializer = CompanionWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user, source_lang=author_lang(request.user))
        return Response(CompanionSerializer(post, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)


class CompanionDetailView(generics.RetrieveDestroyAPIView):
    """동행 상세 / 삭제(작성자)"""

    serializer_class = CompanionSerializer

    def get_permissions(self):
        return [IsAuthorOrReadOnly()] if self.request.method not in permissions.SAFE_METHODS else [permissions.AllowAny()]

    def get_queryset(self):
        return CompanionPost.objects.filter(is_hidden=False).select_related("author", "job", "region").prefetch_related("participants__user")

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and not request.user.is_authenticated:
            self.permission_denied(request)


class CompanionJoinView(APIView):
    """POST: 참여 · DELETE: 참여 취소. 정원이 차면 자동 마감."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: CompanionSerializer})
    def post(self, request, pk):
        post = get_object_or_404(CompanionPost.objects.filter(is_hidden=False), pk=pk)
        if post.author_id == request.user.id:
            raise ServiceError("own_post", "내가 만든 모집에는 참여할 수 없습니다.")
        if post.status != CompanionPost.Status.OPEN:
            raise ServiceError("closed", "마감된 모집입니다.", 409)
        _, created = CompanionParticipant.objects.get_or_create(post=post, user=request.user)
        if created:
            if post.participants.count() >= post.capacity:
                post.status = CompanionPost.Status.CLOSED
                post.save(update_fields=["status"])
            notify(post.author, "companion", "동행 모집에 새 참여자가 생겼어요", post.title, companion_id=post.id)
        return Response(self._ser(request, pk))

    @extend_schema(responses={200: CompanionSerializer})
    def delete(self, request, pk):
        post = get_object_or_404(CompanionPost, pk=pk)
        CompanionParticipant.objects.filter(post=post, user=request.user).delete()
        if post.status == CompanionPost.Status.CLOSED and post.participants.count() < post.capacity:
            post.status = CompanionPost.Status.OPEN
            post.save(update_fields=["status"])
        return Response(self._ser(request, pk))

    def _ser(self, request, pk):
        post = CompanionPost.objects.select_related("author", "job", "region").prefetch_related("participants").get(pk=pk)
        return CompanionSerializer(post, context={"request": request}).data


class CompanionParticipantListView(generics.ListAPIView):
    """참여자 목록 (작성자/참여자만 열람)"""

    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CompanionParticipant.objects.none()
        post = get_object_or_404(CompanionPost, pk=self.kwargs["pk"])
        u = self.request.user
        if post.author_id != u.id and not post.participants.filter(user=u).exists():
            raise ServiceError("forbidden", "참여자만 볼 수 있습니다.", 403)
        return post.participants.select_related("user").order_by("id")
