# Database Migrations Guide

Alembic manages database migrations for OpenClaw Employee Activity Agent.

## Configuration & Environment
- Migration scripts and templates are in `backend/migrations/`.
- Config file: `backend/alembic.ini`.
- Target connection URL is loaded from `DATABASE_URL` (or `app.config.Settings.database_url`).
- Alembic converts `postgresql://` and `postgres://` to `postgresql+psycopg://` automatically.

## Common Commands

Run commands from the `backend/` directory:

### Apply Migrations (Upgrade)
Upgrade to the latest migration:
```bash
alembic upgrade head
```

Upgrade to a specific revision:
```bash
alembic upgrade <revision_id>
```

### Rollback Migrations (Downgrade)
Revert the most recent migration:
```bash
alembic downgrade -1
```

Revert all migrations:
```bash
alembic downgrade base
```

### Create a New Forward Migration
Generate a new migration script:
```bash
alembic revision -m "description_of_change"
```
*Note: As per architecture rules, migrations are forward-only. Never modify an existing applied migration revision.*

### Check Current Migration Revision
```bash
alembic current
alembic history --verbose
```
