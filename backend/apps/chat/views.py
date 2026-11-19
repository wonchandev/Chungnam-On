from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.exceptions import ServiceError
from apps.jobs.models import JobPost

from .models import ChatParticipant, ChatRoom, Message, QuickReply
from .serializers import (
    MessageCreateSerializer, MessageSerializer, QuickReplySerializer, RoomCreateSerializer, RoomSerializer,
    TranslationSettingSerializer,
)
from .services import broadcast, get_or_create_room, send_message


class MessageCursorPagination(CursorPagination):
    page_size = 30
    ordering = "-id"  # 최신부터, next 로 과거 이력을 불러옴


def my_rooms(user, include_left=False):
    qs = ChatRoom.objects.filter(participants__user=user)
    if not include_left:
        qs = qs.filter(participants__user=user, participants__left_at__isnull=True)
    return qs.distinct().prefetch_related("participants__user__company").select_related("job")


def get_my_room(request, pk):
    return get_object_or_404(my_rooms(request.user), pk=pk)


class RoomListCreateView(generics.ListCreateAPIView):
    """GET: 최근 대화 목록(안읽음 수 포함) · POST: 문의하기 → 채팅방 생성/기존 방 반환"""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends: list = []

    def get_serializer_class(self):
        return RoomCreateSerializer if self.request.method == "POST" else RoomSerializer

    def get_queryset(self):
        return my_rooms(self.request.user)

    @extend_schema(request=RoomCreateSerializer, responses={200: RoomSerializer, 201: RoomSerializer})
    def post(self, request, *args, **kwargs):
        ser = RoomCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        job = None
        if d.get("job_id"):
            job = get_object_or_404(JobPost.objects.select_related("company__owner"), pk=d["job_id"])
            other = job.company.owner
        else:
            other = get_object_or_404(User, pk=d["user_id"])
        if other == request.user:
            raise ServiceError("self_chat", "자기 자신과는 대화할 수 없습니다.")
        existed = ChatRoom.objects.filter(job=job, participants__user=request.user).filter(participants__user=other).exists()
        room = get_or_create_room(request.user, other, job)
        room = my_rooms(request.user).get(pk=room.pk)
        return Response(RoomSerializer(room, context={"request": request}).data,
                        status=status.HTTP_200_OK if existed else status.HTTP_201_CREATED)


class RoomDetailView(generics.RetrieveDestroyAPIView):
    """GET: 채팅방 정보 (상대방, 온라인 여부, 번역 언어) · DELETE: 채팅방 나가기 (내 목록에서만 숨김, 상대가 새 메시지를 보내면 다시 나타남)"""

    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return my_rooms(self.request.user)

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        ChatParticipant.objects.filter(room=room, user=request.user).update(left_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListCreateView(generics.ListCreateAPIView):
    """GET: 메시지 이력 (원문 + 번역본, 커서 페이지네이션, 최신순) · POST: 메시지 전송 (WebSocket 대체 수단)"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessageCursorPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends: list = []

    def get_serializer_class(self):
        return MessageCreateSerializer if self.request.method == "POST" else MessageSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Message.objects.none()
        room = get_my_room(self.request, self.kwargs["pk"])
        return room.messages.prefetch_related("translations")

    @extend_schema(request=MessageCreateSerializer, responses={201: MessageSerializer})
    def post(self, request, pk):
        room = get_my_room(request, pk)
        ser = MessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        msg = send_message(room, request.user, d.get("text", "").strip(), d.get("image"))
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class RoomReadView(APIView):
    """읽음 처리"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        room = get_my_room(request, pk)
        now = timezone.now()
        ChatParticipant.objects.filter(room=room, user=request.user).update(last_read_at=now)
        broadcast(room.id, {"type": "chat.read", "user": request.user.id, "read_at": now.isoformat()})
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomTranslationView(APIView):
    """내가 이 방에서 사용하는 번역 언어 설정 (예: 한국어↔태국어 → 내 언어를 th 로)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TranslationSettingSerializer, responses=RoomSerializer)
    def patch(self, request, pk):
        room = get_my_room(request, pk)
        ser = TranslationSettingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ChatParticipant.objects.filter(room=room, user=request.user).update(language=ser.validated_data["language"])
        room = my_rooms(request.user).get(pk=room.pk)
        return Response(RoomSerializer(room, context={"request": request}).data)


class QuickReplyListView(APIView):
    """추천 단어/빠른 문장 (요청 언어로 번역해서 제공)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=QuickReplySerializer(many=True))
    def get(self, request):
        from apps.core.i18n import get_request_language
        from apps.translation.services import translate_text

        lang = get_request_language(request)
        out = []
        for q in QuickReply.objects.all():
            try:
                text = translate_text(q.text_ko, "ko", lang)
            except Exception:
                text = q.text_ko
            out.append({"id": q.id, "text": text, "text_ko": q.text_ko})
        return Response(out)


class RoomCallView(APIView):
    """전화 연결: 해당 공고에 **승인된 지원**이 있는 방에서만 상대 전화번호를 알려준다 (번호 노출 정책)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        from apps.jobs.models import Application

        room = get_my_room(request, pk)
        other = room.participants.exclude(user=request.user).select_related("user").first()
        if not other:
            raise ServiceError("not_found", "상대를 찾을 수 없습니다.", 404)
        allowed = bool(room.job_id) and Application.objects.filter(
            job_id=room.job_id, status=Application.Status.APPROVED, applicant__in=[request.user, other.user]
        ).exists()
        if not allowed:
            raise ServiceError("call_not_allowed", "지원이 승인된 후에 전화 연결이 가능합니다.", 403)
        if not other.user.phone:
            raise ServiceError("no_phone", "상대방이 전화번호를 등록하지 않았습니다.", 404)
        return Response({"phone": other.user.phone})
