from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # project root

class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./piazza.db"
    default_post_lifetime_minutes: int = 60

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")

settings = Settings()