"""0002_ingest: ingest_batches and activity_events

Revision ID: 0002_ingest
Revises: 0001_identity
Create Date: 2026-11-26 13:30:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_ingest"
down_revision: str | None = "0001_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ingest_batches (
            seq BIGSERIAL PRIMARY KEY,
            id UUID NOT NULL UNIQUE,
            workstation_id UUID NOT NULL REFERENCES workstations(id) ON DELETE CASCADE,
            employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            batch_id TEXT NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_count INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'received',
            CONSTRAINT uq_ingest_batches_workstation_batch UNIQUE (workstation_id, batch_id)
        );

        CREATE TABLE activity_events (
            id UUID PRIMARY KEY,
            ingest_batch_id UUID NOT NULL REFERENCES ingest_batches(id) ON DELETE CASCADE,
            employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            event_kind TEXT NOT NULL,
            occurred_at TIMESTAMPTZ NOT NULL,
            duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            subject TEXT NULL,
            container TEXT NULL,
            metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE INDEX idx_activity_events_employee_occurred ON activity_events(employee_id, occurred_at);
        CREATE INDEX idx_activity_events_ingest_batch_id ON activity_events(ingest_batch_id);
        CREATE INDEX idx_ingest_batches_workstation_id ON ingest_batches(workstation_id);
        CREATE INDEX idx_ingest_batches_employee_id ON ingest_batches(employee_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS activity_events CASCADE;
        DROP TABLE IF EXISTS ingest_batches CASCADE;
        """
    )
