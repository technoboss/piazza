from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import event

# Store users in a local SQLite file called auth.db.
DATABASE_PATH = Path(__file__).resolve().parent / "piazza.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine( DATABASE_URL, connect_args={"check_same_thread": False})

# this function runs PRAGMA foreign_keys = ON on every new database connection to enforce FK constraints
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _):
    dbapi_connection.execute("PRAGMA foreign_keys = ON")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    # Open one database session for the request.
    db = SessionLocal()
    try:
        yield db
    finally:
        # Close it after the request finishes.
        db.close()
