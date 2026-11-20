from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Return the shared connection pool, creating and opening it on first use.

    The pool is created lazily so the app (and tests that do not touch the
    database) can start without a running PostgreSQL server.
    """
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            open=False,
        )
        _pool.open(wait=False)
    return _pool


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Borrow a connection from the pool for the duration of a `with` block."""
    with get_pool().connection() as conn:
        yield conn


def close_pool() -> None:
    """Close the pool if it was opened. Safe to call more than once."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
