import argparse
import sys
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.security import generate_device_token
from app.db.pool import close_pool, connection
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.workstation_repo import WorkstationRepository


def register_employee(args: argparse.Namespace) -> None:
    employee_id = UUID(args.id) if args.id else uuid4()
    with connection() as conn:
        repo = EmployeeRepository(conn)
        existing = repo.get_by_external_ref(args.external_ref)
        if existing:
            print(f"Error: Employee with external_ref '{args.external_ref}' already exists (ID: {existing['id']})", file=sys.stderr)
            sys.exit(1)
        created = repo.create(
            id=employee_id,
            external_ref=args.external_ref,
            display_name=args.display_name,
            role_id=args.role_id,
        )
        print(f"Employee registered successfully:")
        print(f"  ID: {created['id']}")
        print(f"  External Ref: {created['external_ref']}")
        print(f"  Display Name: {created['display_name']}")
        print(f"  Role ID: {created['role_id']}")
        print(f"  Status: {created['status']}")


def register_workstation(args: argparse.Namespace) -> None:
    workstation_id = UUID(args.id) if args.id else uuid4()
    employee_id = UUID(args.employee_id)
    with connection() as conn:
        emp_repo = EmployeeRepository(conn)
        emp = emp_repo.get_by_id(employee_id)
        if not emp:
            print(f"Error: Employee ID {employee_id} not found", file=sys.stderr)
            sys.exit(1)

        ws_repo = WorkstationRepository(conn)
        created = ws_repo.create(
            id=workstation_id,
            employee_id=employee_id,
            name=args.name,
        )
        print(f"Workstation registered successfully:")
        print(f"  ID: {created['id']}")
        print(f"  Employee ID: {created['employee_id']}")
        print(f"  Name: {created['name']}")


def issue_token(args: argparse.Namespace) -> None:
    workstation_id = UUID(args.workstation_id)
    token_id = UUID(args.id) if args.id else uuid4()
    expires_at = datetime.fromisoformat(args.expires_at) if args.expires_at else None

    raw_token, prefix, token_hash = generate_device_token()

    with connection() as conn:
        ws_repo = WorkstationRepository(conn)
        ws = ws_repo.get_by_id(workstation_id)
        if not ws:
            print(f"Error: Workstation ID {workstation_id} not found", file=sys.stderr)
            sys.exit(1)

        token_repo = TokenRepository(conn)
        created = token_repo.create(
            id=token_id,
            workstation_id=workstation_id,
            prefix=prefix,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        print("Device token issued successfully.")
        print(f"  Token ID: {created['id']}")
        print(f"  Workstation ID: {created['workstation_id']}")
        print(f"  Prefix: {created['prefix']}")
        print(f"  Expires At: {created['expires_at']}")
        print(f"  IMPORTANT: Store this token safely. It will not be shown again:")
        print(f"  Token: {raw_token}")


def revoke_token(args: argparse.Namespace) -> None:
    token_id = UUID(args.token_id)
    with connection() as conn:
        token_repo = TokenRepository(conn)
        existing = token_repo.get_by_id(token_id)
        if not existing:
            print(f"Error: Token ID {token_id} not found", file=sys.stderr)
            sys.exit(1)
        revoked = token_repo.revoke(token_id)
        print(f"Token {token_id} revoked at {revoked['revoked_at']}.")


def list_tokens(args: argparse.Namespace) -> None:
    with connection() as conn:
        token_repo = TokenRepository(conn)
        if args.workstation_id:
            tokens = token_repo.list_by_workstation_id(UUID(args.workstation_id))
        else:
            tokens = token_repo.list_all(limit=args.limit, offset=args.offset)

        if not tokens:
            print("No tokens found.")
            return

        print(f"{'Token ID':<38} {'Workstation ID':<38} {'Prefix':<10} {'Revoked At':<25} {'Expires At':<25} {'Last Used At'}")
        print("-" * 140)
        for t in tokens:
            rev_str = str(t["revoked_at"]) if t["revoked_at"] else "None"
            exp_str = str(t["expires_at"]) if t["expires_at"] else "None"
            last_str = str(t["last_used_at"]) if t["last_used_at"] else "None"
            print(f"{str(t['id']):<38} {str(t['workstation_id']):<38} {t['prefix']:<10} {rev_str:<25} {exp_str:<25} {last_str}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw Admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # register-employee
    p_emp = subparsers.add_parser("register-employee", help="Register a new employee")
    p_emp.add_argument("--external-ref", required=True, help="External reference ID (unique)")
    p_emp.add_argument("--display-name", required=True, help="Employee display name")
    p_emp.add_argument("--role-id", required=True, help="Role identifier")
    p_emp.add_argument("--id", required=False, help="Explicit UUID (optional)")
    p_emp.set_defaults(func=register_employee)

    # register-workstation
    p_ws = subparsers.add_parser("register-workstation", help="Register a new workstation for an employee")
    p_ws.add_argument("--employee-id", required=True, help="Employee UUID")
    p_ws.add_argument("--name", required=True, help="Workstation descriptive name")
    p_ws.add_argument("--id", required=False, help="Explicit UUID (optional)")
    p_ws.set_defaults(func=register_workstation)

    # issue-token
    p_tok = subparsers.add_parser("issue-token", help="Issue a new device token for a workstation")
    p_tok.add_argument("--workstation-id", required=True, help="Workstation UUID")
    p_tok.add_argument("--expires-at", required=False, help="Expiration date/time (ISO format, optional)")
    p_tok.add_argument("--id", required=False, help="Explicit UUID (optional)")
    p_tok.set_defaults(func=issue_token)

    # revoke-token
    p_rev = subparsers.add_parser("revoke-token", help="Revoke an existing token by ID")
    p_rev.add_argument("--token-id", required=True, help="Token UUID to revoke")
    p_rev.set_defaults(func=revoke_token)

    # list-tokens
    p_list = subparsers.add_parser("list-tokens", help="List tokens (never prints secret or hash)")
    p_list.add_argument("--workstation-id", required=False, help="Filter by workstation UUID")
    p_list.add_argument("--limit", type=int, default=100, help="Max records to return")
    p_list.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    p_list.set_defaults(func=list_tokens)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    finally:
        close_pool()


if __name__ == "__main__":
    main()
