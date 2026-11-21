from pathlib import Path

from sqlalchemy import create_engine, event  
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite file piazza.db, stored next to this file (app/piazza.db).
DATABASE_PATH = Path(__file__).resolve().parent / "piazza.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # lets FastAPI use SQLite across threads
)


# SQLite ignores foreign keys by default and the setting is per connection, 
# so it must be switched on each time.
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA foreign_keys = ON")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # every model in models.py inherits from this


def get_db():
    # One database session per request, closed afterwards.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
