import os

# Must be set before the app is imported, because settings are read at import time.
os.environ["SECRET_KEY"] = "test-secret-key-only-for-pytest-0123456789abcdef"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models  # noqa: F401  (registers the tables on Base)
from app.main import app


@pytest.fixture
def db_session():
    # In-memory database shared by all connections of this engine.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Creates a user through the API and returns the credentials used."""
    creds = {"username": "alice", "email": "alice@example.com", "password": "S3cret-pass"}
    client.post("/auth/register", json=creds)
    return creds


@pytest.fixture
def auth_headers(client, registered_user):
    """Logs in and returns the Authorization header. Reused by every protected-endpoint test."""
    response = client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}