from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.api.deps import get_rate_limiter
from app.core.rate_limit import TokenBucketRateLimiter
from app.core.security import generate_device_token
from app.main import app
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.workstation_repo import WorkstationRepository


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter = get_rate_limiter()
    limiter.reset()
    yield
    limiter.reset()


def test_whoami_unauthorized_missing_token(client):
    res = client.get("/v1/device/whoami")
    assert res.status_code == 401
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "unauthorized"
    assert data["error"]["message"] == "Invalid or missing authentication token"


def test_whoami_unauthorized_malformed_token(client):
    res = client.get("/v1/device/whoami", headers={"Authorization": "Token not_a_bearer"})
    assert res.status_code == 401
    data = res.json()
    assert data["error"]["code"] == "unauthorized"
    assert data["error"]["message"] == "Invalid or missing authentication token"


@pytest.mark.db
def test_whoami_success_and_identical_401s(client, db_conn):
    emp_repo = EmployeeRepository(db_conn)
    ws_repo = WorkstationRepository(db_conn)
    tok_repo = TokenRepository(db_conn)

    emp_id = uuid4()
    emp_repo.create(id=emp_id, external_ref="emp-whoami-01", display_name="Whoami Emp", role_id="eng")

    ws_id = uuid4()
    ws_repo.create(id=ws_id, employee_id=emp_id, name="Whoami WS")

    # Valid token
    raw_token, prefix, token_hash = generate_device_token()
    tok_repo.create(id=uuid4(), workstation_id=ws_id, prefix=prefix, token_hash=token_hash)

    # Expired token
    raw_exp, prefix_exp, hash_exp = generate_device_token()
    tok_repo.create(
        id=uuid4(),
        workstation_id=ws_id,
        prefix=prefix_exp,
        token_hash=hash_exp,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    # Revoked token
    raw_rev, prefix_rev, hash_rev = generate_device_token()
    rev_id = uuid4()
    tok_repo.create(id=rev_id, workstation_id=ws_id, prefix=prefix_rev, token_hash=hash_rev)
    tok_repo.revoke(rev_id)

    # 1. Success 200
    res = client.get("/v1/device/whoami", headers={"Authorization": f"Bearer {raw_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == str(emp_id)
    assert data["workstation_id"] == str(ws_id)

    # 2. Unknown token -> 401
    res_unk = client.get("/v1/device/whoami", headers={"Authorization": "Bearer ocl_unknown_12345"})
    assert res_unk.status_code == 401
    assert res_unk.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Invalid or missing authentication token",
            "request_id": res_unk.headers.get("X-Request-ID"),
        }
    }

    # 3. Expired token -> identical 401
    res_exp = client.get("/v1/device/whoami", headers={"Authorization": f"Bearer {raw_exp}"})
    assert res_exp.status_code == 401
    assert res_exp.json()["error"]["code"] == "unauthorized"
    assert res_exp.json()["error"]["message"] == "Invalid or missing authentication token"

    # 4. Revoked token -> identical 401
    res_rev = client.get("/v1/device/whoami", headers={"Authorization": f"Bearer {raw_rev}"})
    assert res_rev.status_code == 401
    assert res_rev.json()["error"]["code"] == "unauthorized"
    assert res_rev.json()["error"]["message"] == "Invalid or missing authentication token"


@pytest.mark.db
def test_rate_limiting_enforcement(client, db_conn):
    emp_repo = EmployeeRepository(db_conn)
    ws_repo = WorkstationRepository(db_conn)
    tok_repo = TokenRepository(db_conn)

    emp_id = uuid4()
    emp_repo.create(id=emp_id, external_ref="emp-rate-limit", display_name="Rate Limit Emp", role_id="eng")
    ws_id = uuid4()
    ws_repo.create(id=ws_id, employee_id=emp_id, name="Rate Limit WS")
    raw_token, prefix, token_hash = generate_device_token()
    tok_repo.create(id=uuid4(), workstation_id=ws_id, prefix=prefix, token_hash=token_hash)

    # Override rate limiter with a small burst for testing
    test_limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=2)
    app.dependency_overrides[get_rate_limiter] = lambda: test_limiter

    try:
        # Request 1: 200
        res1 = client.get("/v1/device/whoami", headers={"Authorization": f"Bearer {raw_token}"})
        assert res1.status_code == 200

        # Request 2: 200
        res2 = client.get("/v1/device/whoami", headers={"Authorization": f"Bearer {raw_token}"})
        assert res2.status_code == 200

        # Request 3: 429 Too Many Requests
        res3 = client.get("/v1/device/whoami", headers={"Authorization": f"Bearer {raw_token}"})
        assert res3.status_code == 429
        assert "Retry-After" in res3.headers
        assert res3.json()["error"]["code"] == "rate_limit_exceeded"
    finally:
        app.dependency_overrides.clear()
