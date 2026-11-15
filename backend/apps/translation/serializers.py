from django.conf import settings
from rest_framework import serializers


LANGUAGE_CHOICES = [(l, l) for l in settings.SUPPORTED_LANGUAGES]
SOURCE_LANGUAGE_CHOICES = LANGUAGE_CHOICES + [("auto", "auto")]


class TranslateRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)
    source = serializers.ChoiceField(choices=SOURCE_LANGUAGE_CHOICES, default="ko", help_text="auto: 자동 감지")
    target = serializers.ChoiceField(choices=LANGUAGE_CHOICES)


class TranslateResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    source = serializers.CharField()
    target = serializers.CharField()
    translated_text = serializers.CharField()


from .models import CourseEnrollment, LanguageCourse  # noqa: E402


class VoiceTranslateSerializer(serializers.Serializer):
    audio = serializers.FileField(help_text="녹음 파일 (약 1분 이내, 10MB 이하)")
    source = serializers.ChoiceField(choices=LANGUAGE_CHOICES, help_text="말하는 언어")
    target = serializers.ChoiceField(choices=LANGUAGE_CHOICES)
    encoding = serializers.ChoiceField(choices=["WEBM_OPUS", "OGG_OPUS", "LINEAR16", "FLAC", "MP3"], default="WEBM_OPUS")


class ImageTranslateSerializer(serializers.Serializer):
    image = serializers.ImageField(help_text="번역할 글자가 있는 사진")
    source = serializers.ChoiceField(choices=SOURCE_LANGUAGE_CHOICES, default="auto", help_text="auto: 자동 감지")
    target = serializers.ChoiceField(choices=LANGUAGE_CHOICES)


class CourseSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = LanguageCourse
        fields = ("id", "title", "description", "taught_language", "kind", "is_free", "capacity",
                  "enrolled_count", "is_enrolled")

    def get_enrolled_count(self, obj) -> int:
        return len(obj.enrollments.all())

    def get_is_enrolled(self, obj) -> bool:
        uid = self.context["request"].user.id
        return any(e.user_id == uid for e in obj.enrollments.all())
