from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """What the client sends to register."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """What the API returns. It has no password or hash field on purpose."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: EmailStr
    registered_at: datetime


class Token(BaseModel):
    """Returned by a successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # lifetime in seconds