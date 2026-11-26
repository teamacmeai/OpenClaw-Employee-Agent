# Progress

Alembic Head: 0002_ingest
Locked Contracts: eval_request v1.0, eval_response v1.0

## Current phase
PH-05: Ingest API and event storage (Completed, pending user verification)

## PH-05 Summary
- **Status:** Completed
- **What was built:** Migration `0002_ingest` (`ingest_batches` and `activity_events` with indexing), `IngestRepository` with atomic transactional insertion & deduplication, `IngestService` performing adapter normalization, container resolution, and subject/attribute redaction with per-event rejection handling, `POST /v1/ingest` endpoint returning 202 with capped rejection list, collector simulation script `scripts/simulate_ingest.py`, and test suite covering fixture ingestion, idempotency/duplicates, partial rejection, payload body size limits, and privacy logging.
- **Key files:**
  - `backend/migrations/versions/0002_ingest.py`: Alembic forward migration for batch and event tables
  - `backend/app/repositories/ingest_repo.py`: SQL operations for batches and events
  - `backend/app/services/ingest_service.py`: Normalization, redaction, container, and rejection pipeline
  - `backend/app/api/routes/ingest.py` & `backend/app/api/router.py`: `POST /v1/ingest` route
  - `scripts/simulate_ingest.py`: CLI simulation runner for posting JSON fixture batches
  - `backend/tests/test_ingest.py`: End-to-end ingest, duplicate, rejection, 413, and logging tests
- **Interfaces / Routes / Tables:** `POST /v1/ingest`, tables `ingest_batches`, `activity_events`
- **New environment variables:** None
- **Verification commands:** `alembic upgrade head` (from `backend/`), `pytest tests/test_ingest.py` (from `backend/`), `python scripts/simulate_ingest.py --token <token>`
- **Assumptions and open questions:** None; rejection list is capped at 20 items and re-sent batches return 202 with `duplicate: true`.
- **Notes for next phase:** Ready for PH-06 (Processing pipeline and windows aggregation).

## PH-04 Summary
- **Status:** Completed
- **What was built:** Canonical event schemas, `SourceAdapter` protocol, `AdapterRegistry`, `GenericAdapter`, example adapters, `ContainerResolver`, redaction utilities, and fixture batches.
- **Key files:** `backend/app/schemas/events.py`, `backend/app/adapters/`, `backend/app/core/containers.py`, `backend/app/core/redaction.py`, `fixtures/ingest_batches.json`, `backend/tests/test_adapters.py`.

## PH-03 Summary
- **Status:** Completed
- **What was built:** Device token authentication, rate limiting, admin CLI, and whoami endpoint.
- **Key files:** `backend/app/core/security.py`, `backend/app/core/rate_limit.py`, `backend/app/services/auth_service.py`, `backend/app/api/deps.py`, `backend/app/api/routes/device.py`, `backend/app/cli.py`, `backend/tests/test_auth.py`.

## PH-02 Summary
- **Status:** Completed
- **What was built:** Alembic setup (`0001_identity`), psycopg `dict_row` repositories (`EmployeeRepository`, `WorkstationRepository`, `TokenRepository`), and repository test suite.
- **Key files:** `migrations/versions/0001_identity.py`, `backend/app/repositories/`, `docs/MIGRATIONS.md`.

## PH-01 Summary
- **Status:** Completed
- **What was built:** Layout, request-ID middleware, privacy logging, standard error responses, `/health`, `/health/db`.
- **Key files:** `backend/app/core/`, `backend/app/api/routes/health.py`, `backend/app/config.py`.

## Done
- Repo guardrails: .gitignore, .graphifyignore, AGENTS.md
- Backend tooling files: requirements.txt, pyproject.toml
- Backend skeleton: config, DB pool, /health endpoint and test
- Evaluation contract v1.0: contracts/, Pydantic models, fixtures/sample_payloads.json, contract tests
- PH-01: Package layout, core logging/middleware/errors, /health/db, and test harness
- PH-02: Alembic setup, 0001_identity migration, psycopg repositories, and tests
- PH-03: Device authentication, rate limiting, admin CLI, and whoami endpoint
- PH-04: Canonical events, source adapter protocol and registry, generic & example adapters, redaction, container resolution, and 3-source fixture batches
- PH-05: Ingest API, event storage, duplicate rejection, and simulator script

## Next
- PH-06: Processing pipeline (windows)

## Decisions
- (record decisions D1-D6 here)
