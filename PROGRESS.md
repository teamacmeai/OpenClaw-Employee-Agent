# Progress

Alembic Head: None
Locked Contracts: eval_request v1.0, eval_response v1.0

## Current phase
PH-01: Backend skeleton and conventions (Completed, pending user verification)

## PH-01 Summary
- **Status:** Completed
- **What was built:** Package layout (`app/api/routes`, `core`, `services`, `repositories`, `adapters`, `clients`, `workers`), request-ID propagation/generation middleware, privacy-safe audit logging, unified error format (`{"error": {"code", "message", "request_id"}}`), `/health` and `/health/db` endpoints, settings extension, and pytest setup with client and `db` marker.
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

## Next
- PH-02: Alembic setup and identity schema

## Decisions
- (record decisions D1-D6 here)
