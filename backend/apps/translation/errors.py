from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import ceil

from apps.core.exceptions import ServiceError


class TranslationProviderError(ServiceError):
    """번역 공급자 오류를 API 응답과 워커 재시도에 공통으로 사용한다."""

    ERRORS = {
        "translation_timeout": (504, True, "번역 서비스 응답 시간이 초과되었습니다."),
        "translation_rate_limited": (503, True, "번역 요청이 몰리고 있습니다. 잠시 후 다시 시도해주세요."),
        "translation_unavailable": (503, True, "번역 서비스를 일시적으로 사용할 수 없습니다."),
        "translation_quota_exhausted": (503, False, "번역 서비스 사용 한도에 도달했습니다."),
        "translation_provider_error": (502, False, "외부 번역 서비스 호출에 실패했습니다."),
        "translation_invalid_response": (502, False, "번역 서비스에서 유효한 응답을 받지 못했습니다."),
    }

    def __init__(self, code: str, retry_after: str | None = None):
        status, self.retryable, message = self.ERRORS[code]
        self.wait = _retry_after_seconds(retry_after) if self.retryable else None
        super().__init__(code, message, status)


def _retry_after_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        seconds = int(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (ValueError, OverflowError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        seconds = ceil((when - datetime.now(UTC)).total_seconds())
    return max(0, seconds) if seconds <= 365 * 86400 else None


def classify_http_error(status: int, reasons, retry_after: str | None) -> TranslationProviderError:
    """공급자의 단기 요청 제한과 운영자가 해결해야 하는 한도 초과를 구분한다."""
    reasons = {reason for reason in reasons if isinstance(reason, str)}
    if reasons & {
        "Daily Limit Exceeded", "dailyLimitExceeded", "insufficient_quota", "billing_hard_limit_reached",
        "organization_spend_limit_exceeded", "project_spend_limit_exceeded", "organization_usage_limit_exceeded",
    }:
        return TranslationProviderError("translation_quota_exhausted")
    if status == 429 or reasons & {"User Rate Limit Exceeded", "userRateLimitExceeded", "rateLimitExceeded"}:
        return TranslationProviderError("translation_rate_limited", retry_after)
    if status in {408, 504}:
        return TranslationProviderError("translation_timeout", retry_after)
    if 500 <= status < 600:
        return TranslationProviderError("translation_unavailable", retry_after)
    return TranslationProviderError("translation_provider_error")
