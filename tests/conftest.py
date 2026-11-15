import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.models  
from app.main import app


# A fixture is a setup helper. Any test that lists "db_session" as a
# parameter receives the value yielded below.
@pytest.fixture
def db_session():
    # A throwaway database that lives only in memory, so tests never
    # touch the real piazza.db file.
    # StaticPool makes every connection share the same in-memory database.
    # Without it, each new connection would see an empty one.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Same foreign key switch as in database.py. This engine is a
    # different one, so it needs its own copy.
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    # Build all the tables in the empty test database.
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db  # the test runs here, using this session
    finally:
        # Cleanup after each test, so the next test starts from scratch.
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

@pytest.fixture
def client(db_session):
    # Replacement for get_db: hand out the test session instead of the
    # real database session.
    def override_get_db():
        yield db_session

    # Tell FastAPI to use the replacement whenever a route asks for get_db.
    app.dependency_overrides[get_db] = override_get_db
    # No "with" block on purpose: that would trigger the startup code
    # and create tables in the real piazza.db.
    yield TestClient(app)
    # Remove the replacement so it cannot leak into other tests.
    app.dependency_overrides.clear()