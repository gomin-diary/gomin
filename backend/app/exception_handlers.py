import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from app.errors import AppError, HTTP_ERRORS
from app.schemas.response import ApiError, ApiFailure, ErrorDetail
from app.validation_error_paths import safe_validation_path

logger = logging.getLogger(__name__)

# Declare the same error contract in OpenAPI as the handlers return at runtime.
ERROR_RESPONSES = {
    status: {"model": ApiFailure, "description": code}
    for status, (code, _) in HTTP_ERRORS.items()
}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = ApiFailure(error=ApiError(code=exc.code, message=exc.message, details=exc.details))
    return JSONResponse(body.model_dump(mode="json"), status_code=exc.status_code, headers=exc.headers)


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code, message = HTTP_ERRORS.get(
        exc.status_code,
        ("INTERNAL_ERROR", "요청 처리 중 오류가 발생했습니다.")
        if exc.status_code >= 500 else ("HTTP_ERROR", "요청을 처리할 수 없습니다."),
    )
    # HTTPException.detail is not assumed safe to expose.
    return await app_error_handler(request, AppError(exc.status_code, code, message, headers=exc.headers))


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        error_type = error["type"]
        if error_type == "missing":
            code, message = "REQUIRED", "필수 입력값입니다."
        elif error_type.endswith(("_parsing", "_type")) or error_type == "json_invalid":
            code, message = "INVALID_FORMAT", "입력 형식이 올바르지 않습니다."
        else:
            code, message = "INVALID_VALUE", "입력값이 올바르지 않습니다."
        # Never echo input, ctx, or Pydantic's message (custom validators may include input).
        details.append(ErrorDetail(path=safe_validation_path(request, error["loc"]), code=code, message=message))
    return await app_error_handler(request, AppError(422, "VALIDATION_ERROR", "입력값을 확인해 주세요.", details=details))


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled API exception: %s", type(exc).__name__)
    return await app_error_handler(request, AppError(500, "INTERNAL_ERROR", "요청 처리 중 오류가 발생했습니다."))


async def api_error_boundary(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Registered inside CORS so unexpected errors also get the CORS headers.
    # Successful responses are never rewritten by this boundary.
    try:
        return await call_next(request)
    except Exception as exc:
        return await internal_error_handler(request, exc)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.middleware("http")(api_error_boundary)
