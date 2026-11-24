from datetime import datetime
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row


class TokenRepository:
    """Data access repository for api_tokens."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create(
        self,
        id: UUID,
        workstation_id: UUID,
        prefix: str,
        token_hash: str,
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> dict:
        query = """
            INSERT INTO api_tokens (id, workstation_id, prefix, token_hash, expires_at, created_at)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()))
            RETURNING id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                query,
                (id, workstation_id, prefix, token_hash, expires_at, created_at),
            )
            return cur.fetchone()

    def get_by_id(self, id: UUID) -> dict | None:
        query = """
            SELECT id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at
            FROM api_tokens
            WHERE id = %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (id,))
            return cur.fetchone()

    def get_by_hash(self, token_hash: str) -> dict | None:
        query = """
            SELECT id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at
            FROM api_tokens
            WHERE token_hash = %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (token_hash,))
            return cur.fetchone()

    def list_by_workstation_id(self, workstation_id: UUID) -> list[dict]:
        query = """
            SELECT id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at
            FROM api_tokens
            WHERE workstation_id = %s
            ORDER BY created_at DESC;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (workstation_id,))
            return cur.fetchall()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        query = """
            SELECT id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at
            FROM api_tokens
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (limit, offset))
            return cur.fetchall()

    def revoke(self, id: UUID, revoked_at: datetime | None = None) -> dict | None:
        """Revoke a token by setting revoked_at timestamp."""
        query = """
            UPDATE api_tokens
            SET revoked_at = COALESCE(%s, NOW())
            WHERE id = %s
            RETURNING id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (revoked_at, id))
            return cur.fetchone()

    def update_last_used(self, id: UUID, last_used_at: datetime | None = None) -> dict | None:
        """Update last_used_at timestamp for a token."""
        query = """
            UPDATE api_tokens
            SET last_used_at = COALESCE(%s, NOW())
            WHERE id = %s
            RETURNING id, workstation_id, prefix, token_hash, expires_at, revoked_at, last_used_at, created_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (last_used_at, id))
            return cur.fetchone()
