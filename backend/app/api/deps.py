import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings
from app.core.rate_limit import TokenBucketRateLimiter
from app.db.pool import connection
from app.services.auth_service import AuthService, AuthenticationError, DeviceIdentity

logger = logging.getLogger(__name__)

_rate_limiter: TokenBucketRateLimiter | None = None


def get_rate_limiter() -> TokenBucketRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = TokenBucketRateLimiter(rate_per_minute=settings.rate_limit_per_minute)
    return _rate_limiter


def require_device(
    authorization: Annotated[str | None, Header()] = None,
    rate_limiter: Annotated[TokenBucketRateLimiter, Depends(get_rate_limiter)] = None,
) -> DeviceIdentity:
    """FastAPI dependency requiring valid Bearer device token and enforcing per-workstation rate limit.

    Missing, malformed, invalid, revoked, or expired tokens all return 401 with standard message.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        with connection() as conn:
            service = AuthService(conn)
            identity = service.authenticate(token)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Per-workstation rate limiting
    allowed, retry_after = rate_limiter.check(str(identity.workstation_id))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    return identity
