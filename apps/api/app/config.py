from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RDC_", env_file=".env", extra="ignore")

    app_name: str = "Requirements Discovery Copilot API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://rdc:rdc@localhost:5432/rdc"
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    # Provider selection; only "mock" implementations ship in this increment.
    stt_provider: str = "mock"
    llm_provider: str = "mock"
    embedding_provider: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
