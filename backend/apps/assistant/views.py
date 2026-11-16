from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.jobs.models import Application, JobPost

from .models import AdminGuide, GuideView
from .serializers import GuideDetailSerializer, GuideListSerializer


class DashboardView(APIView):
    """행정관리 대시보드 통계 (60초 캐시)"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        data = cache.get("admin-info:dashboard")
        if data is None:
            today = timezone.localdate()
            data = {
                "total_workers": User.objects.filter(role=User.Role.WORKER, is_active=True).count(),
                "total_employers": User.objects.filter(role=User.Role.EMPLOYER, is_active=True).count(),
                "open_jobs": JobPost.objects.open().count(),
                "new_jobs_today": JobPost.objects.filter(created_at__date=today).count(),
                "applications_total": Application.objects.count(),
                "guides_total": AdminGuide.objects.filter(is_published=True).count(),
            }
            cache.set("admin-info:dashboard", data, 60)
        return Response(data)


class GuideListView(generics.ListAPIView):
    """행정 정보 목록. `?category=visa|insurance|labor|tax|life|etc`, `?search=키워드` (한국어 원문 기준)"""

    serializer_class = GuideListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["category"]
    ordering_fields = ["created_at", "view_count"]

    def get_queryset(self):
        qs = AdminGuide.objects.filter(is_published=True).prefetch_related("translations")
        q = self.request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q)
                | Q(translations__title__icontains=q) | Q(translations__body__icontains=q)
            ).distinct()
        return qs

    @extend_schema(parameters=[OpenApiParameter("search", str)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class GuideDetailView(generics.RetrieveAPIView):
    """행정 정보 상세 (조회수 증가). Accept-Language 에 맞는 번역본, 없으면 한국어."""

    serializer_class = GuideDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return AdminGuide.objects.filter(is_published=True).prefetch_related("translations")

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        AdminGuide.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
        GuideView.objects.create(guide=obj)
        obj.view_count += 1
        return Response(self.get_serializer(obj).data)


class _TopGuidesView(generics.ListAPIView):
    serializer_class = GuideListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends: list = []

    def limit(self):
        return min(int(self.request.query_params.get("limit", 10) or 10), 50)


class FrequentGuideView(_TopGuidesView):
    """자주 찾는 정보: 누적 조회수 순"""

    def get_queryset(self):
        return AdminGuide.objects.filter(is_published=True).prefetch_related("translations").order_by("-view_count")[: self.limit()]


class PopularGuideView(_TopGuidesView):
    """최근 인기: 최근 7일 조회수 순"""

    def get_queryset(self):
        since = timezone.now() - timedelta(days=7)
        return (
            AdminGuide.objects.filter(is_published=True).prefetch_related("translations")
            .annotate(recent=Count("views", filter=Q(views__created_at__gte=since)))
            .filter(recent__gt=0).order_by("-recent")[: self.limit()]
        )


# ───────── P1: 민원 / AI 챗봇 / 서류 작성 도움 ─────────
from django.http import StreamingHttpResponse  # noqa: E402
from rest_framework import status  # noqa: E402

from apps.core.exceptions import ServiceError  # noqa: E402
from apps.core.i18n import get_request_language  # noqa: E402
from apps.translation.services import translate_text  # noqa: E402

from . import chatbot, documents  # noqa: E402
from .models import ChatTurn, Complaint, Conversation  # noqa: E402
from .serializers import (  # noqa: E402
    AssistantChatRequestSerializer, ChatTurnSerializer, ComplaintSerializer, ConversationSerializer,
    DocumentRequestSerializer, TurnFeedbackSerializer,
)


class ComplaintListCreateView(generics.ListCreateAPIView):
    """민원: 내 민원 목록 / 접수. `?status=received|in_progress|resolved`"""

    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "category"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        return Complaint.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ComplaintDetailView(generics.RetrieveAPIView):
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        return Complaint.objects.filter(user=self.request.user)


class AssistantChatView(APIView):
    """AI 챗봇 질의응답. 행정 가이드를 검색해 근거로 삼고, 요청 언어로 답한다.
    `stream=true` 면 SSE: `data: {"type":"delta","text":"..."}` … 마지막 `{"type":"done","conversation_id","message_id","sources"}`.
    `stream=false` 면 JSON `{conversation_id, message_id, answer, sources, title, suggestions, pii_masked}`.
    하루 질문 한도 초과 시 429 `assistant_rate_limited`."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=AssistantChatRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = AssistantChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        conv = None
        if d.get("conversation_id"):
            conv = get_object_or_404(Conversation, pk=d["conversation_id"], user=request.user)
        lang = get_request_language(request)
        chatbot.check_limit(request.user)
        events = chatbot.run(request.user, d["message"], lang, conv)
        if d["stream"]:
            resp = StreamingHttpResponse(chatbot.sse(events), content_type="text/event-stream")
            resp["Cache-Control"] = "no-cache"
            resp["X-Accel-Buffering"] = "no"
            return resp
        text, done, error = [], {}, None
        for e in events:
            if e["type"] == "delta":
                text.append(e["text"])
            elif e["type"] == "done":
                done = e
            elif e["type"] == "error":
                error = e["message"]
        if error and not text:
            raise ServiceError("assistant_unavailable", error, 503)
        return Response({"conversation_id": done["conversation_id"], "message_id": done["message_id"],
                         "answer": "".join(text), "sources": done["sources"], "title": done["title"],
                         "suggestions": done["suggestions"], "pii_masked": done["pii_masked"]})


