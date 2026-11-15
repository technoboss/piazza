PRAGMA foreign_keys = ON;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pwd_hash TEXT NOT NULL UNIQUE,
    registered_at TEXT NOT NULL DEFAULT (datetime('now'))
                  CHECK (datetime(registered_at) IS NOT NULL)
);

CREATE TABLE topic (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    description TEXT NOT NULL
);

-- relationships: user publishes post (1:N), topic categorizes post (1:N)
CREATE TABLE post (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    topic_id INTEGER NOT NULL REFERENCES topic(topic_id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
               CHECK (datetime(created_at) IS NOT NULL),
    expires_at TEXT NOT NULL
               CHECK (datetime(expires_at) IS NOT NULL),
               CHECK (expires_at > created_at)
);

-- relationships: post has comment (1:N), user writes comment (1:N)
CREATE TABLE comment (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES post(post_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
               CHECK (datetime(created_at) IS NOT NULL)
);

-- relationship: user reacts to post (M:N), with attributes type and reacted_at
CREATE TABLE reacts (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    post_id INTEGER NOT NULL REFERENCES post(post_id),
    type TEXT NOT NULL,
    reacted_at TEXT NOT NULL DEFAULT (datetime('now'))
               CHECK (datetime(reacted_at) IS NOT NULL),
    PRIMARY KEY (user_id, post_id)
);
