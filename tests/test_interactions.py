
# Scenario: alice (auth_headers) writes the posts; bob (other_auth_headers) reacts and comments.
from datetime import datetime, timedelta, timezone

from app.models import Comment, Post, Reaction, Topic
from app.utils import utcnow


def make_post(client, headers):
    """Alice creates a live post through the API and we return its id."""
    body = {
        "title": "Hello",
        "body": "My First Great post!",
        "topics": ["Tech"],
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    return client.post("/posts", json=body, headers=headers).json()["post_id"]


def expire(db, post_id):
    """Push an existing post into the past (the API itself refuses past dates)."""
    post = db.get(Post, post_id)
    post.created_at = utcnow() - timedelta(days=2)
    post.expires_at = utcnow() - timedelta(days=1)
    db.commit()


def react(client, post_id, headers, reaction="like"):
    return client.put(f"/posts/{post_id}/reaction", json={"type": reaction}, headers=headers)


def comment(client, post_id, headers, text="Nice post"):
    return client.post(f"/posts/{post_id}/comments", json={"body": text}, headers=headers)


# ====================== reactions ======================

def test_like_increases_like_count(client, auth_headers, other_auth_headers):
    # Bob likes Alice's post: the response shows 1 like and 0 dislikes.
    pid = make_post(client, auth_headers)
    r = react(client, pid, other_auth_headers, "like")
    assert r.status_code == 200
    assert r.json()["likes"] == 1 and r.json()["dislikes"] == 0


def test_dislike_increases_dislike_count(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    body = react(client, pid, other_auth_headers, "dislike").json()
    assert body["likes"] == 0 and body["dislikes"] == 1


def test_repeating_same_reaction_does_not_increase_count(client, db_session, auth_headers, other_auth_headers):
    # Liking five times still counts once, and only one row is stored.
    pid = make_post(client, auth_headers)
    for _ in range(5):
        body = react(client, pid, other_auth_headers, "like").json()
    assert body["likes"] == 1
    assert db_session.query(Reaction).filter_by(post_id=pid).count() == 1


def test_switching_like_to_dislike_replaces_reaction(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    react(client, pid, other_auth_headers, "like")
    body = react(client, pid, other_auth_headers, "dislike").json()
    assert body["likes"] == 0 and body["dislikes"] == 1  # the like is gone
    assert db_session.query(Reaction).filter_by(post_id=pid).count() == 1


def test_switching_dislike_to_like_replaces_reaction(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    react(client, pid, other_auth_headers, "dislike")
    body = react(client, pid, other_auth_headers, "like").json()
    assert body["likes"] == 1 and body["dislikes"] == 0


def test_only_one_reaction_per_user_per_post_after_many_changes(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    for kind in ["like", "dislike", "like", "like", "dislike"]:
        react(client, pid, other_auth_headers, kind)
    assert db_session.query(Reaction).filter_by(post_id=pid).count() == 1


def test_different_users_reactions_are_counted_separately(client, auth_headers, other_auth_headers):
    # Carol joins, so two users react to Alice's post.
    client.post("/auth/register", json={"username": "carol", "email": "carol@example.com", "password": "S3cret-pass"})
    token = client.post("/auth/login", data={"username": "carol", "password": "S3cret-pass"}).json()["access_token"]
    carol = {"Authorization": f"Bearer {token}"}
    pid = make_post(client, auth_headers)
    react(client, pid, other_auth_headers, "like")
    body = react(client, pid, carol, "dislike").json()
    assert body["likes"] == 1 and body["dislikes"] == 1


def test_author_cannot_like_own_post(client, auth_headers):
    pid = make_post(client, auth_headers)
    assert react(client, pid, auth_headers, "like").status_code == 403


def test_author_cannot_dislike_own_post(client, auth_headers):
    pid = make_post(client, auth_headers)
    assert react(client, pid, auth_headers, "dislike").status_code == 403


def test_rejected_author_reaction_changes_nothing(client, db_session, auth_headers):
    pid = make_post(client, auth_headers)
    react(client, pid, auth_headers, "like")
    assert db_session.query(Reaction).count() == 0
    assert client.get(f"/posts/{pid}", headers=auth_headers).json()["likes"] == 0


def test_reaction_user_comes_from_token_not_body(client, db_session, auth_headers, other_auth_headers):
    # A spoofed user_id in the body is ignored: the reaction belongs to Bob (user 2).
    pid = make_post(client, auth_headers)
    client.put(f"/posts/{pid}/reaction", json={"type": "like", "user_id": 1}, headers=other_auth_headers)
    assert db_session.query(Reaction).one().user_id == 2


def test_invalid_reaction_type_rejected(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    assert react(client, pid, other_auth_headers, "love").status_code == 422


def test_missing_reaction_type_rejected(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    r = client.put(f"/posts/{pid}/reaction", json={}, headers=other_auth_headers)
    assert r.status_code == 422


def test_reaction_requires_token(client, auth_headers):
    pid = make_post(client, auth_headers)
    assert client.put(f"/posts/{pid}/reaction", json={"type": "like"}).status_code == 401


def test_reaction_on_unknown_post_is_404(client, other_auth_headers):
    assert react(client, 999, other_auth_headers).status_code == 404


def test_reaction_counts_show_when_reading_the_post(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    react(client, pid, other_auth_headers, "like")
    body = client.get(f"/posts/{pid}", headers=auth_headers).json()
    assert body["likes"] == 1 and body["dislikes"] == 0


# ====================== comments ======================

def test_add_comment_records_author_content_and_timestamp(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    r = comment(client, pid, other_auth_headers, "Great read")
    assert r.status_code == 201
    body = r.json()
    assert body["author"]["username"] == "bob"
    assert body["body"] == "Great read"
    assert body["created_at"]
    assert body["comment_id"] == 1


def test_comment_author_comes_from_token_not_body(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    client.post(f"/posts/{pid}/comments", json={"body": "hi", "user_id": 1}, headers=other_auth_headers)
    assert db_session.query(Comment).one().user_id == 2


def test_author_may_comment_on_own_live_post(client, auth_headers):
    pid = make_post(client, auth_headers)
    r = comment(client, pid, auth_headers, "Adding a note")
    assert r.status_code == 201 and r.json()["author"]["username"] == "alice"


def test_one_user_can_add_multiple_comments(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    for text in ["first", "second", "third"]:
        assert comment(client, pid, other_auth_headers, text).status_code == 201
    assert db_session.query(Comment).filter_by(user_id=2).count() == 3


def test_comments_appear_on_the_post_oldest_first(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    comment(client, pid, other_auth_headers, "first")
    comment(client, pid, auth_headers, "second")
    comments = client.get(f"/posts/{pid}", headers=auth_headers).json()["comments"]
    assert [(c["body"], c["author"]["username"]) for c in comments] == [("first", "bob"), ("second", "alice")]


def test_blank_comment_rejected(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    assert comment(client, pid, other_auth_headers, "   ").status_code == 422
    assert comment(client, pid, other_auth_headers, "").status_code == 422


def test_comment_is_trimmed(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    assert comment(client, pid, other_auth_headers, "  hello  ").json()["body"] == "hello"


def test_missing_comment_body_rejected(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    assert client.post(f"/posts/{pid}/comments", json={}, headers=other_auth_headers).status_code == 422


def test_comment_requires_token(client, auth_headers):
    pid = make_post(client, auth_headers)
    assert client.post(f"/posts/{pid}/comments", json={"body": "hi"}).status_code == 401


def test_comment_on_unknown_post_is_404(client, other_auth_headers):
    assert comment(client, 999, other_auth_headers).status_code == 404


# ====================== expired posts accept no interactions ======================

def test_cannot_react_to_expired_post(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    expire(db_session, pid)
    assert react(client, pid, other_auth_headers, "like").status_code == 409
    assert db_session.query(Reaction).count() == 0


def test_cannot_switch_reaction_after_expiry(client, db_session, auth_headers, other_auth_headers):
    # Bob liked while the post was live; after expiry he cannot change it.
    pid = make_post(client, auth_headers)
    react(client, pid, other_auth_headers, "like")
    expire(db_session, pid)
    assert react(client, pid, other_auth_headers, "dislike").status_code == 409
    body = client.get(f"/posts/{pid}", headers=other_auth_headers).json()
    assert body["likes"] == 1 and body["dislikes"] == 0  # unchanged, still readable


def test_cannot_comment_on_expired_post(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    expire(db_session, pid)
    assert comment(client, pid, other_auth_headers).status_code == 409
    assert db_session.query(Comment).count() == 0


def test_author_cannot_comment_on_own_expired_post(client, db_session, auth_headers):
    pid = make_post(client, auth_headers)
    expire(db_session, pid)
    assert comment(client, pid, auth_headers).status_code == 409


def test_interactions_stop_the_moment_the_post_expires(client, db_session, auth_headers, other_auth_headers):
    # Same post: allowed while live, refused after it expires.
    pid = make_post(client, auth_headers)
    assert comment(client, pid, other_auth_headers, "before").status_code == 201
    assert react(client, pid, other_auth_headers, "like").status_code == 200
    expire(db_session, pid)
    assert comment(client, pid, other_auth_headers, "after").status_code == 409
    assert react(client, pid, other_auth_headers, "dislike").status_code == 409
    post = client.get(f"/posts/{pid}", headers=other_auth_headers).json()
    assert post["status"] == "Expired"
    assert [c["body"] for c in post["comments"]] == ["before"]  # history preserved