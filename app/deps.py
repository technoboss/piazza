import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# Reads the "Authorization: Bearer <token>" header. If the header is missing,
# FastAPI answers 401 by itself. tokenUrl makes the Authorize button in /docs work.
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
    """Dependency for every protected endpoint: returns the logged-in user or raises 401."""
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token")

    try:
        user = db.get(User, int(payload["sub"]))
    except (ValueError, TypeError):
        raise _unauthorized("Invalid token")
    if user is None:  # valid token, but the user no longer exists
        raise _unauthorized("Invalid token")
    return user