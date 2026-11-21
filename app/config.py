from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Each field is filled from the environment variable of the same name,
    # ignoring case: secret_key <- SECRET_KEY. Values are converted to the type.
    secret_key: str  # the app will refuse to start without it
    algorithm: str = "HS256"  # JWT signing algorithm
    access_token_expire_minutes: int = 60  # token lifetime
    database_url: str = "sqlite:///./piazza.db"  
    default_post_lifetime_minutes: int = 60  

    # Real environment variables override the .env file (Docker/GKE rely on this).
    # extra="ignore": unknown .env entries won't crash at startup.
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


# One shared instance, created once on first import: from app.config import settings
settings = Settings()
