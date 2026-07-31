from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. PostgreSQL is used in deployment; SQLite keeps the demo runnable."""

    model_config = SettingsConfigDict(env_file=Path(__file__).parents[1] / ".env", extra="ignore")

    database_url: str = "sqlite:///./subscription.db"
    jwt_secret: str = "development-secret-change-me-32-bytes"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    demo_mode: bool = True

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
