# Dependencies = shared logic that endpoints
# request with Depends(...).
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# Reads "Authorization: Bearer <token>". A missing header gives 401 automatically.
# tokenUrl also powers the Authorize button in /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Add Depends(get_current_user) to any protected endpoint.
    Returns the logged-in user, or raises 401 so the endpoint never runs."""
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidTokenError:  # bad signature, garbage, missing claims
        raise _unauthorized("Invalid token")

    try:
        user = db.get(User, int(payload["sub"]))
    except (ValueError, TypeError):
        raise _unauthorized("Invalid token")
    if user is None:  # valid token, but the user was deleted
        raise _unauthorized("Invalid token")
    return user
