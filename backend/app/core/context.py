from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Retrieve the current active request ID from context."""
    return request_id_ctx.get()


def set_request_id(req_id: str | None) -> None:
    """Set the current active request ID in context."""
    request_id_ctx.set(req_id)
