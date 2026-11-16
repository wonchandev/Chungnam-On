from rest_framework import serializers

from apps.core.i18n import get_request_language

from .models import AdminGuide


class GuideListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = AdminGuide
        fields = ("id", "category", "category_label", "title", "summary", "view_count", "updated_at")

    def _t(self, obj):
        lang = self.context.setdefault("lang", get_request_language(self.context["request"]))
        if lang == "ko":
            return None
        return next((t for t in obj.translations.all() if t.lang == lang), None)

    def get_title(self, obj) -> str:
        t = self._t(obj)
        return t.title if t else obj.title

    def get_summary(self, obj) -> str:
        t = self._t(obj)
        return t.summary if t else obj.summary


class GuideDetailSerializer(GuideListSerializer):
    body = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()

    class Meta(GuideListSerializer.Meta):
        fields = GuideListSerializer.Meta.fields + ("body", "source_url", "language")

    def get_body(self, obj) -> str:
        t = self._t(obj)
        return t.body if t else obj.body

    def get_language(self, obj) -> str:
        return "ko" if self._t(obj) is None else self.context["lang"]


from django.conf import settings  # noqa: E402

from .models import ChatTurn, Complaint, Conversation  # noqa: E402


class ComplaintSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = ("id", "category", "category_label", "title", "body", "status", "status_label", "answer", "answered_at", "created_at")
        read_only_fields = ("id", "status", "answer", "answered_at", "created_at")


class AssistantChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    conversation_id = serializers.IntegerField(required=False, help_text="이어갈 대화 (없으면 새 대화)")
    stream = serializers.BooleanField(default=False, help_text="true 면 SSE(text/event-stream)로 스트리밍")


class ChatTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatTurn
        fields = ("id", "role", "text", "sources", "feedback", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ("id", "title", "language", "created_at", "updated_at")


class DocumentRequestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["visa_extension_reason", "employment_certificate_request", "absence_notice"])
    fields = serializers.DictField(child=serializers.CharField(allow_blank=True), help_text="템플릿별 입력값 (GET templates 참고)")


class TurnFeedbackSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(choices=["up", "down"], required=False)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)
    report = serializers.BooleanField(required=False, help_text="true 면 부적절한 답변으로 신고")
