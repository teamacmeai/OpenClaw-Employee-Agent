# Progress

Alembic Head: 0001_identity
Locked Contracts: eval_request v1.0, eval_response v1.0

## Current phase
PH-02: Alembic setup and identity schema (Completed, pending user verification)

## PH-02 Summary
- **Status:** Completed
- **What was built:** Alembic setup (`alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`), forward migration `0001_identity` (`employees`, `workstations`, `api_tokens` tables and indexes), psycopg `dict_row` repositories (`EmployeeRepository`, `WorkstationRepository`, `TokenRepository`), migration test runner & table cleanup fixtures in `conftest.py`, repository test suite (`test_repositories.py`), and `docs/MIGRATIONS.md`.
- **Key files:**
  - `backend/alembic.ini` & `backend/migrations/env.py`: Alembic runner reading database URL
  - `backend/migrations/versions/0001_identity.py`: DDL for identity schema tables and indexes
  - `backend/app/repositories/`: `employee_repo.py`, `workstation_repo.py`, `token_repo.py`
  - `backend/tests/`: `conftest.py` (session migration runner & truncate cleanup), `test_repositories.py`
  - `docs/MIGRATIONS.md`: Migration upgrade/downgrade and revision guide
- **Interfaces / Tables:** Tables `employees`, `workstations`, `api_tokens`
- **New environment variables:** None (`DATABASE_URL` and `TEST_DATABASE_URL` reused)
- **Verification commands:** `alembic upgrade head`, `alembic downgrade -1`, `pytest tests/test_repositories.py` (from `backend/`)
- **Assumptions and open questions:** None; DB tests skip gracefully when `TEST_DATABASE_URL` is unset and run against migrated DB when set.
- **Notes for next phase:** Ready for PH-03 (Device authentication, token hashing, rate limiting, and admin CLI).

## PH-01 Summary
- **Status:** Completed
- **What was built:** Package layout, request-ID propagation/generation middleware, privacy-safe audit logging, unified error format (`{"error": {"code", "message", "request_id"}}`), `/health` and `/health/db` endpoints, settings extension, and pytest setup with client and `db` marker.
- **Key files:**
  - `backend/app/api/router.py` & `backend/app/api/routes/health.py`: Router aggregation and health checks
  - `backend/app/core/`: `context.py`, `logging.py`, `middleware.py`, `errors.py`
  - `backend/app/config.py`: Added `app_env`, `log_level`, `request_max_bytes`
  - `backend/tests/conftest.py` & `pyproject.toml`: `client`, `db_conn` fixtures and `db` marker registration
  - `backend/tests/test_health.py` & `backend/tests/test_core.py`: Route, error handling, and middleware test suites
- **Interfaces / Routes:** `GET /health`, `GET /health/db`, `X-Request-ID` request/response header, standard error payload
- **New environment variables:** `APP_ENV`, `LOG_LEVEL`, `REQUEST_MAX_BYTES`, `TEST_DATABASE_URL` (optional, for db tests)
- **Verification commands:** `pytest` (from `backend/`), `curl -i http://localhost:8000/health`, `curl -i http://localhost:8000/health/db`
- **Assumptions and open questions:** None; DB tests gracefully skip if `TEST_DATABASE_URL` is unset.
- **Notes for next phase:** Ready for PH-02 (Alembic initialization, identity tables migration, and psycopg repositories).

## Done
- Repo guardrails: .gitignore, .graphifyignore, AGENTS.md
- Backend tooling files: requirements.txt, pyproject.toml
- Backend skeleton: config, DB pool, /health endpoint and test
- Evaluation contract v1.0: contracts/, Pydantic models, fixtures/sample_payloads.json, contract tests
- PH-01: Package layout, core logging/middleware/errors, /health/db, and test harness
- PH-02: Alembic setup, 0001_identity migration, psycopg repositories, and tests

## Next
- PH-03: Device authentication and provisioning

## Decisions
- (record decisions D1-D6 here)
