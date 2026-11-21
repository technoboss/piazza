# Pydantic will validates data in and shapes data out.

from datetime import datetime, timezone
from typing import Annotated, Literal 

from pydantic import ( BaseModel, ConfigDict, EmailStr, Field, PlainSerializer,
                       field_validator )

from app.constants import ReactionType, TopicName  


# Every timestamp the API RETURNS is shown in UTC with an explicit
# "Z", for example 2030-01-01T00:00:00Z. Inside the app and the database times are
# naive UTC, so this type adds the missing UTC marker just before sending.
def _as_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_as_utc_iso, return_type=str, when_used="json")]


class UserCreate(BaseModel):
    """What the client sends to register. Invalid input gets a 422 before our code runs."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr  # use the email-validator package
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """What the API returns. No password or hash field, so neither can leak."""
    model_config = ConfigDict(from_attributes=True)  # lets it read SQLAlchemy objects

    user_id: int
    username: str
    email: EmailStr
    registered_at: UTCDateTime  # returned as UTC with Z


class Token(BaseModel):
    """Returned by a successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # lifetime in seconds


# ======================= posts and topics =======================

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
        # A time WITHOUT a timezone is now refused (422), because
        # we cannot know what clock it was written on. A time WITH a timezone
        # ("...Z" or "+01:00") is converted to UTC, then tzinfo is dropped so it
        # matches the naive UTC the database stores and returns.
        if v.tzinfo is None:
            raise ValueError("expires_at must include a timezone, for example 2030-01-01T00:00:00Z")
        return v.astimezone(timezone.utc).replace(tzinfo=None)


class AuthorOut(BaseModel):
    """Public view of an author: no email, no hash."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    comment_id: int
    author: AuthorOut
    body: str
    created_at: UTCDateTime 


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    name: str
    description: str


class PostOut(BaseModel):
    post_id: int
    author: AuthorOut
    title: str
    body: str
    topics: list[str]
    created_at: UTCDateTime  # returned as UTC with Z
    expires_at: UTCDateTime  # returned as UTC with Z
    status: Literal["Live", "Expired"]  # computed from expires_at, never stored
    likes: int
    dislikes: int
    comments: list[CommentOut]


# ======================= reactions and comments =======================

class ReactionIn(BaseModel):
    """What the client sends to react. Only the type: the user comes from the token
    and the post comes from the URL, so neither can be faked in the body."""
    type: ReactionType  # "like" or "dislike"


class CommentCreate(BaseModel):
    """What the client sends to comment. No user_id or created_at field on purpose."""
    body: str = Field(max_length=2_000)

    @field_validator("body")
    @classmethod
    def not_blank(cls, v: str) -> str:
        return _require_text(v)  # same rule as post titles: real text, trimmed