# Tests for the posts and topics requirements.
from datetime import datetime, timedelta, timezone

from app.models import Post, Topic
from app.utils import utcnow


def future(hours=24):
    """An ISO expiry time in the future, with a timezone, as a client would send it."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def new_post(**overrides):
    body = {"title": "Hello", "body": "First post", "topics": ["Tech"], "expires_at": future()}
    body.update(overrides)
    return body


def make_expired_post(db, author_id=1, topics=("Tech",)):
    """Insert an already expired post directly (the API refuses to create one)."""
    t = [db.query(Topic).filter_by(name=n).one() for n in topics]
    post = Post(user_id=author_id, title="Old news", body="Expired body", topics=t,
                created_at=utcnow() - timedelta(days=2), expires_at=utcnow() - timedelta(days=1))
    db.add(post)
    db.commit()
    return post


# ---------- creating posts ----------

def test_create_post_success(client, auth_headers):
    # Creation returns 201 and every field the requirement lists.
    r = client.post("/posts", json=new_post(), headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["post_id"] == 1
    assert body["author"]["username"] == "alice"
    assert body["title"] == "Hello" and body["body"] == "First post"
    assert body["topics"] == ["Tech"]
    assert body["created_at"] and body["expires_at"]
    assert body["status"] == "Live"


def test_new_post_starts_with_zero_counts_and_no_comments(client, auth_headers):
    body = client.post("/posts", json=new_post(), headers=auth_headers).json()
    assert body["likes"] == 0 and body["dislikes"] == 0
    assert body["comments"] == []


def test_server_generates_id_author_and_timestamp(client, auth_headers):
    # Fields the client must not control are ignored if sent.
    spoof = new_post(user_id=999, post_id=500, created_at="2000-01-01T00:00:00")
    body = client.post("/posts", json=spoof, headers=auth_headers).json()
    assert body["post_id"] == 1
    assert body["author"]["user_id"] == 1
    assert not body["created_at"].startswith("2000")


def test_post_ids_are_increasing_integers(client, auth_headers):
    first = client.post("/posts", json=new_post(), headers=auth_headers).json()
    second = client.post("/posts", json=new_post(), headers=auth_headers).json()
    assert isinstance(first["post_id"], int) and second["post_id"] == first["post_id"] + 1


def test_post_with_naive_expiry_is_read_as_utc(client, auth_headers):
    naive = (utcnow() + timedelta(hours=2)).isoformat()
    r = client.post("/posts", json=new_post(expires_at=naive), headers=auth_headers)
    assert r.status_code == 201


# ---------- validation ----------

def test_blank_title_rejected(client, auth_headers):
    assert client.post("/posts", json=new_post(title="   "), headers=auth_headers).status_code == 422


def test_blank_body_rejected(client, auth_headers):
    assert client.post("/posts", json=new_post(body=""), headers=auth_headers).status_code == 422


def test_title_and_body_are_trimmed(client, auth_headers):
    body = client.post("/posts", json=new_post(title="  Hi  ", body="  text "), headers=auth_headers).json()
    assert body["title"] == "Hi" and body["body"] == "text"


def test_post_needs_at_least_one_topic(client, auth_headers):
    assert client.post("/posts", json=new_post(topics=[]), headers=auth_headers).status_code == 422


def test_unknown_topic_rejected(client, auth_headers):
    r = client.post("/posts", json=new_post(topics=["Cooking"]), headers=auth_headers)
    assert r.status_code == 422


def test_topic_names_are_case_sensitive(client, auth_headers):
    # "Use these topic names consistently": only the exact spelling is accepted.
    assert client.post("/posts", json=new_post(topics=["tech"]), headers=auth_headers).status_code == 422


def test_expiry_in_the_past_rejected(client, auth_headers):
    r = client.post("/posts", json=new_post(expires_at=future(hours=-1)), headers=auth_headers)
    assert r.status_code == 422


def test_missing_expiry_rejected(client, auth_headers):
    body = new_post()
    del body["expires_at"]
    assert client.post("/posts", json=body, headers=auth_headers).status_code == 422


def test_duplicate_topics_are_collapsed(client, auth_headers):
    body = client.post("/posts", json=new_post(topics=["Tech", "Tech"]), headers=auth_headers).json()
    assert body["topics"] == ["Tech"]


# ---------- authentication ----------

def test_create_requires_token(client):
    assert client.post("/posts", json=new_post()).status_code == 401


def test_read_endpoints_require_token(client, auth_headers):
    client.post("/posts", json=new_post(), headers=auth_headers)
    assert client.get("/posts").status_code == 401
    assert client.get("/posts/1").status_code == 401
    assert client.get("/topics").status_code == 401


# ---------- reading and browsing ----------

def test_get_single_post(client, auth_headers):
    client.post("/posts", json=new_post(), headers=auth_headers)
    r = client.get("/posts/1", headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "Hello"


def test_get_unknown_post_is_404(client, auth_headers):
    assert client.get("/posts/999", headers=auth_headers).status_code == 404


def test_multi_topic_post_appears_under_each_of_its_topics(client, auth_headers):
    client.post("/posts", json=new_post(title="Both", topics=["Tech", "Health"]), headers=auth_headers)
    client.post("/posts", json=new_post(title="Only sport", topics=["Sport"]), headers=auth_headers)

    def titles(topic):
        r = client.get("/posts", params={"topic": topic}, headers=auth_headers)
        return [p["title"] for p in r.json()]

    assert titles("Tech") == ["Both"]
    assert titles("Health") == ["Both"]
    assert titles("Sport") == ["Only sport"]
    assert titles("Politics") == []


def test_list_without_topic_returns_everything_newest_first(client, auth_headers):
    for n in range(3):
        client.post("/posts", json=new_post(title=f"post {n}"), headers=auth_headers)
    titles = [p["title"] for p in client.get("/posts", headers=auth_headers).json()]
    assert titles == ["post 2", "post 1", "post 0"]


def test_invalid_topic_filter_rejected(client, auth_headers):
    assert client.get("/posts", params={"topic": "Cooking"}, headers=auth_headers).status_code == 422


def test_topics_endpoint_lists_the_four_fixed_topics(client, auth_headers):
    names = [t["name"] for t in client.get("/topics", headers=auth_headers).json()]
    assert names == ["Politics", "Health", "Sport", "Tech"]


# ---------- expired posts stay readable ----------

def test_expired_post_is_readable_by_any_authenticated_user(client, db_session, auth_headers, other_auth_headers):
    # Alice (user 1) owns the expired post; Bob (user 2) reads it.
    make_expired_post(db_session, author_id=1)
    r = client.get("/posts/1", headers=other_auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "Expired"


def test_expired_post_appears_in_topic_browsing(client, db_session, auth_headers):
    make_expired_post(db_session, topics=("Tech", "Sport"))
    r = client.get("/posts", params={"topic": "Sport"}, headers=auth_headers)
    assert [p["status"] for p in r.json()] == ["Expired"]


def test_live_post_reports_live(client, auth_headers):
    client.post("/posts", json=new_post(), headers=auth_headers)
    assert client.get("/posts/1", headers=auth_headers).json()["status"] == "Live"