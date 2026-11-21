# Read-only: the four topics are fixed and seeded at startup.
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Topic, User
from app.schemas import TopicOut

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
def list_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # token required
):
    return db.scalars(select(Topic).order_by(Topic.topic_id)).all()