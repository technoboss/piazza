# [NEW in Step 3] Create a post, read one post, browse posts by topic.
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.constants import TopicName 
from app.database import get_db
from app.deps import get_current_user
from app.models import Comment, Post, Topic, User
from app.schemas import PostCreate, PostOut
from app.utils import utcnow

router = APIRouter(prefix="/posts", tags=["posts"])


def to_post_out(post: Post) -> PostOut:
    """Turn a database Post into the API response, computing status and counts."""
    likes = sum(1 for r in post.reactions if r.type == "like")
    dislikes = sum(1 for r in post.reactions if r.type == "dislike")
    return PostOut.model_validate(
        {
            "post_id": post.post_id,
            "author": post.author,
            "title": post.title,
            "body": post.body,
            "topics": [t.name for t in post.topics],
            "created_at": post.created_at,
            "expires_at": post.expires_at,
            # Derived at read time, so a post flips to Expired by itself.
            "status": "Expired" if post.expires_at <= utcnow() else "Live",
            "likes": likes,
            "dislikes": dislikes,
            "comments": post.comments,
        }
    )


# Load everything a response needs in a few queries instead of one per post.
LOAD_OPTIONS = (
    selectinload(Post.author),
    selectinload(Post.topics),
    selectinload(Post.reactions),
    selectinload(Post.comments).selectinload(Comment.author),
)


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # token required
):
    now = utcnow()  # server-generated creation time
    if payload.expires_at <= now: 
        raise HTTPException(422, "expires_at must be in the future")

    names = [t.value for t in payload.topics]
    topics = db.scalars(select(Topic).where(Topic.name.in_(names))).all()
    if len(topics) != len(names):  # only possible if the topics were not seeded
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Topics are not initialised")

    post = Post(
        user_id=current_user.user_id,  # author from the verified token, never from the request
        title=payload.title,
        body=payload.body,
        created_at=now,
        expires_at=payload.expires_at,
        topics=topics,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return to_post_out(post)  # new post: 0 likes, 0 dislikes, no comments


@router.get("", response_model=list[PostOut])
def list_posts(
    topic: TopicName | None = Query(None, description="Politics, Health, Sport or Tech"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All posts, newest first, expired ones included. topic= keeps only posts that
    carry that topic, so a multi-topic post shows up under each of its topics."""
    query = select(Post).options(*LOAD_OPTIONS)
    if topic is not None:
        query = query.where(Post.topics.any(Topic.name == topic.value))
    query = query.order_by(Post.created_at.desc(), Post.post_id.desc()).limit(limit).offset(offset)
    return [to_post_out(p) for p in db.scalars(query).all()]


@router.get("/{post_id}", response_model=PostOut)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.scalar(select(Post).options(*LOAD_OPTIONS).where(Post.post_id == post_id))
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    return to_post_out(post)  # readable even when expired