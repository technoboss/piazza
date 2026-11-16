from datetime import timedelta

import jwt

from app.config import settings
from app.security import create_access_token


# ---------- login ----------

def test_login_with_email_returns_token(client, registered_user):
    # Login by email returns a bearer token with a lifetime.
    response = client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == settings.access_token_expire_minutes * 60


def test_login_with_username_also_works(client, registered_user):
    response = client.post(
        "/auth/login",
        data={"username": registered_user["username"], "password": registered_user["password"]},
    )
    assert response.status_code == 200


def test_token_contains_user_and_future_expiry(client, registered_user):
    # Decode the token: it identifies the user and carries an expiry in the future.
    response = client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    payload = jwt.decode(
        response.json()["access_token"], settings.secret_key, algorithms=[settings.algorithm]
    )
    assert payload["sub"] == "1"
    assert payload["exp"] > payload["iat"]


def test_login_wrong_password_rejected(client, registered_user):
    response = client.post(
        "/auth/login", data={"username": registered_user["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_unknown_user_gets_same_error(client, registered_user):
    # Same message as a wrong password, so registered emails cannot be guessed.
    wrong_pw = client.post(
        "/auth/login", data={"username": registered_user["email"], "password": "wrong-password"}
    )
    unknown = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "whatever-123"}
    )
    assert unknown.status_code == 401
    assert unknown.json() == wrong_pw.json()


def test_login_response_hides_hash(client, registered_user):
    body = client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    ).json()
    assert "pwd_hash" not in body and "password" not in body


# ---------- bearer token protection (via GET /auth/me) ----------

def test_protected_route_with_valid_token(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert "pwd_hash" not in response.json()


def test_protected_route_without_token_rejected(client):
    # No Authorization header at all.
    assert client.get("/auth/me").status_code == 401


def test_protected_route_with_garbage_token_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_protected_route_with_expired_token_rejected(client, registered_user):
    # A token that expired one minute ago.
    token = create_access_token(1, expires_delta=timedelta(minutes=-1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_protected_route_with_wrong_signature_rejected(client, registered_user):
    # Signed with a different secret, so it must be refused.
    forged = jwt.encode({"sub": "1", "exp": 9999999999}, "another-secret-key-0123456789abcdefghij", algorithm="HS256")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_protected_route_with_wrong_scheme_rejected(client, auth_headers):
    # "Basic ..." instead of "Bearer ...".
    token = auth_headers["Authorization"].split()[1]
    response = client.get("/auth/me", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 401


def test_token_for_deleted_user_rejected(client):
    # Valid signature and expiry, but user 999 does not exist.
    token = create_access_token(999)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_health_and_docs_stay_public(client):
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200