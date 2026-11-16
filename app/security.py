from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings

# argon2 with sensible defaults. Each hash includes its own random salt.
password_hasher = PasswordHash.recommended()

# Hash of a throwaway password. Login verifies against it when the user does
# not exist, so unknown users and wrong passwords take about the same time.
DUMMY_HASH = password_hasher.hash("dummy-password-for-timing")


def hash_password(plain_password: str) -> str:
    """Turn a plaintext password into a one-way hash for storage."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return password_hasher.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT that identifies the user and expires."""
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": str(user_id), "iat": now, "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Verify signature and expiry. Raises jwt.InvalidTokenError (or a subclass) on failure."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"require": ["exp", "sub"]},
    )