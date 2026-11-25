from uuid import uuid4

import pytest

from app.cli import main
from app.core.security import generate_device_token
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.workstation_repo import WorkstationRepository


@pytest.mark.db
def test_admin_cli_flow(capsys, db_conn):
    emp_ref = f"emp-{uuid4().hex[:8]}"
    # 1. Register employee
    main(["register-employee", "--external-ref", emp_ref, "--display-name", "CLI Alice", "--role-id", "engineer"])
    captured = capsys.readouterr().out
    assert "Employee registered successfully" in captured
    assert emp_ref in captured

    emp_repo = EmployeeRepository(db_conn)
    emp = emp_repo.get_by_external_ref(emp_ref)
    assert emp is not None

    # 2. Register workstation
    ws_name = "MacBook-Pro-CLI"
    main(["register-workstation", "--employee-id", str(emp["id"]), "--name", ws_name])
    captured = capsys.readouterr().out
    assert "Workstation registered successfully" in captured
    assert ws_name in captured

    ws_repo = WorkstationRepository(db_conn)
    workstations = ws_repo.list_by_employee_id(emp["id"])
    assert len(workstations) == 1
    ws_id = workstations[0]["id"]

    # 3. Issue token
    main(["issue-token", "--workstation-id", str(ws_id)])
    captured = capsys.readouterr().out
    assert "Device token issued successfully" in captured
    assert "ocl_" in captured
    assert "IMPORTANT: Store this token safely" in captured

    tok_repo = TokenRepository(db_conn)
    tokens = tok_repo.list_by_workstation_id(ws_id)
    assert len(tokens) == 1
    tok_id = tokens[0]["id"]

    # 4. List tokens
    main(["list-tokens", "--workstation-id", str(ws_id)])
    captured = capsys.readouterr().out
    assert str(tok_id) in captured
    # Ensure raw secret and token_hash are never printed in list
    assert tokens[0]["token_hash"] not in captured

    # 5. Revoke token
    main(["revoke-token", "--token-id", str(tok_id)])
    captured = capsys.readouterr().out
    assert f"Token {tok_id} revoked at" in captured

    revoked_tok = tok_repo.get_by_id(tok_id)
    assert revoked_tok["revoked_at"] is not None
