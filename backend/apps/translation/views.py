from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TranslateRequestSerializer, TranslateResponseSerializer
from .services import translate_text


class TranslateTextView(APIView):
    """텍스트 번역 (로그인 필요)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TranslateRequestSerializer, responses=TranslateResponseSerializer)
    def post(self, request):
        ser = TranslateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        translated = translate_text(d["text"], d["source"], d["target"])
        return Response({**d, "translated_text": translated})


# ───────── P1: 언어 목록 / 음성·사진 번역 / 표현집 / 언어 교육 ─────────
from django.conf import settings  # noqa: E402
from django.shortcuts import get_object_or_404  # noqa: E402
from drf_spectacular.types import OpenApiTypes  # noqa: E402
from drf_spectacular.utils import OpenApiParameter  # noqa: E402
from rest_framework import generics, status  # noqa: E402
from rest_framework.parsers import FormParser, MultiPartParser  # noqa: E402

from apps.core.exceptions import ServiceError  # noqa: E402
from apps.core.i18n import get_request_language  # noqa: E402

from . import google  # noqa: E402
from .models import CourseEnrollment, LanguageCourse, Phrase  # noqa: E402
from .serializers import CourseSerializer, ImageTranslateSerializer, VoiceTranslateSerializer  # noqa: E402

LANGUAGE_NAMES = {
    "ko": ("한국어", "Korean"), "en": ("English", "English"), "vi": ("Tiếng Việt", "Vietnamese"),
    "th": ("ภาษาไทย", "Thai"), "zh": ("中文", "Chinese"), "uz": ("Oʻzbekcha", "Uzbek"),
    "km": ("ភាសាខ្មែរ", "Khmer"), "ne": ("नेपाली", "Nepali"), "id": ("Bahasa Indonesia", "Indonesian"),
    "mn": ("Монгол", "Mongolian"),
}


class LanguageListView(APIView):
    """서비스 지원 언어 목록"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response([{"code": c, "native_name": LANGUAGE_NAMES[c][0], "name": LANGUAGE_NAMES[c][1]}
                         for c in settings.SUPPORTED_LANGUAGES])


MAX_UPLOAD = 10 * 1024 * 1024


class VoiceTranslateView(APIView):
    """음성 번역: 녹음 → 텍스트(STT) → 번역. Google Speech-to-Text 사용 (API 키 필요)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=VoiceTranslateSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = VoiceTranslateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        audio = d["audio"]
        if audio.size > MAX_UPLOAD:
            raise ServiceError("file_too_large", "10MB 이하의 파일만 가능합니다.", 413)
        transcript = google.speech_to_text(audio.read(), d["source"], d["encoding"])
        translated = translate_text(transcript, d["source"], d["target"]) if transcript else ""
        return Response({"transcript": transcript, "source": d["source"], "target": d["target"], "translated_text": translated})


class ImageTranslateView(APIView):
    """사진 번역: 사진 속 글자(OCR) → 번역. Google Vision 사용 (API 키 필요)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=ImageTranslateSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = ImageTranslateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if d["image"].size > MAX_UPLOAD:
            raise ServiceError("file_too_large", "10MB 이하의 파일만 가능합니다.", 413)
        detected = google.image_to_text(d["image"].read())
        translated = translate_text(detected, d["source"], d["target"]) if detected else ""
        return Response({"detected_text": detected, "source": d["source"], "target": d["target"], "translated_text": translated})


class PhraseListView(APIView):
    """자주 쓰는 현장 표현. `?category=safety&q=안전` (q 는 한국어 원문 검색). 요청 언어로 번역해서 제공(캐시)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(parameters=[OpenApiParameter("category", str), OpenApiParameter("q", str)], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        lang = get_request_language(request)
        qs = Phrase.objects.all()
        if request.query_params.get("category"):
            qs = qs.filter(category=request.query_params["category"])
        if request.query_params.get("q"):
            qs = qs.filter(text_ko__icontains=request.query_params["q"])
        out = []
        for p in qs:
            try:
                text = translate_text(p.text_ko, "ko", lang)
            except Exception:
                text = p.text_ko
            out.append({"id": p.id, "category": p.category, "category_label": p.get_category_display(),
                        "text_ko": p.text_ko, "text": text, "language": lang})
        return Response(out)


class CourseListView(generics.ListAPIView):
    """무료 언어 교육 목록"""

    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends: list = []

    def get_queryset(self):
        return LanguageCourse.objects.filter(is_active=True).prefetch_related("enrollments")


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return LanguageCourse.objects.filter(is_active=True).prefetch_related("enrollments")


class CourseEnrollView(APIView):
    """POST: 신청하기 (정원/중복 검증) · DELETE: 신청 취소"""

    permission_classes = [permissions.IsAuthenticated]

    def _ser(self, request, pk):
        c = LanguageCourse.objects.prefetch_related("enrollments").get(pk=pk)
        return CourseSerializer(c, context={"request": request}).data

    @extend_schema(request=None, responses={201: CourseSerializer})
    def post(self, request, pk):
        course = get_object_or_404(LanguageCourse, pk=pk, is_active=True)
        if course.capacity is not None and course.enrollments.count() >= course.capacity:
            raise ServiceError("course_full", "정원이 마감되었습니다.", 409)
        _, created = CourseEnrollment.objects.get_or_create(course=course, user=request.user)
        if not created:
            raise ServiceError("already_enrolled", "이미 신청한 교육입니다.", 409)
        return Response(self._ser(request, pk), status=status.HTTP_201_CREATED)

    @extend_schema(responses=CourseSerializer)
    def delete(self, request, pk):
        CourseEnrollment.objects.filter(course_id=pk, user=request.user).delete()
        return Response(self._ser(request, pk))


class MyCourseListView(generics.ListAPIView):
    """내 신청 내역"""

    serializer_class = CourseSerializer
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LanguageCourse.objects.none()
        return LanguageCourse.objects.filter(enrollments__user=self.request.user).prefetch_related("enrollments")
