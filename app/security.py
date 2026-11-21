
from datetime import datetime, timedelta, timezone

import jwt 
from pwdlib import PasswordHash

from app.config import settings

# argon2 hashing with sensible defaults. Every hash carries its own random salt.
password_hasher = PasswordHash.recommended()

# Hash of a throwaway password. Login verifies against it when the user does not
# exist, so "unknown user" and "wrong password" take about the same time.
DUMMY_HASH = password_hasher.hash("dummy-password-for-timing")


def hash_password(plain_password: str) -> str:
    """Plaintext -> one-way hash. Only the hash is ever stored."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login password against the stored hash."""
    return password_hasher.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Build a signed JWT. sub = who, iat = issued at, exp = when it stops working."""
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": str(user_id), "iat": now, "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Verify signature and expiry. Raises a jwt error if the token is bad or expired."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],  # only accept the algorithm we expect
        options={"require": ["exp", "sub"]},  # reject tokens missing these claims
    )
