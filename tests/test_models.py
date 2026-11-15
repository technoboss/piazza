from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Comment, Post, Topic, User


# Helper, not a test (the name does not start with "test_").
# Creates the user and topic that a post needs.
def make_user_and_topic(db):
    user = User(username="alice", email="alice@example.com", pwd_hash="hash1")
    topic = Topic(name="Cloud", description="Cloud computing")
    db.add_all([user, topic])
    db.commit()  # commit assigns the auto-generated ids
    return user, topic


def test_create_post(db_session):
    user, topic = make_user_and_topic(db_session)
    # Current UTC time without timezone info, the format SQLite stores.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    post = Post(user_id=user.user_id, topic_id=topic.topic_id,
                title="Hello", body="First post",
                expires_at=now + timedelta(days=1))  # expires in one day
    db_session.add(post)
    db_session.commit()
    assert post.post_id is not None          # the database gave it an id
    assert post.author.username == "alice"   # the relationship works


def test_foreign_key_is_enforced(db_session):
    make_user_and_topic(db_session)
    # Post 999 does not exist, so this comment points at nothing.
    db_session.add(Comment(post_id=999, user_id=1, body="orphan"))
    # The test passes only if the database refuses the insert.
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_post_must_expire_after_creation(db_session):
    user, topic = make_user_and_topic(db_session)
    # expires_at (Jan 1) is before created_at (Jan 2), which the
    # CHECK constraint on the post table forbids.
    db_session.add(Post(
        user_id=user.user_id, topic_id=topic.topic_id, title="x", body="y",
        created_at=datetime(2026, 1, 2), expires_at=datetime(2026, 1, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()