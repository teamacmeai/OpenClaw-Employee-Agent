from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "x-request-id" in response.headers


def test_health_db_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    @contextmanager
    def mock_connection() -> Iterator[MagicMock]:
        yield mock_conn

    monkeypatch.setattr("app.api.routes.health.connection", mock_connection)
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_db_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def mock_failing_connection() -> Iterator[None]:
        raise psycopg.OperationalError("Could not connect to server")
        yield

    monkeypatch.setattr("app.api.routes.health.connection", mock_failing_connection)
    response = client.get("/health/db")
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "service_unavailable"
    assert data["error"]["message"] == "Database connection failed"
    assert data["error"]["request_id"] is not None
    assert response.headers["x-request-id"] == data["error"]["request_id"]


@pytest.mark.db
def test_health_db_live(client: TestClient) -> None:
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
