from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import User

from apps.translation.serializers import LANGUAGE_CHOICES

from . import presence
from .models import ChatRoom, Message


class MessageSerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("id", "room", "sender", "text", "image", "source_lang", "translations", "created_at")

    def get_translations(self, obj) -> dict:
        return {t.lang: t.text for t in obj.translations.all()}


class MessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    image = serializers.ImageField(required=False, help_text="이미지 첨부 (multipart)")

    def validate(self, a):
        if not a.get("text", "").strip() and not a.get("image"):
            raise serializers.ValidationError("text 또는 image 가 필요합니다.")
        return a


class RoomCreateSerializer(serializers.Serializer):
    job_id = serializers.IntegerField(required=False, help_text="공고 문의: 공고 사업주와 채팅방 생성/반환")
    user_id = serializers.IntegerField(required=False, help_text="직접 대화(친구 등)")

    def validate(self, a):
        if bool(a.get("job_id")) == bool(a.get("user_id")):
            raise serializers.ValidationError("job_id 또는 user_id 중 하나만 보내세요.")
        return a


class TranslationSettingSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES)


class CounterpartSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name")
    is_online = serializers.SerializerMethodField()
    is_employer = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name", "profile_image", "is_employer", "preferred_language", "temperature", "is_online")

    def get_is_online(self, obj):
        return presence.is_online(obj.id)

    def get_is_employer(self, obj):
        return obj.role == "employer"


class RoomSerializer(serializers.ModelSerializer):
    """최근 대화 목록 항목"""

    counterpart = serializers.SerializerMethodField()
    job = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    my_language = serializers.SerializerMethodField()
    counterpart_language = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ("id", "job", "counterpart", "last_message", "last_message_at", "unread_count",
                  "my_language", "counterpart_language", "created_at")

    def _mine_other(self, obj):
        me = self.context["request"].user
        parts = {p.user_id: p for p in obj.participants.all()}
        other = next((p for uid, p in parts.items() if uid != me.id), None)
        return parts.get(me.id), other

    def get_counterpart(self, obj) -> dict | None:
        _, other = self._mine_other(obj)
        return CounterpartSerializer(other.user, context=self.context).data if other else None

    def get_job(self, obj) -> dict | None:
        return {"id": obj.job_id, "title": obj.job.title} if obj.job_id else None

    def get_last_message(self, obj) -> dict | None:
        msg = obj.messages.order_by("-id").first()
        return MessageSerializer(msg).data if msg else None

    def get_unread_count(self, obj) -> int:
        mine, _ = self._mine_other(obj)
        qs = obj.messages.exclude(sender=self.context["request"].user)
        if mine and mine.last_read_at:
            qs = qs.filter(created_at__gt=mine.last_read_at)
        return qs.count()

    def get_my_language(self, obj) -> str | None:
        mine, _ = self._mine_other(obj)
        return mine.language if mine else None

    def get_counterpart_language(self, obj) -> str | None:
        _, other = self._mine_other(obj)
        return other.language if other else None


class QuickReplySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField(help_text="요청 언어로 번역된 문장 (그대로 전송하면 상대 언어로 다시 번역됨)")
    text_ko = serializers.CharField()
