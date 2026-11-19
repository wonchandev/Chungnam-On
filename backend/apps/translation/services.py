import hashlib
import json
import logging
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.module_loading import import_string

from .chat_text import expand_abbreviations, mark_emoticons
from .errors import TranslationProviderError
from .glossary import mark_terms, restore_terms
from .models import TranslationCache

logger = logging.getLogger(__name__)
CACHE_VERSION = 2


def get_translator():
    return import_string(settings.TRANSLATION_BACKEND)()


def detect_source_language(text: str, fallback: str) -> str:
    """감지할 수 없는 입력과 서비스 미지원 언어에는 지정한 기본값을 쓴다."""
    if not any(char.isalpha() for char in text):
        return fallback
    try:
        detected = get_translator().detect_language(text)
    except Exception as error:
        logger.warning("Language detection failed (%s)", type(error).__name__)
        return fallback
    if not isinstance(detected, str):
        return fallback
    language = detected.strip().lower().replace("_", "-").split("-", 1)[0]
    return language if language in settings.SUPPORTED_LANGUAGES else fallback


def translate_text(text: str, source: str, target: str, *, chat: bool = False) -> str:
    """번역 + DB 캐시. 같은 언어이거나 빈 문자열이면 원문을 그대로 반환."""
    return translate_batch([text], source, target, chat=chat)[0]


def translate_batch(texts: list[str], source: str, target: str, *, chat: bool = False) -> list[str]:
    """한 대상 언어로 묶어 번역한다. 빈 입력과 캐시가 있는 문장은 외부 요청에서 제외한다."""
    if source == target:
        return list(texts)
    normalized = [unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")) for text in texts]
    unique_texts = dict.fromkeys(text for text in normalized if text.strip())
    if not unique_texts:
        return list(texts)

    backend = settings.TRANSLATION_BACKEND
    model = settings.OPENAI_TRANSLATE_MODEL if backend == "apps.translation.backends.OpenAITranslator" else None
    cache_days = settings.TRANSLATION_CACHE_TTL_DAYS
    is_echo = backend == "apps.translation.backends.EchoTranslator"
    use_glossary = source in {"ko", "auto"} and not is_echo
    prepared = {}
    for text in unique_texts:
        provider_text = expand_abbreviations(text, source) if chat and not is_echo else text
        marked, terms = mark_terms(provider_text, target) if use_glossary else (provider_text, {})
        if chat and not is_echo:
            marked, emoticons = mark_emoticons(marked)
            terms.update(emoticons)
        prepared_input = [marked, terms] if marked != text or terms else None
        cache_input = json.dumps([CACHE_VERSION, backend, model, source, target, text, prepared_input], sort_keys=True)
        key = hashlib.sha256(cache_input.encode()).hexdigest()
        prepared[text] = (key, marked, terms)

    cached = {}
    if cache_days > 0:
        cutoff = timezone.now() - timedelta(days=cache_days)
        cached = TranslationCache.objects.filter(created_at__gt=cutoff).in_bulk(
            [item[0] for item in prepared.values()], field_name="key",
        )
    missing = {text: item for text, item in prepared.items() if item[0] not in cached}
    results = {text: cached[item[0]].translated_text for text, item in prepared.items() if item[0] in cached}
    if missing:
        translated = get_translator().translate_batch([item[1] for item in missing.values()], source, target)
        if len(translated) != len(missing) or any(not isinstance(value, str) or not value.strip() for value in translated):
            raise TranslationProviderError("translation_invalid_response")

        rows = []
        for (text, (key, _, terms)), value in zip(missing.items(), translated, strict=True):
            try:
                result = restore_terms(value, terms)
            except ValueError as error:
                raise TranslationProviderError("translation_invalid_response") from error
            results[text] = result
            rows.append(TranslationCache(
                key=key, source_lang=source, target_lang=target, source_text=text, translated_text=result, backend=backend,
            ))
        if cache_days > 0:
            TranslationCache.objects.bulk_create(
                rows, update_conflicts=True, unique_fields=["key"], update_fields=["translated_text", "created_at"],
            )

    return [results.get(key, original) for original, key in zip(texts, normalized, strict=True)]


def translate_many(text: str, source: str, targets, *, chat: bool = False) -> dict:
    """여러 언어로 번역. 실패한 언어는 건너뜀(원문 저장/전송을 막지 않기 위해)."""
    if chat and not any(char.isalpha() for char in text):
        return {}
    out = {}
    for target in set(targets):
        if target == source:
            continue
        try:
            out[target] = translate_text(text, source, target, chat=chat)
        except TranslationProviderError as error:
            logger.warning("Translation %s->%s failed (%s)", source, target, error.get_codes())
        except Exception:  # 외부 API 장애
            logger.exception("translation failed %s->%s", source, target)
    return out
