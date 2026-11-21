# Pydantic will validates data in and shapes data out.
from datetime import datetime, timezone
from typing import Literal 

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator 

from app.constants import TopicName  # [ADD in Step 3]


class UserCreate(BaseModel):
    """What the client sends to register. Invalid input gets a 422 before our code runs."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """What the API returns. No password or hash field, so neither can leak."""
    model_config = ConfigDict(from_attributes=True)  # lets it read SQLAlchemy objects

    user_id: int
    username: str
    email: EmailStr
    registered_at: datetime


class Token(BaseModel):
    """Returned by a successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ======================= [ADD in Step 3] posts and topics =======================

def _require_text(value: str) -> str:
    """Reject empty or whitespace-only text; store the trimmed version."""
    value = value.strip()
    if not value:
        raise ValueError("must contain non-whitespace text")
    return value


class PostCreate(BaseModel):
    """What the client sends to create a post. There is deliberately NO user_id,
    post_id or created_at field: the server decides those (author comes from the token)."""
    title: str = Field(max_length=200)
    body: str = Field(max_length=10_000)
    topics: list[TopicName] = Field(min_length=1)  # only Politics, Health, Sport, Tech
    expires_at: datetime

    @field_validator("title", "body")
    @classmethod
    def not_blank(cls, v: str) -> str:
        return _require_text(v)

    @field_validator("topics")
    @classmethod
    def unique_topics(cls, v: list[TopicName]) -> list[TopicName]:
        return list(dict.fromkeys(v))  # drop duplicates, keep order

    @field_validator("expires_at")
    @classmethod
    def to_naive_utc(cls, v: datetime) -> datetime:
        # Clients may send "...Z" or "+01:00". Convert to UTC and drop tzinfo,
        # the same form the database returns. A time without tzinfo is read as UTC.
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class AuthorOut(BaseModel):
    """Public view of an author: no email, no hash."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str


class CommentOut(BaseModel):
    """A comment as returned inside a post. The author is shown as a public
    summary (id and username only), never the email or the hash."""
    model_config = ConfigDict(from_attributes=True)

    comment_id: int
    author: AuthorOut
    body: str
    created_at: datetime


class TopicOut(BaseModel):
    """One of the four fixed topics (Politics, Health, Sport, Tech),
    as returned by GET /topics."""
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    name: str
    description: str


class PostOut(BaseModel):
    """A post as returned by the API. It is built by to_post_out() in
    routers/posts.py, not read straight from the database, because some
    fields are calculated."""
    post_id: int
    author: AuthorOut
    title: str
    body: str
    topics: list[str]
    created_at: datetime
    expires_at: datetime
    status: Literal["Live", "Expired"]  # computed from expires_at, never stored
    likes: int
    dislikes: int
    comments: list[CommentOut]