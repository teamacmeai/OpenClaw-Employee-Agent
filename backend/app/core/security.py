import hashlib
import hmac
import secrets

TOKEN_PREFIX_SCHEME = "ocl"


def generate_device_token() -> tuple[str, str, str]:
    """Generate a high-entropy device token.

    Format: ocl_<prefix>_<secret>
    Returns: (raw_token, prefix, token_hash)
    Prefix is 8 hex chars (4 bytes), secret is 32 hex chars (16 bytes).
    """
    prefix = secrets.token_hex(4)
    secret = secrets.token_hex(16)
    token = f"{TOKEN_PREFIX_SCHEME}_{prefix}_{secret}"
    token_hash = hash_token(token)
    return token, prefix, token_hash


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(token: str, expected_hash: str) -> bool:
    """Verify raw token against expected hash using constant-time comparison."""
    computed_hash = hash_token(token)
    return hmac.compare_digest(computed_hash, expected_hash)
