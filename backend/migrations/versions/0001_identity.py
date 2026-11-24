"""0001_identity: employees, workstations, api_tokens

Revision ID: 0001_identity
Revises: 
Create Date: 2026-11-24 16:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_identity"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE employees (
            id UUID PRIMARY KEY,
            external_ref TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            role_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE workstations (
            id UUID PRIMARY KEY,
            employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ NULL
        );

        CREATE TABLE api_tokens (
            id UUID PRIMARY KEY,
            workstation_id UUID NOT NULL REFERENCES workstations(id) ON DELETE CASCADE,
            prefix TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NULL,
            revoked_at TIMESTAMPTZ NULL,
            last_used_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_workstations_employee_id ON workstations(employee_id);
        CREATE INDEX idx_api_tokens_workstation_id ON api_tokens(workstation_id);
        CREATE INDEX idx_api_tokens_prefix ON api_tokens(prefix);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS api_tokens CASCADE;
        DROP TABLE IF EXISTS workstations CASCADE;
        DROP TABLE IF EXISTS employees CASCADE;
        """
    )
