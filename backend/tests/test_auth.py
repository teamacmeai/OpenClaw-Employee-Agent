import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.rate_limit import TokenBucketRateLimiter
from app.core.security import generate_device_token, hash_token, verify_token_hash
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.workstation_repo import WorkstationRepository
from app.services.auth_service import AuthService, AuthenticationError


def test_token_generation_and_hashing():
    raw_token, prefix, token_hash = generate_device_token()
    assert raw_token.startswith("ocl_")
    parts = raw_token.split("_")
    assert len(parts) == 3
    assert parts[0] == "ocl"
    assert parts[1] == prefix
    assert len(prefix) == 8
    assert token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert verify_token_hash(raw_token, token_hash) is True
    assert verify_token_hash("invalid", token_hash) is False


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=2)
    key = "ws-1"

    allowed, wait = limiter.check(key)
    assert allowed is True
    assert wait == 0

    allowed, wait = limiter.check(key)
    assert allowed is True
    assert wait == 0

    # Burst exceeded
    allowed, wait = limiter.check(key)
    assert allowed is False
    assert wait >= 1

    # Another key is independent
    allowed_other, wait_other = limiter.check("ws-2")
    assert allowed_other is True
    assert wait_other == 0


@pytest.mark.db
def test_auth_service_success_and_failures(db_conn):
    emp_repo = EmployeeRepository(db_conn)
    ws_repo = WorkstationRepository(db_conn)
    tok_repo = TokenRepository(db_conn)

    emp_id = uuid4()
    emp_repo.create(id=emp_id, external_ref="emp-test-01", display_name="Test Emp", role_id="eng")

    ws_id = uuid4()
    ws_repo.create(id=ws_id, employee_id=emp_id, name="Test Laptop")

    raw_token, prefix, token_hash = generate_device_token()
    tok_id = uuid4()
    tok_repo.create(id=tok_id, workstation_id=ws_id, prefix=prefix, token_hash=token_hash)

    service = AuthService(db_conn)

    # 1. Success authentication
    identity = service.authenticate(raw_token)
    assert identity.employee_id == emp_id
    assert identity.workstation_id == ws_id

    # Check last_used_at was updated
    tok_record = tok_repo.get_by_id(tok_id)
    assert tok_record["last_used_at"] is not None

    # 2. Unknown token failure
    with pytest.raises(AuthenticationError):
        service.authenticate("ocl_unknown_token_1234567890")

    # 3. Expired token failure
    raw_exp_token, exp_prefix, exp_hash = generate_device_token()
    tok_repo.create(
        id=uuid4(),
        workstation_id=ws_id,
        prefix=exp_prefix,
        token_hash=exp_hash,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    with pytest.raises(AuthenticationError):
        service.authenticate(raw_exp_token)

    # 4. Revoked token failure
    raw_rev_token, rev_prefix, rev_hash = generate_device_token()
    rev_tok_id = uuid4()
    tok_repo.create(
        id=rev_tok_id,
        workstation_id=ws_id,
        prefix=rev_prefix,
        token_hash=rev_hash,
    )
    tok_repo.revoke(rev_tok_id)
    with pytest.raises(AuthenticationError):
        service.authenticate(raw_rev_token)

    # 5. Revoked workstation failure
    ws_rev_id = uuid4()
    ws_repo.create(id=ws_rev_id, employee_id=emp_id, name="Revoked WS")
    raw_ws_rev_tok, ws_rev_pfx, ws_rev_hash = generate_device_token()
    tok_repo.create(id=uuid4(), workstation_id=ws_rev_id, prefix=ws_rev_pfx, token_hash=ws_rev_hash)
    ws_repo.revoke(ws_rev_id)
    with pytest.raises(AuthenticationError):
        service.authenticate(raw_ws_rev_tok)
