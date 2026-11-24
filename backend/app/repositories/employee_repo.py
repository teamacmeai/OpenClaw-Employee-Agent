from datetime import datetime
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row


class EmployeeRepository:
    """Data access repository for employees."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create(
        self,
        id: UUID,
        external_ref: str,
        display_name: str,
        role_id: str,
        status: str = "active",
        created_at: datetime | None = None,
    ) -> dict:
        query = """
            INSERT INTO employees (id, external_ref, display_name, role_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()))
            RETURNING id, external_ref, display_name, role_id, status, created_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                query,
                (id, external_ref, display_name, role_id, status, created_at),
            )
            return cur.fetchone()

    def get_by_id(self, id: UUID) -> dict | None:
        query = """
            SELECT id, external_ref, display_name, role_id, status, created_at
            FROM employees
            WHERE id = %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (id,))
            return cur.fetchone()

    def get_by_external_ref(self, external_ref: str) -> dict | None:
        query = """
            SELECT id, external_ref, display_name, role_id, status, created_at
            FROM employees
            WHERE external_ref = %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (external_ref,))
            return cur.fetchone()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        query = """
            SELECT id, external_ref, display_name, role_id, status, created_at
            FROM employees
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (limit, offset))
            return cur.fetchall()

    def revoke(self, id: UUID) -> dict | None:
        """Deactivate an employee by setting status to 'revoked'."""
        query = """
            UPDATE employees
            SET status = 'revoked'
            WHERE id = %s
            RETURNING id, external_ref, display_name, role_id, status, created_at;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (id,))
            return cur.fetchone()
