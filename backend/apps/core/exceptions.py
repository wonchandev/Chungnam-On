"""공통 에러 응답 포맷: {"code": str, "message": str, "detail": any}"""
from rest_framework import exceptions
from rest_framework.views import exception_handler

MESSAGES = {
    "validation_error": "입력값이 올바르지 않습니다.",
    "not_authenticated": "로그인이 필요합니다.",
    "authentication_failed": "인증에 실패했습니다.",
    "permission_denied": "권한이 없습니다.",
    "not_found": "대상을 찾을 수 없습니다.",
    "method_not_allowed": "허용되지 않는 요청입니다.",
    "throttled": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.APIException):
        code = exc.get_codes()
        code = code if isinstance(code, str) else "validation_error"
        if isinstance(exc, exceptions.ValidationError):
            code = "validation_error"
    else:  # Http404, PermissionDenied (Django)
        code = {404: "not_found", 403: "permission_denied"}.get(response.status_code, "error")

    detail = response.data
    if isinstance(detail, dict) and set(detail.keys()) == {"detail"}:
        message = str(detail["detail"])
        detail = None
    else:
        message = MESSAGES.get(code, "요청을 처리할 수 없습니다.")
    response.data = {"code": code, "message": message, "detail": detail}
    return response


class ServiceError(exceptions.APIException):
    """비즈니스 규칙 위반 (HTTP 400/409 등). raise ServiceError("code", "메시지", status)"""

    status_code = 400

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(detail=message, code=code)
