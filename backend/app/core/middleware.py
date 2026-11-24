import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.core.context import set_request_id
from app.core.errors import error_payload

logger = logging.getLogger("app.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every HTTP request has an X-Request-ID and structured audit logs."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        incoming_id = request.headers.get("x-request-id")
        req_id = incoming_id.strip() if incoming_id and incoming_id.strip() else uuid.uuid4().hex
        set_request_id(req_id)
        request.state.request_id = req_id

        settings = get_settings()
        content_length_str = request.headers.get("content-length")
        if content_length_str:
            try:
                content_length = int(content_length_str)
                if content_length > settings.request_max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content=error_payload(
                            "payload_too_large",
                            f"Request body exceeds {settings.request_max_bytes} bytes limit",
                            req_id,
                        ),
                        headers={"X-Request-ID": req_id},
                    )
            except ValueError:
                pass

        start_time = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            # Privacy: log method, path, status, and duration; NEVER log body or headers
            logger.info(
                "%s %s %s %.2fms",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )
            if response is not None:
                response.headers["X-Request-ID"] = req_id
