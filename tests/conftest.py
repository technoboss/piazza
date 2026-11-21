import os

# A throwaway key, so tests never depend on your real .env.
os.environ["SECRET_KEY"] = "test-secret-key-only-for-pytest-0123456789abcdef"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models
from app.main import app
from app.seed import seed_topics


@pytest.fixture
def db_session():
    # Throwaway in-memory database: the piazza.db is never touched.
    # StaticPool makes all connections share that one in-memory database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # This engine is a different one, so it needs its own foreign key switch.
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    seed_topics(db)
    try:
        yield db 
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    # Make routes use the test session instead of the real database.
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)  # no "with": that would run startup on the real database
    app.dependency_overrides.clear()


# Fixtures below are reused by every later protected-endpoint test.
@pytest.fixture
def registered_user(client):
    """Creates a user through the API and returns the credentials used."""
    creds = {"username": "alice", "email": "alice@example.com", "password": "S3cret-p@ss"}
    client.post("/auth/register", json=creds)
    return creds


@pytest.fixture
def auth_headers(client, registered_user):
    """Logs in and returns the Authorization header for protected requests."""
    response = client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

# A second logged-in user, to test reading other people's posts.
@pytest.fixture
def other_auth_headers(client):
    creds = {"username": "bob", "email": "bob@example.com", "password": "S3cret-pass"}
    client.post("/auth/register", json=creds)
    response = client.post("/auth/login", data={"username": creds["email"], "password": creds["password"]})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
