# Agent Rules (OpenClaw Employee Activity Agent)

Applies to Gemini 3.8 Flash (`low`). Keep answers short and work in small steps.

1. At the start of every session, read `PROGRESS.md`, then `GRAPH_REPORT.md` (in `graphify-out/` if present), before opening any other file.
2. Never scan, read or index `.venv/`, `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`, `.git/`, or `*.log` files.
3. Do one task per prompt. For anything larger than a small change, propose a short plan and wait for approval.
4. Keep diffs minimal: change only what the task needs. No reformatting, renaming or drive-by refactors.
5. Never edit an applied Alembic migration. Add a new revision instead.
6. Do not add or upgrade dependencies without asking. Pin any approved package in `backend/requirements.txt`.
7. Never commit `.env` or secrets. Read config through `pydantic-settings` environment variables.
8. Privacy: never log, store or transmit raw file contents, window titles or credentials. Use synthetic data in tests.
9. Add or update tests with every change and run `pytest` from `backend/` before saying a task is done.
10. Use type hints and keep functions small.
11. If requirements are unclear, ask one concise question instead of guessing.
12. At the end of each task, update `PROGRESS.md` with what changed and what is next.
13. Treat `contracts/` and `fixtures/` as a locked API contract. Change the JSON Schemas, `backend/app/schemas/eval_contract.py`, the fixtures and the contract tests together, and never in a drive-by edit.
