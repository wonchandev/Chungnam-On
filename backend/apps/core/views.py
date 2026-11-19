from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions

from .models import Region
from .serializers import RegionSerializer


class RegionListView(generics.ListAPIView):
    """지역 목록. `?level=sigungu`, `?parent=44` (상위 코드) 로 필터"""

    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filterset_fields = ["level"]

    def get_queryset(self):
        qs = Region.objects.select_related("parent")
        parent = self.request.query_params.get("parent")
        if parent:
            qs = qs.filter(parent__code=parent)
        return qs


class RegionSearchView(generics.ListAPIView):
    """지역 검색 자동완성 `?q=천안` (최대 20건)"""

    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    @extend_schema(parameters=[OpenApiParameter("q", str, description="검색어 (한글/영문 지역명)")])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        q = self.request.query_params.get("q", "").strip()
        if not q:
            return Region.objects.none()
        from django.db.models import Q

        return Region.objects.filter(Q(name__icontains=q) | Q(name_en__icontains=q)).select_related("parent")[:20]


# ───────────── 알림 / 신고 / 차단 ─────────────
from django.shortcuts import get_object_or_404  # noqa: E402
from rest_framework import status  # noqa: E402

from apps.accounts.models import User  # noqa: E402

from .exceptions import ServiceError  # noqa: E402
from .models import Block, Notification, Report  # noqa: E402
from .serializers import BlockSerializer, NotificationSerializer, ReportSerializer  # noqa: E402


class NotificationListView(generics.ListAPIView):
    """알림 목록. `?unread=true` 로 안 읽은 것만"""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") in ("1", "true", "True"):
            qs = qs.filter(is_read=False)
        return qs


class UnreadCountView(generics.GenericAPIView):
    """안 읽은 알림 수 (🔔 뱃지)"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        from rest_framework.response import Response

        return Response({"unread_count": Notification.objects.filter(user=request.user, is_read=False).count()})


class NotificationReadView(generics.GenericAPIView):
    """POST /notifications/{id}/read/ · POST /notifications/read-all/"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk=None):
        from rest_framework.response import Response

        qs = Notification.objects.filter(user=request.user)
        if pk is not None:
            get_object_or_404(qs, pk=pk)
            qs = qs.filter(pk=pk)
        qs.update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportCreateView(generics.ListCreateAPIView):
    """내 신고 목록 / 신고 접수. 같은 대상 중복 신고는 409."""

    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Report.objects.none()
        return Report.objects.filter(reporter=self.request.user).order_by("-created_at", "-id")

    def perform_create(self, serializer):
        d = serializer.validated_data
        if Report.objects.filter(reporter=self.request.user, target_type=d["target_type"], target_id=d["target_id"]).exists():
            raise ServiceError("already_reported", "이미 신고한 대상입니다.", 409)
        serializer.save(reporter=self.request.user)


class BlockListView(generics.ListAPIView):
    """내가 차단한 유저 목록"""

    serializer_class = BlockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        return Block.objects.filter(blocker=self.request.user).select_related("blocked").order_by("-created_at", "-id")


class BlockView(generics.GenericAPIView):
    """POST: 차단 · DELETE: 차단 해제 (둘 다 멱등)"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BlockSerializer

    @extend_schema(request=None, responses={204: None})
    def post(self, request, user_id):
        from rest_framework.response import Response

        if user_id == request.user.id:
            raise ServiceError("self_block", "자기 자신은 차단할 수 없습니다.")
        Block.objects.get_or_create(blocker=request.user, blocked=get_object_or_404(User, pk=user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={204: None})
    def delete(self, request, user_id):
        from rest_framework.response import Response

        Block.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
