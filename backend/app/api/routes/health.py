import logging

from fastapi import APIRouter, HTTPException
import psycopg

from app.db.pool import connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Basic service health check."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db() -> dict[str, str]:
    """Database connectivity health check."""
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return {"status": "ok", "database": "connected"}
    except (psycopg.Error, Exception) as exc:
        logger.warning("Database health check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from exc
