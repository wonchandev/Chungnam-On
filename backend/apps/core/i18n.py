"""요청 언어 결정: Accept-Language 헤더 → 로그인 사용자의 preferred_language → 기본값"""
from django.conf import settings


def _from_header(header: str):
    for part in header.split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag:
            continue
        for candidate in (tag, tag.split("-")[0]):
            if candidate in settings.SUPPORTED_LANGUAGES:
                return candidate
    return None


def get_request_language(request) -> str:
    lang = _from_header(request.headers.get("Accept-Language", ""))
    if lang:
        return lang
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.preferred_language in settings.SUPPORTED_LANGUAGES:
        return user.preferred_language
    return settings.DEFAULT_LANGUAGE
