# Progress

Alembic Head: 0001_identity
Locked Contracts: eval_request v1.0, eval_response v1.0

## Current phase
PH-04: Canonical events and source adapters (Completed, pending user verification)

## PH-04 Summary
- **Status:** Completed
- **What was built:** Canonical event schemas (`CanonicalEvent`, `RawEvent`, `IngestBatch`), `SourceAdapter` protocol, `AdapterRegistry`, `GenericAdapter` supporting all required event kinds (`file_change`, `commit`, `command_run`, `browser_activity`, `idle_block`, `session_start`, `session_end`), example adapters (`FileActivityAdapter`, `AppFocusAdapter`), prefix/regex `ContainerResolver` driven by `config/container_rules.json`, redaction utilities for sensitive subjects and secret attribute scrubbing, 3-source fixture batches in `fixtures/ingest_batches.json`, and comprehensive test suite `tests/test_adapters.py`.
- **Key files:**
  - `backend/app/schemas/events.py`: Canonical and raw event models
  - `backend/app/adapters/`: `base.py`, `generic.py`, `file_activity.py`, `app_focus.py`, `__init__.py`
  - `backend/app/core/`: `containers.py`, `redaction.py`
  - `config/container_rules.json`: Ordered prefix/regex container mapping rules
  - `fixtures/ingest_batches.json`: 3 fixture batches across 3 tool categories
  - `backend/tests/test_adapters.py`: Normalization, redaction, container, registry, and fixture tests
- **Interfaces / Routes / Tables:** `CanonicalEvent`, `IngestBatch`, `SourceAdapter`, `AdapterRegistry` (no database or API routes in this phase)
- **New environment variables:** None
- **Verification commands:** `pytest tests/test_adapters.py` (from `backend/`)
- **Assumptions and open questions:** None; events cleanly normalize across all specified kinds with allow-listed attributes.
- **Notes for next phase:** Ready for PH-05 (Ingest API and event storage).

## PH-03 Summary
- **Status:** Completed
- **What was built:** Device token generation and SHA-256 verification (`ocl_<prefix>_<secret>`), `AuthService` validating active/unexpired workstation tokens with throttled `last_used_at` updates, `require_device` FastAPI dependency with identical 401s, per-workstation token bucket rate limiter with 429 response & `Retry-After`, admin CLI commands (`register-employee`, `register-workstation`, `issue-token`, `revoke-token`, `list-tokens`), `GET /v1/device/whoami` endpoint, and tests for auth, rate limiting, CLI, and endpoint.
- **Key files:**
  - `backend/app/core/security.py`: Token generation, SHA-256 hashing, constant-time verification
  - `backend/app/core/rate_limit.py`: In-memory thread-safe token bucket rate limiter
  - `backend/app/services/auth_service.py`: `AuthService` resolving `DeviceIdentity`
  - `backend/app/api/deps.py`: `require_device` dependency and rate limit enforcement
  - `backend/app/api/routes/device.py` & `backend/app/api/router.py`: `GET /v1/device/whoami`
  - `backend/app/cli.py`: Admin CLI for employee/workstation registration & token management
  - `backend/tests/`: `test_auth.py`, `test_device_api.py`, `test_cli.py`
- **Interfaces / Routes:** `GET /v1/device/whoami`, `Authorization: Bearer <token>` header, `RATE_LIMIT_PER_MINUTE` setting
- **New environment variables:** `RATE_LIMIT_PER_MINUTE` (default 60)
- **Verification commands:** `pytest` (from `backend/`), `python -m app.cli --help`, `curl -H "Authorization: Bearer <token>" http://localhost:8000/v1/device/whoami`
- **Assumptions and open questions:** None; DB tests run against migrated database when `TEST_DATABASE_URL` is set, non-db tests run standalone.
- **Notes for next phase:** Ready for PH-04 (Canonical events and source adapters).

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

## Next
- PH-05: Ingest API and event storage

## Decisions
- (record decisions D1-D6 here)
