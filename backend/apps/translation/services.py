import hashlib
import logging

from django.conf import settings
from django.utils.module_loading import import_string

from .models import TranslationCache

logger = logging.getLogger(__name__)


def get_translator():
    return import_string(settings.TRANSLATION_BACKEND)()


def translate_text(text: str, source: str, target: str) -> str:
    """번역 + DB 캐시. 같은 언어이거나 빈 문자열이면 원문을 그대로 반환."""
    if not text or source == target:  # source == 'auto' 는 구글 자동 감지
        return text
    key = hashlib.sha256(f"{source}|{target}|{text}".encode()).hexdigest()
    cached = TranslationCache.objects.filter(key=key).first()
    if cached:
        return cached.translated_text
    translator = get_translator()
    result = translator.translate(text, source, target)
    TranslationCache.objects.get_or_create(
        key=key,
        defaults=dict(
            source_lang=source, target_lang=target, source_text=text, translated_text=result,
            backend=settings.TRANSLATION_BACKEND,
        ),
    )
    return result


def translate_many(text: str, source: str, targets) -> dict:
    """여러 언어로 번역. 실패한 언어는 건너뜀(원문 저장/전송을 막지 않기 위해)."""
    out = {}
    for target in set(targets):
        if target == source:
            continue
        try:
            out[target] = translate_text(text, source, target)
        except Exception:  # 외부 API 장애
            logger.exception("translation failed %s->%s", source, target)
    return out
