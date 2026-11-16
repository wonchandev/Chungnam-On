from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TranslateRequestSerializer, TranslateResponseSerializer
from .services import detect_source_language, translate_text


class TranslateTextView(APIView):
    """텍스트 번역 (로그인 필요)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TranslateRequestSerializer, responses=TranslateResponseSerializer)
    def post(self, request):
        ser = TranslateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if d["source"] == "auto":
            d["source"] = detect_source_language(d["text"], fallback="auto")
        translated = translate_text(d["text"], d["source"], d["target"])
        return Response({**d, "translated_text": translated})


# ───────── P1: 언어 목록 / 음성·사진 번역 / 표현집 / 언어 교육 ─────────
from django.conf import settings  # noqa: E402
from django.http import HttpResponse  # noqa: E402
from django.shortcuts import get_object_or_404  # noqa: E402
from drf_spectacular.types import OpenApiTypes  # noqa: E402
from drf_spectacular.utils import OpenApiParameter  # noqa: E402
from rest_framework import generics, status  # noqa: E402
from rest_framework.parsers import FormParser, MultiPartParser  # noqa: E402
from rest_framework.renderers import JSONRenderer  # noqa: E402

from apps.core.exceptions import ServiceError  # noqa: E402
from apps.core.i18n import get_request_language  # noqa: E402

from . import audio, google, ocr  # noqa: E402
from .services import translate_batch  # noqa: E402
from .models import CourseEnrollment, LanguageCourse, Phrase  # noqa: E402
from .serializers import CourseSerializer, ImageTranslateSerializer, TextToSpeechSerializer, VoiceTranslateSerializer  # noqa: E402

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
    """음성 번역: 녹음 → 서버 변환(16kHz PCM) → 텍스트(STT) → 번역. Google Speech-to-Text 사용 (API 키 필요).
    webm/ogg/m4a/mp3/wav 등 대부분 형식을 받고, 1분이 넘는 음성은 나눠서 인식한다(기본 5분·25MB 까지)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=VoiceTranslateSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = VoiceTranslateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        limit = audio.max_upload_bytes()
        if d["audio"].size > limit:
            raise ServiceError("file_too_large", f"{limit // (1024 * 1024)}MB 이하의 파일만 가능합니다.", 413)
        transcript, duration = audio.transcribe(d["audio"].read(), d["source"], d["encoding"])
        translated = translate_text(transcript, d["source"], d["target"]) if transcript else ""
        return Response({"transcript": transcript, "source": d["source"], "target": d["target"], "translated_text": translated,
                         "duration_seconds": duration})


class TextToSpeechView(APIView):
    """번역문을 재생할 수 있는 MP3 파일로 반환한다."""
    permission_classes = [permissions.IsAuthenticated]

    def perform_content_negotiation(self, request, force=False):
        # 성공 시 HttpResponse로 고정 MP3를 반환하고, DRF 오류는 JSON으로 렌더링한다.
        renderer = JSONRenderer()
        return renderer, renderer.media_type

    @extend_schema(request=TextToSpeechSerializer, responses={(200, "audio/mpeg"): OpenApiTypes.BINARY})
    def post(self, request):
        serializer = TextToSpeechSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        audio_bytes = google.text_to_speech(**serializer.validated_data)
        return HttpResponse(audio_bytes, content_type="audio/mpeg")


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
        ocr_result = ocr.parse_annotation(google.annotate_image(d["image"].read()))
        detected, regions = ocr_result["text"], ocr_result["regions"]
        # 전체 문장과 영역별 문장을 한 번에 묶어 번역한다 (캐시·중복 제거는 translate_batch 가 처리).
        texts = [detected] + [r["text"] for r in regions]
        translated = translate_batch(texts, d["source"], d["target"]) if detected else [""] * len(texts)
        return Response({
            "detected_text": detected, "source": d["source"], "target": d["target"], "translated_text": translated[0],
            "image_width": ocr_result["image_width"], "image_height": ocr_result["image_height"],
            "regions": [{**r, "translated_text": t} for r, t in zip(regions, translated[1:], strict=True)],
        })


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
