# Reactions and comments on posts. Both are WRITES, so they should reject once the post has expired.
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Comment, Post, Reaction, User
from app.routers.posts import load_post, to_post_out
from app.schemas import CommentCreate, CommentOut, PostOut, ReactionIn
from app.services import ensure_post_open
from app.utils import utcnow

# Same "/posts" prefix as the posts router: /posts/{id}/reaction, /posts/{id}/comments.
router = APIRouter(prefix="/posts", tags=["reactions and comments"])


def _save_reaction(db: Session, user_id: int, post_id: int, reaction_type: str) -> None:
    """Create the user's reaction, switch it, or do nothing if it is unchanged.
    The reacts table has ONE row per (user, post), so a user can never hold two
    reactions on a post: switching edits the row instead of adding another."""
    for _ in range(2):  # a second try covers a simultaneous first reaction
        reaction = db.get(Reaction, (user_id, post_id))
        if reaction is None:
            db.add(Reaction(user_id=user_id, post_id=post_id, type=reaction_type))
        elif reaction.type != reaction_type:
            reaction.type = reaction_type  # like -> dislike (or back) replaces the old one
            reaction.reacted_at = utcnow()
        else:
            return  # same reaction repeated: nothing changes, so the count cannot grow
        try:
            db.commit()
            return
        except IntegrityError:
            # Two identical first-time requests arrived together and both found no row.
            # The primary key let only one in. 
            db.rollback()
    raise HTTPException(status.HTTP_409_CONFLICT, "Could not save the reaction, please retry")


@router.put("/{post_id}/reaction", response_model=PostOut)
def set_reaction(
    post_id: int,
    payload: ReactionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # the reacting user comes from the token
):
    """Like or dislike a live post. PUT because it is idempotent: sending the same
    request twice leaves the same result. Returns the updated post with its counts."""
    post = load_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    ensure_post_open(post)  # 409 if expired
    if post.user_id == current_user.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Authors cannot react to their own posts")

    _save_reaction(db, current_user.user_id, post_id, payload.type.value)
    return to_post_out(load_post(db, post_id))  # reload so likes/dislikes are current


@router.post("/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # the author comes from the token
):
    """Add a comment to a live post. Anyone logged in may comment, the post's own
    author included, and one user may comment many times."""
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    ensure_post_open(post)  # 409 if expired

    comment = Comment(
        post_id=post_id,
        user_id=current_user.user_id,  # recorded author
        body=payload.body,  # recorded content (already trimmed and checked)
        created_at=utcnow(),  # recorded creation timestamp, set by the server
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment  # response_model=CommentOut shapes it