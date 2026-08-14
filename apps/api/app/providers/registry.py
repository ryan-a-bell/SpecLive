"""Provider registry — resolves configured providers to concrete instances.

A real vendor adapter registers here keyed by its id; the rest of the app only
ever asks for "the configured provider".
"""

from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import EmbeddingProvider, LanguageModelProvider, SpeechToTextProvider
from .mock import (
    MockEmbeddingProvider,
    MockLanguageModelProvider,
    MockSpeechToTextProvider,
)

_LLM_PROVIDERS: dict[str, type[LanguageModelProvider]] = {"mock": MockLanguageModelProvider}
_STT_PROVIDERS: dict[str, type[SpeechToTextProvider]] = {"mock": MockSpeechToTextProvider}
_EMBEDDING_PROVIDERS: dict[str, type[EmbeddingProvider]] = {"mock": MockEmbeddingProvider}


@lru_cache
def get_llm_provider() -> LanguageModelProvider:
    provider_id = get_settings().llm_provider
    cls = _LLM_PROVIDERS.get(provider_id, MockLanguageModelProvider)
    return cls()


@lru_cache
def get_stt_provider() -> SpeechToTextProvider:
    provider_id = get_settings().stt_provider
    cls = _STT_PROVIDERS.get(provider_id, MockSpeechToTextProvider)
    return cls()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider_id = get_settings().embedding_provider
    cls = _EMBEDDING_PROVIDERS.get(provider_id, MockEmbeddingProvider)
    return cls()
