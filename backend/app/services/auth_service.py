from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from psycopg import Connection

from app.core.security import hash_token, verify_token_hash
from app.repositories.token_repo import TokenRepository
from app.repositories.workstation_repo import WorkstationRepository


@dataclass(frozen=True)
class DeviceIdentity:
    employee_id: UUID
    workstation_id: UUID


class AuthenticationError(Exception):
    """Raised when device authentication fails for any reason."""
    pass


class AuthService:
    """Service handling device token verification and identity resolution."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn
        self.token_repo = TokenRepository(conn)
        self.workstation_repo = WorkstationRepository(conn)

    def authenticate(self, raw_token: str, throttle_update_seconds: int = 60) -> DeviceIdentity:
        """Authenticate a device token.

        Rejects unknown, revoked, and expired tokens.
        Updates `last_used_at` with throttling to reduce DB write load.
        Raises AuthenticationError on failure.
        """
        if not raw_token or not isinstance(raw_token, str):
            raise AuthenticationError("Invalid token")

        token_hash = hash_token(raw_token)
        token_record = self.token_repo.get_by_hash(token_hash)
        if not token_record:
            raise AuthenticationError("Invalid token")

        # Constant-time verify the hash
        if not verify_token_hash(raw_token, token_record["token_hash"]):
            raise AuthenticationError("Invalid token")

        now = datetime.now(UTC)

        # Check if token is revoked
        if token_record["revoked_at"] is not None:
            raise AuthenticationError("Invalid token")

        # Check if token is expired
        expires_at = token_record["expires_at"]
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if now >= expires_at:
                raise AuthenticationError("Invalid token")

        workstation_id = token_record["workstation_id"]
        workstation = self.workstation_repo.get_by_id(workstation_id)
        if not workstation:
            raise AuthenticationError("Invalid token")

        if workstation["revoked_at"] is not None:
            raise AuthenticationError("Invalid token")

        employee_id = workstation["employee_id"]

        # Throttled update of last_used_at
        last_used_at = token_record["last_used_at"]
        should_update = False
        if last_used_at is None:
            should_update = True
        else:
            if last_used_at.tzinfo is None:
                last_used_at = last_used_at.replace(tzinfo=UTC)
            if now - last_used_at >= timedelta(seconds=throttle_update_seconds):
                should_update = True

        if should_update:
            self.token_repo.update_last_used(token_record["id"], last_used_at=now)

        return DeviceIdentity(
            employee_id=employee_id,
            workstation_id=workstation_id,
        )
