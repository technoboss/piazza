# [NEW in Step 3] Create a post, read one post, browse posts by topic.
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.constants import PostStatus, TopicName
from app.constants import TopicName 
from app.database import get_db
from app.deps import get_current_user
from app.models import Comment, Post, Topic, User
from app.schemas import PostCreate, PostOut
from app.services import is_expired, status_clause
from app.services import is_expired 
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
            "status": "Expired" if is_expired(post) else "Live",
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


def load_post(db: Session, post_id: int) -> Post | None:
    """Fetch one post with everything a response needs, or None. 
    populate_existing forces fresh data, so counts are correct right after a commit."""
    return db.scalar(
        select(Post)
        .options(*LOAD_OPTIONS)
        .where(Post.post_id == post_id)
        .execution_options(populate_existing=True)
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
    # The URL parameter is called "status". The Python name differs
    # only so it does not clash with the "status" module imported above.
    status_filter: PostStatus | None = Query(
        None, alias="status", description="Live or Expired. Leave out to get both."
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse posts, newest first. ?topic= keeps only posts that carry that topic, so a
    multi-topic post shows up under each of its topics. ?status=Live or ?status=Expired
    filters by status. With no status filter, BOTH are returned."""
    query = select(Post).options(*LOAD_OPTIONS)
    if topic is not None:
        query = query.where(Post.topics.any(Topic.name == topic.value))
    if status_filter is not None:  
        query = query.where(status_clause(status_filter, utcnow()))
    query = query.order_by(Post.created_at.desc(), Post.post_id.desc()).limit(limit).offset(offset)
    return [to_post_out(p) for p in db.scalars(query).all()]

@router.get("/{post_id}", response_model=PostOut)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = load_post(db, post_id)  # reuses the new helper
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    return to_post_out(post)  # readable even when expired
