import logging
import sys

from app.core.context import get_request_id


class RequestIDFilter(logging.Filter):
    """Inject the active request ID into logging records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured console logging.

    Adheres to strict privacy conventions: request bodies, auth headers,
    window titles, and file contents are never logged.
    """
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers on reload
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [req_id:%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIDFilter())
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
            handler.addFilter(RequestIDFilter())
