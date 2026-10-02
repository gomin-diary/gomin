from collections.abc import Mapping

from app.schemas.response import ErrorDetail

HTTP_ERRORS = {
    400: ("BAD_REQUEST", "요청을 확인해 주세요."),
    401: ("UNAUTHORIZED", "로그인이 필요합니다."),
    403: ("FORBIDDEN", "접근 권한이 없습니다."),
    404: ("NOT_FOUND", "요청한 대상을 찾을 수 없습니다."),
    405: ("METHOD_NOT_ALLOWED", "허용되지 않은 요청 방식입니다."),
    409: ("CONFLICT", "요청이 현재 상태와 충돌합니다."),
    422: ("VALIDATION_ERROR", "입력값을 확인해 주세요."),
    429: ("RATE_LIMITED", "잠시 후 다시 요청해 주세요."),
    500: ("INTERNAL_ERROR", "요청 처리 중 오류가 발생했습니다."),
    503: ("SERVICE_UNAVAILABLE", "서비스를 일시적으로 이용할 수 없습니다."),
}


class AppError(Exception):
    """Explicit public error; message and details must contain only safe text."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: list[ErrorDetail] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if not 400 <= status_code <= 599:
            raise ValueError("AppError requires a 4xx or 5xx status")
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        self.headers = headers
