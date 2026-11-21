
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm  # login form (needs python-multipart)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import DUMMY_HASH, create_access_token, hash_password, verify_password

# every route below starts with /auth.
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    # Friendly pre-checks. The email column is NOCASE: ALICE@x.com equals alice@x.com.
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        pwd_hash=hash_password(payload.password),  # never store the plaintext
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two identical registrations at the same instant can both pass the checks above.
        # The database UNIQUE constraint is the final guard.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already in use")
    db.refresh(user)  # loads user_id and the database-generated registered_at
    return user  # response_model=UserOut strips pwd_hash


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # The OAuth2 form field is always called "username"; we accept email or username.
    user = db.scalar(select(User).where(User.email == form.username))
    if user is None:
        user = db.scalar(select(User).where(User.username == form.username))

    # Same error for "no such user" and "wrong password", so attackers cannot
    # discover which emails are registered.
    if user is None:
        verify_password(form.password, DUMMY_HASH)  # keep response timing similar
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form.password, user.pwd_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        access_token=create_access_token(user.user_id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    """Protected endpoint: returns the logged-in user. Handy for testing a token."""
    return current_user
