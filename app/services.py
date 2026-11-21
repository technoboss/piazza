# Business rules shared by several endpoints.
# Keeping the expiry rule in ONE place means reactions, comments and any later
# endpoint cannot disagree about what "expired" means.

from datetime import datetime 

from fastapi import HTTPException, status

from app.constants import PostStatus

from app.models import Post
from app.utils import utcnow


def is_expired(post: Post) -> bool:
    """A post is expired once its expiry time is now or in the past."""
    return post.expires_at <= utcnow()


def ensure_post_open(post: Post) -> None:
    """Raise 409 if the post has expired. Call this before ANY write on a post.
    Reading an expired post is still allowed, so reads never call this."""
    if is_expired(post):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This post has expired: it accepts no further reactions or comments",
        )


def status_clause(wanted: PostStatus, now: datetime):
    """The same Live/Expired rule as is_expired(), written as a SQL
    condition so the database can filter. Expired is expires_at <= now; Live is the
    opposite. Pass ONE 'now' per request so a whole list uses the same instant."""
    if wanted is PostStatus.expired:
        return Post.expires_at <= now
    return Post.expires_at > now
