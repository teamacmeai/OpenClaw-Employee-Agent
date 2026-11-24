import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import get_request_id

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception with explicit error code and status."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def error_payload(code: str, message: str, request_id: str | None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform error response handlers returning {error: {code, message, request_id}}."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        req_id = get_request_id()
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, req_id),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = get_request_id()
        code = "http_error"
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 403:
            code = "forbidden"
        elif exc.status_code == 413:
            code = "payload_too_large"
        elif exc.status_code == 503:
            code = "service_unavailable"

        detail_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, detail_msg, req_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = get_request_id()
        return JSONResponse(
            status_code=422,
            content=error_payload("validation_error", "Request validation failed", req_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        req_id = get_request_id()
        logger.exception("Unhandled server error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_error", "Internal server error", req_id),
        )
