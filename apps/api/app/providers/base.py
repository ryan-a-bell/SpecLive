"""Provider interfaces.

These Protocols/ABCs decouple the application from any single speech-to-text or
LLM vendor. Concrete adapters live alongside; the MVP ships mock adapters only.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from ..domain.enums import (
    ArtifactType,
    DerivationMethod,
    EvidenceRelationship,
)


@dataclass
class TranscriptChunk:
    """A streamed transcription fragment from an STT provider."""

    text: str
    speaker: str
    start_time: float
    end_time: float
    is_final: bool = True


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
    """Streams transcript chunks from an audio source."""

    @abc.abstractmethod
    def stream(self, session_id: str) -> AsyncIterator[TranscriptChunk]: ...


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
