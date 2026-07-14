"""Provider abstractions and their selection.

No provider-specific logic leaks into domain entities or services beyond these
interfaces (ADR-0004). Only mock implementations ship in this increment, so the
application runs with no external API keys.
"""

from app.config import get_settings
from app.providers.base import (
    ArtifactExporter,
    EmbeddingProvider,
    LanguageModelProvider,
    SpeechToTextProvider,
)
from app.providers.mock import (
    MockEmbeddingProvider,
    MockLanguageModelProvider,
    MockSpeechToTextProvider,
)

_STT = {"mock": MockSpeechToTextProvider}
_LLM = {"mock": MockLanguageModelProvider}
_EMBED = {"mock": MockEmbeddingProvider}


def get_stt_provider() -> SpeechToTextProvider:
    return _STT[get_settings().stt_provider]()


def get_llm_provider() -> LanguageModelProvider:
    return _LLM[get_settings().llm_provider]()


def get_embedding_provider() -> EmbeddingProvider:
    return _EMBED[get_settings().embedding_provider]()


__all__ = [
    "ArtifactExporter",
    "EmbeddingProvider",
    "LanguageModelProvider",
    "SpeechToTextProvider",
    "get_stt_provider",
    "get_llm_provider",
    "get_embedding_provider",
]
