
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Comment, Post, Topic, User
from app.utils import utcnow


def make_user_and_topic(db):
    user = User(username="alice", email="alice@example.com", pwd_hash="hash1")
    topic = db.query(Topic).filter_by(name="Tech").one()  # seeded by the db_session fixture
    db.add(user)
    db.commit()
    return user, topic


def test_create_post(db_session):
    user, topic = make_user_and_topic(db_session)
    post = Post(user_id=user.user_id, title="Hello", body="First post",
                expires_at=utcnow() + timedelta(days=1), topics=[topic])
    db_session.add(post)
    db_session.commit()
    assert post.post_id is not None
    assert post.author.username == "alice"  # the relationship works
    assert [t.name for t in post.topics] == ["Tech"]


def test_foreign_key_is_enforced(db_session):
    make_user_and_topic(db_session)
    # Post 999 does not exist, so this comment points at nothing.
    db_session.add(Comment(post_id=999, user_id=1, body="orphan"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_post_must_expire_after_creation(db_session):
    user, topic = make_user_and_topic(db_session)
    # expires_at (Jan 1) is before created_at (Jan 2): the CHECK constraint forbids it.
    db_session.add(Post(user_id=user.user_id, title="x", body="y", topics=[topic],
                        created_at=datetime(2026, 1, 2), expires_at=datetime(2026, 1, 1)))
    with pytest.raises(IntegrityError):
        db_session.commit()