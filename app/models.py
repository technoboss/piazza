from sqlalchemy import (CheckConstraint, Column, DateTime, ForeignKey,
                        Integer, String, Text, text, Table)

from sqlalchemy.orm import relationship

from app.database import Base 

NOW = text("(datetime('now'))") 

# Junction table: one row = "this post belongs to this topic".
# The composite primary key stops the same topic being attached twice to a post.
post_topic = Table(
    "post_topic",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("post.post_id"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topic.topic_id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("datetime(registered_at) IS NOT NULL", name="ck_users_registered_at"),
        {"sqlite_autoincrement": True},
    )

    user_id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String(collation="NOCASE"), nullable=False, unique=True)
    pwd_hash = Column(String, nullable=False, unique=True)
    registered_at = Column(DateTime, nullable=False, server_default=NOW)

    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author")
    reactions = relationship("Reaction", back_populates="user")


class Topic(Base):
    __tablename__ = "topic"
    __table_args__ = {"sqlite_autoincrement": True}

    topic_id = Column(Integer, primary_key=True)
    name = Column(String(collation="NOCASE"), nullable=False, unique=True)
    description = Column(Text, nullable=False)

    # [CHANGE] many-to-many through post_topic (was one-to-many)
    posts = relationship("Post", secondary=post_topic, back_populates="topics")


class Post(Base):
    __tablename__ = "post"
    __table_args__ = (
        CheckConstraint("datetime(created_at) IS NOT NULL", name="ck_post_created_at"),
        CheckConstraint("datetime(expires_at) IS NOT NULL", name="ck_post_expires_at"),
        CheckConstraint("expires_at > created_at", name="ck_post_expires_after_created"),
        {"sqlite_autoincrement": True},
    )

    post_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=NOW)
    expires_at = Column(DateTime, nullable=False)

    author = relationship("User", back_populates="posts")
    topics = relationship("Topic", secondary=post_topic, back_populates="posts")
    comments = relationship(
        "Comment", back_populates="post", order_by="[Comment.created_at, Comment.comment_id]"
    )
    reactions = relationship("Reaction", back_populates="post")


class Comment(Base):
    __tablename__ = "comment"
    __table_args__ = (
        CheckConstraint("datetime(created_at) IS NOT NULL", name="ck_comment_created_at"),
        {"sqlite_autoincrement": True},
    )

    comment_id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("post.post_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=NOW)

    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")


class Reaction(Base):
    __tablename__ = "reacts"
    __table_args__ = (
        CheckConstraint("datetime(reacted_at) IS NOT NULL", name="ck_reacts_reacted_at"),
    )

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    post_id = Column(Integer, ForeignKey("post.post_id"), primary_key=True)
    type = Column(String, nullable=False)  # "like" or "dislike"
    reacted_at = Column(DateTime, nullable=False, server_default=NOW)

    user = relationship("User", back_populates="reactions")
    post = relationship("Post", back_populates="reactions")