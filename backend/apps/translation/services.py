import hashlib
import logging

from django.conf import settings
from django.utils.module_loading import import_string

from .glossary import mark_terms, restore_terms
from .models import TranslationCache

logger = logging.getLogger(__name__)


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


def translate_text(text: str, source: str, target: str) -> str:
    """번역 + DB 캐시. 같은 언어이거나 빈 문자열이면 원문을 그대로 반환."""
    return translate_batch([text], source, target)[0]


def translate_batch(texts: list[str], source: str, target: str) -> list[str]:
    """한 대상 언어로 묶어 번역한다. 빈 입력과 캐시가 있는 문장은 외부 요청에서 제외한다."""
    if source == target:
        return list(texts)
    unique_texts = dict.fromkeys(text for text in texts if text.strip())
    if not unique_texts:
        return list(texts)

    backend = settings.TRANSLATION_BACKEND
    use_glossary = source in {"ko", "auto"} and backend != "apps.translation.backends.EchoTranslator"
    prepared = {}
    for text in unique_texts:
        marked, terms = mark_terms(text, target) if use_glossary else (text, {})
        cache_input = f"{source}|{target}|{text}"
        if terms:
            cache_input += f"|glossary|{backend}|{list(terms.values())!r}"
        key = hashlib.sha256(cache_input.encode()).hexdigest()
        prepared[text] = (key, marked, terms)

    cached = TranslationCache.objects.in_bulk([item[0] for item in prepared.values()], field_name="key")
    missing = {text: item for text, item in prepared.items() if item[0] not in cached}
    results = {text: cached[item[0]].translated_text for text, item in prepared.items() if item[0] in cached}
    if missing:
        translated = get_translator().translate_batch([item[1] for item in missing.values()], source, target)
        if len(translated) != len(missing) or any(not isinstance(value, str) or not value.strip() for value in translated):
            raise ValueError("Translation backend returned missing or invalid text")

        rows = []
        for (text, (key, _, terms)), value in zip(missing.items(), translated, strict=True):
            result = restore_terms(value, terms)
            results[text] = result
            rows.append(TranslationCache(
                key=key, source_lang=source, target_lang=target, source_text=text, translated_text=result, backend=backend,
            ))
        TranslationCache.objects.bulk_create(rows, ignore_conflicts=True)

    return [results.get(text, text) for text in texts]


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
