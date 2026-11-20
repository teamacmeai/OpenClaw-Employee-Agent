from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "OpenClaw Employee Activity Agent"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/openclaw"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
