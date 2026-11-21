# Tests for expiry, UTC handling and the Live/Expired filter.
# Cast: alice (auth_headers) writes posts; bob (other_auth_headers) reacts and comments.
from datetime import datetime, timedelta, timezone

from app.models import Post, Topic
from app.services import is_expired
from app.utils import utcnow


def iso_future(hours=24):
    """A timezone-aware expiry in the future, written the way a client should send it."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def make_post(client, headers, title="Live post", topics=("Tech",), expires_at=None):
    body = {"title": title, "body": "text", "topics": list(topics),
            "expires_at": expires_at or iso_future()}
    return client.post("/posts", json=body, headers=headers).json()["post_id"]


def expire(db, post_id):
    """Push an existing post into the past (the API itself refuses past dates)."""
    post = db.get(Post, post_id)
    post.created_at = utcnow() - timedelta(days=2)
    post.expires_at = utcnow() - timedelta(days=1)
    db.commit()


def titles(client, headers, **params):
    return [p["title"] for p in client.get("/posts", params=params, headers=headers).json()]


# ====================== the expiry rule: current time >= expiry time ======================

def test_post_is_expired_exactly_at_its_expiry_time(monkeypatch):
    # Freeze "now" and test the boundary: equal counts as expired, one microsecond
    # earlier does not.
    now = datetime(2030, 1, 1, 12, 0, 0)
    monkeypatch.setattr("app.services.utcnow", lambda: now)
    assert is_expired(Post(expires_at=now)) is True
    assert is_expired(Post(expires_at=now + timedelta(microseconds=1))) is False
    assert is_expired(Post(expires_at=now - timedelta(microseconds=1))) is True


def test_status_is_live_before_and_expired_after(client, db_session, auth_headers):
    pid = make_post(client, auth_headers)
    assert client.get(f"/posts/{pid}", headers=auth_headers).json()["status"] == "Live"
    expire(db_session, pid)
    assert client.get(f"/posts/{pid}", headers=auth_headers).json()["status"] == "Expired"


# ====================== UTC and timezones ======================

def test_expiry_with_z_suffix_is_accepted(client, auth_headers):
    z = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = client.post("/posts", json={"title": "t", "body": "b", "topics": ["Tech"], "expires_at": z}, headers=auth_headers)
    assert r.status_code == 201


def test_expiry_with_offset_is_converted_to_utc(client, auth_headers):
    # 14:00 at +02:00 is 12:00 UTC.
    r = client.post("/posts", json={"title": "t", "body": "b", "topics": ["Tech"],
                                    "expires_at": "2030-06-01T14:00:00+02:00"}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["expires_at"] == "2030-06-01T12:00:00Z"


def test_expiry_without_timezone_is_rejected(client, auth_headers):
    r = client.post("/posts", json={"title": "t", "body": "b", "topics": ["Tech"],
                                    "expires_at": "2030-06-01T12:00:00"}, headers=auth_headers)
    assert r.status_code == 422


def test_date_only_expiry_is_rejected(client, auth_headers):
    r = client.post("/posts", json={"title": "t", "body": "b", "topics": ["Tech"],
                                    "expires_at": "2030-06-01"}, headers=auth_headers)
    assert r.status_code == 422


def test_expiry_is_compared_in_utc_not_by_clock_digits(client, auth_headers):
    # The instant is one hour AGO, but written at +05:00 its clock digits look like
    # four hours in the FUTURE. A naive comparison would accept it; UTC must refuse it.
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    plus5 = one_hour_ago.astimezone(timezone(timedelta(hours=5))).isoformat()
    r = client.post("/posts", json={"title": "t", "body": "b", "topics": ["Tech"], "expires_at": plus5}, headers=auth_headers)
    assert r.status_code == 422


def test_returned_timestamps_are_utc_with_z(client, auth_headers):
    pid = make_post(client, auth_headers)
    body = client.get(f"/posts/{pid}", headers=auth_headers).json()
    assert body["created_at"].endswith("Z") and body["expires_at"].endswith("Z")


def test_comment_and_user_timestamps_are_utc_with_z(client, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    c = client.post(f"/posts/{pid}/comments", json={"body": "hi"}, headers=other_auth_headers).json()
    assert c["created_at"].endswith("Z")
    assert client.get("/auth/me", headers=auth_headers).json()["registered_at"].endswith("Z")


# ====================== expired posts: readable, but closed ======================

def test_expired_post_keeps_its_reactions_and_comments(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    client.put(f"/posts/{pid}/reaction", json={"type": "like"}, headers=other_auth_headers)
    client.post(f"/posts/{pid}/comments", json={"body": "before expiry"}, headers=other_auth_headers)
    expire(db_session, pid)
    body = client.get(f"/posts/{pid}", headers=other_auth_headers).json()
    assert body["status"] == "Expired"
    assert body["likes"] == 1
    assert [c["body"] for c in body["comments"]] == ["before expiry"]


def test_repeating_the_same_reaction_on_an_expired_post_is_still_rejected(client, db_session, auth_headers, other_auth_headers):
    # Clarification: expiry blocks even a repeat that would leave the counts unchanged.
    pid = make_post(client, auth_headers)
    client.put(f"/posts/{pid}/reaction", json={"type": "like"}, headers=other_auth_headers)
    expire(db_session, pid)
    r = client.put(f"/posts/{pid}/reaction", json={"type": "like"}, headers=other_auth_headers)
    assert r.status_code == 409


def test_expired_post_rejects_new_reaction_and_comment(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers)
    expire(db_session, pid)
    assert client.put(f"/posts/{pid}/reaction", json={"type": "dislike"}, headers=other_auth_headers).status_code == 409
    assert client.post(f"/posts/{pid}/comments", json={"body": "late"}, headers=other_auth_headers).status_code == 409


# ====================== browsing with the status filter ======================

def setup_mixed_posts(client, db_session, headers):
    """Two live posts and two expired posts, spread over topics."""
    live_tech = make_post(client, headers, "live tech", ["Tech"])
    live_both = make_post(client, headers, "live tech+health", ["Tech", "Health"])
    old_tech = make_post(client, headers, "old tech", ["Tech"])
    old_sport = make_post(client, headers, "old sport", ["Sport"])
    expire(db_session, old_tech)
    expire(db_session, old_sport)
    return live_tech, live_both, old_tech, old_sport


def test_no_status_filter_returns_live_and_expired(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    assert sorted(titles(client, auth_headers, topic="Tech")) == ["live tech", "live tech+health", "old tech"]


def test_status_live_returns_only_live_posts(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    assert sorted(titles(client, auth_headers, topic="Tech", status="Live")) == ["live tech", "live tech+health"]


def test_status_expired_returns_only_expired_posts(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    assert titles(client, auth_headers, topic="Tech", status="Expired") == ["old tech"]


def test_status_filter_works_without_a_topic(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    assert sorted(titles(client, auth_headers, status="Expired")) == ["old sport", "old tech"]
    assert len(titles(client, auth_headers)) == 4


def test_status_filter_on_a_topic_with_no_matches_is_empty(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    assert titles(client, auth_headers, topic="Politics", status="Expired") == []
    assert titles(client, auth_headers, topic="Sport", status="Live") == []


def test_multi_topic_live_post_appears_under_each_topic_with_live_filter(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    assert titles(client, auth_headers, topic="Health", status="Live") == ["live tech+health"]


def test_every_returned_post_matches_the_requested_status(client, db_session, auth_headers):
    setup_mixed_posts(client, db_session, auth_headers)
    for wanted in ["Live", "Expired"]:
        posts = client.get("/posts", params={"status": wanted}, headers=auth_headers).json()
        assert posts and all(p["status"] == wanted for p in posts)


def test_invalid_status_value_is_rejected(client, auth_headers):
    assert client.get("/posts", params={"status": "expired"}, headers=auth_headers).status_code == 422
    assert client.get("/posts", params={"status": "Active"}, headers=auth_headers).status_code == 422


def test_status_filter_needs_a_token(client):
    assert client.get("/posts", params={"status": "Live"}).status_code == 401


def test_filtered_expired_posts_still_show_their_counts_and_comments(client, db_session, auth_headers, other_auth_headers):
    pid = make_post(client, auth_headers, "history")
    client.put(f"/posts/{pid}/reaction", json={"type": "dislike"}, headers=other_auth_headers)
    client.post(f"/posts/{pid}/comments", json={"body": "kept"}, headers=other_auth_headers)
    expire(db_session, pid)
    post = client.get("/posts", params={"status": "Expired"}, headers=other_auth_headers).json()[0]
    assert post["dislikes"] == 1 and [c["body"] for c in post["comments"]] == ["kept"]