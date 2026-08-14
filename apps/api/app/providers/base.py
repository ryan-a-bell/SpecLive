"""Provider interfaces.

These Protocols/ABCs decouple the application from any single speech-to-text or
LLM vendor. Concrete adapters live alongside the provider-neutral ports.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import uuid4

from ..domain.enums import (
    ArtifactType,
    DerivationMethod,
    EvidenceRelationship,
)


@dataclass
class TranscriptEvent:
    """Provider-neutral partial or final transcription event."""

    text: str
    is_final: bool
    segment_id: str = field(default_factory=lambda: str(uuid4()))
    speaker: str | None = None
    start_time: float | None = None
    end_time: float | None = None


# Backwards-compatible name for integrations built against the original MVP.
TranscriptChunk = TranscriptEvent


@dataclass
class EvidenceCandidate:
    """Span within a segment that supports a candidate artifact."""

    quote_start: int
    quote_end: int
    quoted_text: str
    relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTING
    confidence: float = 0.5
    rationale: str | None = None


@dataclass
class ArtifactCandidate:
    """A proposed artifact produced by a LanguageModelProvider from a segment."""

    artifact_type: ArtifactType
    title: str
    statement: str
    confidence: float
    rationale: str
    evidence: list[EvidenceCandidate] = field(default_factory=list)
    derivation_method: DerivationMethod = DerivationMethod.KEYWORD_HEURISTIC


class SpeechToTextProvider(abc.ABC):
    """Consumes SpecLive PCM audio and emits normalized transcript events.

    ``pcm`` is always mono signed 16-bit little-endian PCM sampled at 16 kHz.
    Provider adapters own any vendor-specific framing or resampling.
    """

    @abc.abstractmethod
    async def start(self, session_id: str) -> None: ...

    @abc.abstractmethod
    async def push_audio(self, session_id: str, pcm: bytes) -> None: ...

    @abc.abstractmethod
    def events(self, session_id: str) -> AsyncIterator[TranscriptEvent]: ...

    @abc.abstractmethod
    async def stop(self, session_id: str) -> None: ...


class LanguageModelProvider(abc.ABC):
    """Derives candidate artifacts + evidence from transcript text."""

    @abc.abstractmethod
    def analyze_segment(self, text: str, *, speaker: str) -> list[ArtifactCandidate]: ...

    @abc.abstractmethod
    def recommend_questions(self, context: str, *, gaps: list[str]) -> list[str]: ...


class EmbeddingProvider(abc.ABC):
    """Produces vector embeddings for clustering/similarity."""

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class ArtifactExporter(abc.ABC):
    """Serializes a discovery package into a target format.

    New formats (CSV, DOCX, ReqIF, Jira, DOORS, SysML) implement this interface
    without touching the export service.
    """

    #: Short identifier, e.g. "json" or "markdown".
    format_id: str
    #: MIME type of the produced artifact.
    media_type: str

    @abc.abstractmethod
    def export(self, package: dict) -> str: ...
