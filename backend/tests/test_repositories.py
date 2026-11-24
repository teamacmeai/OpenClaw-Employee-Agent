import uuid
from datetime import UTC, datetime, timedelta

import pytest
from psycopg import Connection

from app.repositories import EmployeeRepository, TokenRepository, WorkstationRepository


@pytest.mark.db
def test_employee_repository_crud(db_conn: Connection) -> None:
    repo = EmployeeRepository(db_conn)

    emp_id = uuid.uuid4()
    external_ref = f"emp-{uuid.uuid4().hex[:8]}"

    # Create
    created = repo.create(
        id=emp_id,
        external_ref=external_ref,
        display_name="Test Developer",
        role_id="engineering",
    )
    assert created["id"] == emp_id
    assert created["external_ref"] == external_ref
    assert created["status"] == "active"

    # Get by id
    fetched = repo.get_by_id(emp_id)
    assert fetched is not None
    assert fetched["display_name"] == "Test Developer"

    # Get by external_ref
    fetched_by_ref = repo.get_by_external_ref(external_ref)
    assert fetched_by_ref is not None
    assert fetched_by_ref["id"] == emp_id

    # List
    all_employees = repo.list_all()
    assert any(e["id"] == emp_id for e in all_employees)

    # Revoke
    revoked = repo.revoke(emp_id)
    assert revoked is not None
    assert revoked["status"] == "revoked"


@pytest.mark.db
def test_workstation_repository_crud(db_conn: Connection) -> None:
    emp_repo = EmployeeRepository(db_conn)
    ws_repo = WorkstationRepository(db_conn)

    emp_id = uuid.uuid4()
    emp_repo.create(
        id=emp_id,
        external_ref=f"emp-{uuid.uuid4().hex[:8]}",
        display_name="Workstation Owner",
        role_id="engineering",
    )

    ws_id = uuid.uuid4()
    created = ws_repo.create(
        id=ws_id,
        employee_id=emp_id,
        name="MacBook-Pro-Dev-01",
    )
    assert created["id"] == ws_id
    assert created["employee_id"] == emp_id
    assert created["name"] == "MacBook-Pro-Dev-01"
    assert created["revoked_at"] is None

    # Get by id
    fetched = ws_repo.get_by_id(ws_id)
    assert fetched is not None
    assert fetched["name"] == "MacBook-Pro-Dev-01"

    # List by employee
    emp_ws = ws_repo.list_by_employee_id(emp_id)
    assert len(emp_ws) == 1
    assert emp_ws[0]["id"] == ws_id

    # List all
    all_ws = ws_repo.list_all()
    assert any(w["id"] == ws_id for w in all_ws)

    # Revoke
    revoked = ws_repo.revoke(ws_id)
    assert revoked is not None
    assert revoked["revoked_at"] is not None


@pytest.mark.db
def test_token_repository_crud(db_conn: Connection) -> None:
    emp_repo = EmployeeRepository(db_conn)
    ws_repo = WorkstationRepository(db_conn)
    token_repo = TokenRepository(db_conn)

    emp_id = uuid.uuid4()
    emp_repo.create(
        id=emp_id,
        external_ref=f"emp-{uuid.uuid4().hex[:8]}",
        display_name="Token User",
        role_id="engineering",
    )

    ws_id = uuid.uuid4()
    ws_repo.create(
        id=ws_id,
        employee_id=emp_id,
        name="Linux-Workstation-01",
    )

    token_id = uuid.uuid4()
    token_hash = f"hash_{uuid.uuid4().hex}"
    expires_at = datetime.now(UTC) + timedelta(days=30)

    # Create
    created = token_repo.create(
        id=token_id,
        workstation_id=ws_id,
        prefix="dev1",
        token_hash=token_hash,
        expires_at=expires_at,
    )
    assert created["id"] == token_id
    assert created["prefix"] == "dev1"
    assert created["token_hash"] == token_hash
    assert created["revoked_at"] is None
    assert created["last_used_at"] is None

    # Get by id
    fetched = token_repo.get_by_id(token_id)
    assert fetched is not None
    assert fetched["id"] == token_id

    # Get by hash
    fetched_hash = token_repo.get_by_hash(token_hash)
    assert fetched_hash is not None
    assert fetched_hash["id"] == token_id

    # List by workstation
    ws_tokens = token_repo.list_by_workstation_id(ws_id)
    assert len(ws_tokens) == 1
    assert ws_tokens[0]["id"] == token_id

    # Update last_used
    updated = token_repo.update_last_used(token_id)
    assert updated is not None
    assert updated["last_used_at"] is not None

    # Revoke
    revoked = token_repo.revoke(token_id)
    assert revoked is not None
    assert revoked["revoked_at"] is not None