class ConversationListView(generics.ListAPIView):
    """내 챗봇 대화 목록"""

    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        return Conversation.objects.filter(user=self.request.user)


class ConversationDetailView(APIView):
    """GET: 대화 내용 · DELETE: 삭제"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        c = get_object_or_404(Conversation, pk=pk, user=request.user)
        return Response({**ConversationSerializer(c).data, "turns": ChatTurnSerializer(c.turns.all(), many=True).data})

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        get_object_or_404(Conversation, pk=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationExportView(APIView):
    """대화 내보내기 (텍스트 파일 다운로드)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, pk):
        from django.http import HttpResponse

        c = get_object_or_404(Conversation, pk=pk, user=request.user)
        lines = [f"# {c.title}", ""]
        for t in c.turns.all():
            lines.append(f"[{'나' if t.role == 'user' else 'AI'}] {t.text}\n")
        resp = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="conversation-{c.id}.txt"'
        return resp


class TurnFeedbackView(APIView):
    """챗봇 답변 피드백(👍/👎 + 사유)과 부적절 답변 신고. 신고는 admin 의 '챗봇 답변' 화면에서 검토."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TurnFeedbackSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        turn = get_object_or_404(ChatTurn, pk=pk, role=ChatTurn.Role.ASSISTANT, conversation__user=request.user)
        ser = TurnFeedbackSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if "rating" in d:
            turn.feedback = d["rating"]
        if "reason" in d:
            turn.feedback_reason = d["reason"]
        if d.get("report"):
            turn.reported = True
        turn.save(update_fields=["feedback", "feedback_reason", "reported"])
        return Response({"id": turn.id, "feedback": turn.feedback, "feedback_reason": turn.feedback_reason, "reported": turn.reported})


class DocumentTemplateListView(APIView):
    """서류 템플릿 목록과 입력 필드"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response([{"type": t.key, "title": t.title, "fields": t.fields} for t in documents.TEMPLATES.values()])


class DocumentDraftView(APIView):
    """서류 초안 생성: 템플릿에 입력값을 채운 한국어 초안 + 요청 언어 번역(이해용). 법적 효력 서식이 아님."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=DocumentRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = DocumentRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from django.utils import timezone

        d = ser.validated_data
        out = documents.render(d["type"], d["fields"], timezone.localdate().strftime("%Y년 %m월 %d일"))
        lang = get_request_language(request)
        try:
            out["body_translated"] = translate_text(out["body_ko"], "ko", lang) if lang != "ko" else None
        except Exception:
            out["body_translated"] = None
        out["language"] = lang
        out["notice"] = "문장 초안입니다. 실제 제출 서식과 요건은 접수 기관(출입국·외국인관서 등)에서 확인하세요."
        return Response(out)
