"""Application configuration, loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings. No secrets are hard-coded here."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    # Persistence. SQLite fallback keeps tests/demo runnable without Postgres.
    database_url: str = "sqlite+pysqlite:///./copilot.db"

    # Event bus: "memory" (in-process) or "redis".
    event_bus: str = "memory"
    redis_url: str = "redis://redis:6379/0"

    # Provider selection. "mock" requires no external keys.
    stt_provider: str = "mock"
    llm_provider: str = "mock"
    embedding_provider: str = "mock"
    exporter: str = "default"

    # HTTP
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Privacy placeholders (see SECURITY.md)
    transcript_retention_days: int = 90
    enable_transcript_redaction: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""

    return Settings()
