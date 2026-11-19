from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import User
from apps.core.i18n import get_request_language
from apps.core.models import Region
from apps.translation.services import translate_text

from .models import Comment, CompanionParticipant, CompanionPost, Post


def localized(request, text: str, source_lang: str) -> str:
    """요청 언어로 번역 (캐시됨). 실패하면 원문."""
    lang = get_request_language(request)
    if lang == source_lang or not text:
        return text
    try:
        return translate_text(text, source_lang, lang)
    except Exception:
        return text


def author_lang(user) -> str:
    return user.preferred_language if user.preferred_language in settings.SUPPORTED_LANGUAGES else "ko"


class AuthorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name")

    class Meta:
        model = User
        fields = ("id", "name", "nationality", "profile_image", "temperature")


class PostListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    region = serializers.SlugRelatedField(slug_field="code", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True, default=None)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ("id", "category", "region", "region_name", "title", "preview", "image", "author",
                  "like_count", "comment_count", "is_liked", "source_lang", "created_at")

    def get_title(self, obj) -> str:
        return localized(self.context["request"], obj.title, obj.source_lang)

    def get_preview(self, obj) -> str:
        return localized(self.context["request"], obj.body[:120], obj.source_lang)

    def get_like_count(self, obj) -> int:
        return getattr(obj, "like_count_ann", None) if hasattr(obj, "like_count_ann") else obj.likes.count()

    def get_comment_count(self, obj) -> int:
        return obj.comment_count_ann if hasattr(obj, "comment_count_ann") else obj.comments.filter(is_hidden=False).count()

    def get_is_liked(self, obj) -> bool:
        return obj.id in self.context.get("liked_ids", ())


class PostDetailSerializer(PostListSerializer):
    body = serializers.SerializerMethodField()
    original_title = serializers.CharField(source="title", read_only=True)
    original_body = serializers.CharField(source="body", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ("body", "original_title", "original_body", "job", "is_mine")

    def get_body(self, obj) -> str:
        return localized(self.context["request"], obj.body, obj.source_lang)

    def get_is_mine(self, obj) -> bool:
        return obj.author_id == self.context["request"].user.id


class PostWriteSerializer(serializers.ModelSerializer):
    region = serializers.SlugRelatedField(
        slug_field="code", queryset=Region.objects.filter(level="sigungu"), required=False, allow_null=True
    )

    class Meta:
        model = Post
        fields = ("id", "category", "region", "title", "body", "image", "job")
        read_only_fields = ("id",)


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    body = serializers.SerializerMethodField()
    original_body = serializers.CharField(source="body", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "body", "original_body", "source_lang", "is_mine", "created_at")

    def get_body(self, obj) -> str:
        return localized(self.context["request"], obj.body, obj.source_lang)

    def get_is_mine(self, obj) -> bool:
        return obj.author_id == self.context["request"].user.id


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=1000)


class CompanionSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    region = serializers.SlugRelatedField(slug_field="code", queryset=Region.objects.filter(level="sigungu"), required=False, allow_null=True)
    job_title = serializers.CharField(source="job.title", read_only=True, default=None)
    participant_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = CompanionPost
        fields = ("id", "title", "body", "author", "job", "job_title", "region", "meet_place", "meet_at",
                  "capacity", "participant_count", "is_joined", "is_mine", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")

    def get_title(self, obj) -> str:
        return localized(self.context["request"], obj.title, obj.source_lang)

    def get_body(self, obj) -> str:
        return localized(self.context["request"], obj.body, obj.source_lang)

    def get_participant_count(self, obj) -> int:
        return len(obj.participants.all())

    def get_is_joined(self, obj) -> bool:
        uid = self.context["request"].user.id
        return any(p.user_id == uid for p in obj.participants.all())

    def get_is_mine(self, obj) -> bool:
        return obj.author_id == self.context["request"].user.id


class CompanionWriteSerializer(serializers.ModelSerializer):
    region = serializers.SlugRelatedField(
        slug_field="code", queryset=Region.objects.filter(level="sigungu"), required=False, allow_null=True
    )
    capacity = serializers.IntegerField(min_value=1, max_value=32767, default=2)

    class Meta:
        model = CompanionPost
        fields = ("title", "body", "job", "region", "meet_place", "meet_at", "capacity")


class ParticipantSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = CompanionParticipant
        fields = ("user", "created_at")
