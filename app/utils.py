
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time WITHOUT tzinfo. SQLite returns naive datetimes, so every
    comparison in the app (expiry checks, status) must use the same naive-UTC form."""
    return datetime.now(timezone.utc).replace(tzinfo=None)