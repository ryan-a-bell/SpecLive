"""Provider abstractions and their mock implementations.

Providers are the only place external services (STT, LLM, embeddings, export)
may be integrated. Domain and services depend on the interfaces here, never on a
concrete SDK.
"""

from .base import (
    ArtifactCandidate,
    ArtifactExporter,
    EmbeddingProvider,
    EvidenceCandidate,
    LanguageModelProvider,
    SpeechToTextProvider,
    TranscriptChunk,
)
from .registry import get_embedding_provider, get_llm_provider, get_stt_provider

__all__ = [
    "ArtifactCandidate",
    "ArtifactExporter",
    "EmbeddingProvider",
    "EvidenceCandidate",
    "LanguageModelProvider",
    "SpeechToTextProvider",
    "TranscriptChunk",
    "get_embedding_provider",
    "get_llm_provider",
    "get_stt_provider",
]
