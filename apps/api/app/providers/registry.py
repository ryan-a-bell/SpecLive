"""Provider registry — resolves configured providers to concrete instances.

A real vendor adapter registers here keyed by its id; the rest of the app only
ever asks for "the configured provider".
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from ..config import get_settings
from .base import EmbeddingProvider, LanguageModelProvider, SpeechToTextProvider
from .faster_whisper import FasterWhisperProvider
from .mock import (
    MockEmbeddingProvider,
    MockLanguageModelProvider,
    MockSpeechToTextProvider,
)
from .openai_realtime import OpenAIRealtimeProvider
from .replay import ReplaySpeechToTextProvider
from .wispr_flow import WisprFlowProvider

_LLM_PROVIDERS: dict[str, type[LanguageModelProvider]] = {"mock": MockLanguageModelProvider}
_EMBEDDING_PROVIDERS: dict[str, type[EmbeddingProvider]] = {"mock": MockEmbeddingProvider}


@lru_cache
def get_llm_provider() -> LanguageModelProvider:
    provider_id = get_settings().llm_provider
    cls = _LLM_PROVIDERS.get(provider_id)
    if cls is None:
        raise ValueError(f"Unsupported LLM provider: {provider_id}")
    return cls()


@lru_cache
def get_stt_provider() -> SpeechToTextProvider:
    settings = get_settings()
    def _replay() -> SpeechToTextProvider:
        if not settings.replay_script:
            raise ValueError("STT_PROVIDER=replay requires REPLAY_SCRIPT to be set")
        return ReplaySpeechToTextProvider(
            script_path=settings.replay_script,
            seconds_per_turn=settings.replay_seconds_per_turn,
        )

    factories: dict[str, Callable[[], SpeechToTextProvider]] = {
        "mock": MockSpeechToTextProvider,
        "replay": _replay,
        "local": lambda: FasterWhisperProvider(
            model_name=settings.faster_whisper_model,
            device=settings.faster_whisper_device,
            compute_type=settings.faster_whisper_compute_type,
            chunk_seconds=settings.faster_whisper_chunk_seconds,
            language=settings.stt_language,
        ),
        "faster-whisper": lambda: FasterWhisperProvider(
            model_name=settings.faster_whisper_model,
            device=settings.faster_whisper_device,
            compute_type=settings.faster_whisper_compute_type,
            chunk_seconds=settings.faster_whisper_chunk_seconds,
            language=settings.stt_language,
        ),
        "openai": lambda: OpenAIRealtimeProvider(
            api_key=settings.openai_api_key or "",
            model=settings.openai_realtime_model,
            websocket_url=settings.openai_realtime_url,
            language=settings.stt_language,
            prompt=settings.stt_prompt,
        ),
        "wispr": lambda: WisprFlowProvider(
            api_key=settings.wispr_flow_api_key or "",
            access_token=settings.wispr_flow_access_token or "",
            websocket_url=settings.wispr_flow_websocket_url,
            language=settings.stt_language,
        ),
        "wispr-flow": lambda: WisprFlowProvider(
            api_key=settings.wispr_flow_api_key or "",
            access_token=settings.wispr_flow_access_token or "",
            websocket_url=settings.wispr_flow_websocket_url,
            language=settings.stt_language,
        ),
    }
    factory = factories.get(settings.stt_provider)
    if factory is None:
        raise ValueError(f"Unsupported STT provider: {settings.stt_provider}")
    return factory()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider_id = get_settings().embedding_provider
    cls = _EMBEDDING_PROVIDERS.get(provider_id)
    if cls is None:
        raise ValueError(f"Unsupported embedding provider: {provider_id}")
    return cls()
