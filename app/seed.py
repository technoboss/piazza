# Makes sure the four topics exist. Safe to run on every startup.
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import TOPIC_DESCRIPTIONS
from app.models import Topic


def seed_topics(db: Session) -> None:
    existing = set(db.scalars(select(Topic.name)).all())
    for name, description in TOPIC_DESCRIPTIONS.items():
        if name.value not in existing:
            db.add(Topic(name=name.value, description=description))
    db.commit()