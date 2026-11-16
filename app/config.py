from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # project root, where .env lives


class Settings(BaseSettings):
    secret_key: str  # required: the app refuses to start without it
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./piazza.db"
    default_post_lifetime_minutes: int = 60  # used by the posts endpoint in Step 3

    # extra="ignore": unknown entries in .env will no longer crash the app.
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


settings = Settings() 