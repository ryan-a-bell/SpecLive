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

    # Speech-to-text adapters. The browser always sends mono PCM16 at 16 kHz;
    # adapters handle provider-specific resampling and framing server-side.
    stt_language: str | None = None
    stt_prompt: str | None = None
    stt_speaker_detection: bool = False
    openai_api_key: str | None = None
    openai_realtime_model: str = "gpt-live-transcribe"
    openai_realtime_url: str = "wss://api.openai.com/v1/realtime"
    wispr_flow_api_key: str | None = None
    wispr_flow_access_token: str | None = None
    wispr_flow_websocket_url: str = "wss://platform-api.wisprflow.ai/api/v1/dash/ws"
    faster_whisper_model: str = "small.en"
    faster_whisper_device: str = "auto"
    faster_whisper_compute_type: str = "default"
    faster_whisper_chunk_seconds: float = 3.0
    # Scripted replay STT (test/demo only): emits a fixture conversation's turns
    # as anonymous *detected* voices, paced by incoming audio, so the auto
    # speaker-grouping and correction workflow can be exercised without a real
    # diarization engine. See scripts/README.md.
    replay_script: str | None = None
    replay_seconds_per_turn: float = 2.5

    # Analysis context strategy: how much surrounding transcript a
    # LanguageModelProvider sees per call. "segment" (default) = each
    # segment alone, matching the original per-turn heuristics; "window" =
    # consecutive segments grouped into ANALYSIS_WINDOW_SECONDS time-boxed
    # chunks; "full" = the whole session in one call. See
    # app/services/context_strategy.py.
    analysis_context_mode: str = "segment"
    analysis_window_seconds: float = 300.0

    # LLM provider selection. "mock" (default) is a deterministic
    # keyword/regex heuristic engine, no API key required.
    # "openai_compatible" speaks the OpenAI chat-completions wire format, so
    # it works unmodified against OpenAI itself, a local Ollama server, a
    # vLLM OpenAI-compatible server, Anthropic's OpenAI-compatible endpoint,
    # or anything else implementing that contract — point LLM_API_BASE at
    # whichever one you want. See app/providers/openai_compatible.py.
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 60.0

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
