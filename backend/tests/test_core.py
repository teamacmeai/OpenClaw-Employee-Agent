import pytest
from fastapi.testclient import TestClient


def test_request_id_generated(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    req_id = response.headers.get("x-request-id")
    assert req_id is not None
    assert len(req_id) > 0


def test_request_id_propagated(client: TestClient) -> None:
    custom_id = "test-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


def test_not_found_standard_error(client: TestClient) -> None:
    response = client.get("/unknown-route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert data["error"]["message"] == "Not Found"
    assert data["error"]["request_id"] == response.headers.get("x-request-id")


def test_request_body_max_bytes_exceeded(client: TestClient) -> None:
    large_header = {"Content-Length": "2000000"}
    response = client.post("/health", headers=large_header)
    assert response.status_code == 413
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "payload_too_large"
    assert data["error"]["request_id"] == response.headers.get("x-request-id")
