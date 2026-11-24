from datetime import datetime
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row


class WorkstationRepository:
    """Data access repository for workstations."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create(
        self,
        id: UUID,
        employee_id: UUID,
        name: str,
        created_at: datetime | None = None,
    ) -> dict:
        query = """
            INSERT INTO workstations (id, employee_id, name, created_at)
            VALUES (%s, %s, %s, COALESCE(%s, NOW()))
            RETURNING id, employee_id, name, created_at, revoked_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (id, employee_id, name, created_at))
            return cur.fetchone()

    def get_by_id(self, id: UUID) -> dict | None:
        query = """
            SELECT id, employee_id, name, created_at, revoked_at
            FROM workstations
            WHERE id = %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (id,))
            return cur.fetchone()

    def list_by_employee_id(self, employee_id: UUID) -> list[dict]:
        query = """
            SELECT id, employee_id, name, created_at, revoked_at
            FROM workstations
            WHERE employee_id = %s
            ORDER BY created_at DESC;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (employee_id,))
            return cur.fetchall()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        query = """
            SELECT id, employee_id, name, created_at, revoked_at
            FROM workstations
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (limit, offset))
            return cur.fetchall()

    def revoke(self, id: UUID, revoked_at: datetime | None = None) -> dict | None:
        """Revoke a workstation by setting revoked_at timestamp."""
        query = """
            UPDATE workstations
            SET revoked_at = COALESCE(%s, NOW())
            WHERE id = %s
            RETURNING id, employee_id, name, created_at, revoked_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (revoked_at, id))
            return cur.fetchone()
