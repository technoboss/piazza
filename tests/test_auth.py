from app.models import User

# A valid registration payload reused by the tests below.
VALID = {"username": "alice", "email": "alice@example.com", "password": "S3cret-pass"}


def test_register_success(client):
    # A valid payload creates the user: 201 Created, with the public fields returned.
    response = client.post("/auth/register", json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "user_id" in body and "registered_at" in body


def test_register_response_hides_password_and_hash(client):
    # The response must never contain the password or its hash.
    body = client.post("/auth/register", json=VALID).json()
    assert "password" not in body
    assert "pwd_hash" not in body
    assert "S3cret-pass" not in str(body)


def test_password_is_stored_hashed(client, db_session):
    # Look inside the database: the stored value must be an argon2 hash,
    # not the plaintext password.
    client.post("/auth/register", json=VALID)
    user = db_session.query(User).filter_by(username="alice").one()
    assert user.pwd_hash != "S3cret-pass"
    assert user.pwd_hash.startswith("$argon2")


def test_duplicate_email_rejected_case_insensitive(client):
    # Same email in a different case, with a new username, is still a duplicate: 409.
    client.post("/auth/register", json=VALID)
    other = {**VALID, "username": "bob", "email": "ALICE@example.com"}
    response = client.post("/auth/register", json=other)
    assert response.status_code == 409


def test_duplicate_username_rejected(client):
    # Same username with a different email is rejected: 409.
    client.post("/auth/register", json=VALID)
    other = {**VALID, "email": "other@example.com"}
    response = client.post("/auth/register", json=other)
    assert response.status_code == 409


def test_invalid_email_rejected(client):
    # Pydantic rejects a malformed email before the endpoint code runs: 422.
    response = client.post("/auth/register", json={**VALID, "email": "not-an-email"})
    assert response.status_code == 422


def test_short_password_rejected(client):
    # Passwords under 8 characters fail validation: 422.
    response = client.post("/auth/register", json={**VALID, "password": "short"})
    assert response.status_code == 422


def test_missing_field_rejected(client):
    # A request without email and password fails validation: 422.
    response = client.post("/auth/register", json={"username": "alice"})
    assert response.status_code == 422