import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row

from app.schemas.events import CanonicalEvent


class IngestRepository:
    """Data access repository for ingest_batches and activity_events."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def get_batch_by_workstation_and_batch_id(
        self, workstation_id: UUID, batch_id: str
    ) -> Optional[Dict[str, Any]]:
        query = """
            SELECT seq, id, workstation_id, employee_id, batch_id, received_at, event_count, status
            FROM ingest_batches
            WHERE workstation_id = %s AND batch_id = %s;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (workstation_id, batch_id))
            return cur.fetchone()

    def insert_batch_with_events(
        self,
        batch_record_id: UUID,
        workstation_id: UUID,
        employee_id: UUID,
        batch_id: str,
        events: List[CanonicalEvent],
        received_at: Optional[datetime] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        """Insert ingest_batch and its activity_events in a single transaction.

        If (workstation_id, batch_id) already exists, returns (existing_batch, True) without inserting.
        Otherwise inserts batch and events, returning (new_batch, False).
        """
        with self.conn.transaction():
            existing = self.get_batch_by_workstation_and_batch_id(workstation_id, batch_id)
            if existing:
                return existing, True

            insert_batch_query = """
                INSERT INTO ingest_batches (id, workstation_id, employee_id, batch_id, received_at, event_count, status)
                VALUES (%s, %s, %s, %s, COALESCE(%s, NOW()), %s, 'received')
                ON CONFLICT (workstation_id, batch_id) DO NOTHING
                RETURNING seq, id, workstation_id, employee_id, batch_id, received_at, event_count, status;
            """
            with self.conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    insert_batch_query,
                    (
                        batch_record_id,
                        workstation_id,
                        employee_id,
                        batch_id,
                        received_at,
                        len(events),
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    # Concurrently inserted
                    existing = self.get_batch_by_workstation_and_batch_id(workstation_id, batch_id)
                    return existing, True

                batch_row = row

                if events:
                    insert_event_query = """
                        INSERT INTO activity_events (
                            id, ingest_batch_id, employee_id, source_type, source_name,
                            event_kind, occurred_at, duration_seconds, subject,
                            container, metrics, attributes
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb);
                    """
                    event_params = [
                        (
                            ev.event_id,
                            batch_record_id,
                            employee_id,
                            ev.source_type,
                            ev.source_name,
                            ev.event_kind,
                            ev.occurred_at,
                            ev.duration_seconds,
                            ev.subject,
                            ev.container,
                            json.dumps(ev.metrics),
                            json.dumps(ev.attributes),
                        )
                        for ev in events
                    ]
                    cur.executemany(insert_event_query, event_params)

                return batch_row, False

    def list_events_by_batch_id(self, ingest_batch_id: UUID) -> List[Dict[str, Any]]:
        query = """
            SELECT id, ingest_batch_id, employee_id, source_type, source_name,
                   event_kind, occurred_at, duration_seconds, subject,
                   container, metrics, attributes
            FROM activity_events
            WHERE ingest_batch_id = %s
            ORDER BY occurred_at ASC;
        """
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (ingest_batch_id,))
            return cur.fetchall()
