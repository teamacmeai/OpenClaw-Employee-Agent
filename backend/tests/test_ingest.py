import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_rate_limiter
from app.core.security import generate_device_token
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.ingest_repo import IngestRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.workstation_repo import WorkstationRepository


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter = get_rate_limiter()
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def test_identity(db_conn):
    """Seed test employee, workstation, and token."""
    emp_repo = EmployeeRepository(db_conn)
    ws_repo = WorkstationRepository(db_conn)
    tok_repo = TokenRepository(db_conn)

    emp_id = uuid4()
    emp_repo.create(id=emp_id, external_ref="emp-ingest-01", display_name="Ingest Tester", role_id="eng")

    ws_id = uuid4()
    ws_repo.create(id=ws_id, employee_id=emp_id, name="tester-ws-1")

    raw_token, prefix, token_hash = generate_device_token()
    tok_repo.create(id=uuid4(), workstation_id=ws_id, prefix=prefix, token_hash=token_hash)

    return {
        "employee_id": emp_id,
        "workstation_id": ws_id,
        "token": raw_token,
    }


@pytest.mark.db
def test_ingest_fixtures_and_duplicate(client: TestClient, db_conn, test_identity):
    """Verify all three fixture batches normalize and insert correctly, and re-sending is duplicate."""
    fixtures_path = Path(__file__).resolve().parent.parent.parent / "fixtures" / "ingest_batches.json"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        batches = json.load(f)

    headers = {"Authorization": f"Bearer {test_identity['token']}"}
    repo = IngestRepository(db_conn)

    for batch in batches:
        batch_id = batch["batch_id"]
        # First ingest
        resp = client.post("/v1/ingest", json=batch, headers=headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["batch_id"] == batch_id
        assert data["duplicate"] is False
        assert data["accepted"] > 0
        if batch_id == "batch-ide-file-001":
            # 1 out of 3 events had .env which is sensitive and dropped
            assert data["accepted"] == 2
            assert len(data["rejected"]) == 1
            assert data["rejected"][0]["index"] == 2
        elif batch_id == "batch-generic-tool-002":
            assert data["accepted"] == 6
            assert len(data["rejected"]) == 0
        elif batch_id == "batch-focus-browser-003":
            assert data["accepted"] == 2
            assert len(data["rejected"]) == 0

        # Duplicate ingest
        dup_resp = client.post("/v1/ingest", json=batch, headers=headers)
        assert dup_resp.status_code == 202
        dup_data = dup_resp.json()
        assert dup_data["batch_id"] == batch_id
        assert dup_data["duplicate"] is True
        assert dup_data["accepted"] == data["accepted"]
        assert len(dup_data["rejected"]) == 0

    # Verify rows in DB
    batch_1 = repo.get_batch_by_workstation_and_batch_id(test_identity["workstation_id"], "batch-ide-file-001")
    assert batch_1 is not None
    events_1 = repo.list_events_by_batch_id(batch_1["id"])
    assert len(events_1) == 2
    # Verify container resolution happened
    assert events_1[0]["container"] == "backend-workspace"
    assert events_1[1]["container"] == "frontend-workspace"


@pytest.mark.db
def test_ingest_partial_rejection(client: TestClient, db_conn, test_identity):
    """Verify unknown sources and sensitive files are rejected per-event while valid ones succeed."""
    batch = {
        "schema_version": "1.0",
        "batch_id": "batch-partial-rejection-test",
        "sent_at": "2026-11-26T12:00:00Z",
        "events": [
            {
                "source_type": "file_activity",
                "source_name": "code-editor",
                "payload": {
                    "file_path": "/repo/backend/app/main.py",
                    "event_kind": "file_change",
                    "occurred_at": "2026-11-26T12:00:00Z",
                    "duration_seconds": 1.0,
                },
            },
            {
                "source_type": "unsupported_unknown_source",
                "source_name": "alien_sensor",
                "payload": {"data": 123},
            },
            {
                "source_type": "file_activity",
                "source_name": "code-editor",
                "payload": {
                    "file_path": "/repo/secret/.env",
                    "event_kind": "file_change",
                    "occurred_at": "2026-11-26T12:01:00Z",
                },
            },
            {
                "source_type": "generic",
                "source_name": "git-vcs",
                "payload": {
                    "event_id": str(uuid4()),
                    "event_kind": "commit",
                    "occurred_at": "2026-11-26T12:02:00Z",
                    "subject": "commit/123",
                    "metrics": {"files_count": 1.0},
                    "attributes": {"branch": "main"},
                },
            },
        ],
    }
    headers = {"Authorization": f"Bearer {test_identity['token']}"}
    resp = client.post("/v1/ingest", json=batch, headers=headers)
    assert resp.status_code == 202
    data = resp.json()
    assert data["batch_id"] == "batch-partial-rejection-test"
    assert data["accepted"] == 2  # event 0 and 3
    assert data["duplicate"] is False
    assert len(data["rejected"]) == 2

    # Check rejection indices
    indices = [r["index"] for r in data["rejected"]]
    assert indices == [1, 2]


@pytest.mark.db
def test_ingest_rejections_capped_at_20(client: TestClient, db_conn, test_identity):
    """Verify rejection reasons list is capped at 20 even if more are rejected."""
    rejected_events = [
        {
            "source_type": f"unknown_source_{i}",
            "source_name": "test",
            "payload": {"data": i},
        }
        for i in range(30)
    ]
    batch = {
        "schema_version": "1.0",
        "batch_id": "batch-capped-rejections-test",
        "sent_at": "2026-11-26T12:00:00Z",
        "events": rejected_events,
    }
    headers = {"Authorization": f"Bearer {test_identity['token']}"}
    resp = client.post("/v1/ingest", json=batch, headers=headers)
    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted"] == 0
    assert len(data["rejected"]) == 20  # capped at 20


def test_ingest_payload_too_large(client: TestClient, test_identity):
    """Verify oversized request body returns 413 payload_too_large."""
    huge_data = "x" * (1_048_576 + 100)
    headers = {
        "Authorization": f"Bearer {test_identity['token']}",
        "Content-Length": str(len(huge_data)),
        "Content-Type": "application/json",
    }
    resp = client.post("/v1/ingest", content=huge_data, headers=headers)
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"]["code"] == "payload_too_large"


@pytest.mark.db
def test_ingest_no_payload_content_logged(client: TestClient, db_conn, test_identity, caplog):
    """Verify that sensitive payload content is never logged."""
    secret_marker = "SUPER_SECRET_PAYLOAD_MARKER_9999"
    batch = {
        "schema_version": "1.0",
        "batch_id": "batch-logging-check",
        "sent_at": "2026-11-26T12:00:00Z",
        "events": [
            {
                "source_type": "generic",
                "source_name": "git-vcs",
                "payload": {
                    "event_id": str(uuid4()),
                    "event_kind": "commit",
                    "occurred_at": "2026-11-26T12:02:00Z",
                    "subject": f"commit/{secret_marker}",
                    "metrics": {"files_count": 1.0},
                    "attributes": {"secret_field": secret_marker},
                },
            }
        ],
    }
    headers = {"Authorization": f"Bearer {test_identity['token']}"}
    with caplog.at_level(logging.DEBUG):
        resp = client.post("/v1/ingest", json=batch, headers=headers)
        assert resp.status_code == 202

    # Check caplog records
    log_text = " ".join([record.getMessage() for record in caplog.records])
    assert secret_marker not in log_text
    assert "Bearer " not in log_text
