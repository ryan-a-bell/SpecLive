"""Provider interfaces.

These Protocols/ABCs decouple the application from any single speech-to-text or
LLM vendor. Concrete adapters live alongside the provider-neutral ports.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import uuid4

from ..domain.entities import TranscriptSegment
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
    speaker_confidence: float | None = None
    start_time: float | None = None
    end_time: float | None = None


# Backwards-compatible name for integrations built against the original MVP.
TranscriptChunk = TranscriptEvent


@dataclass
class EvidenceCandidate:
    """Span within a segment that supports a candidate artifact.

    ``segment_id`` identifies which segment the quote came from. It is
    optional because a provider that only ever sees one segment at a time
    (e.g. ``MockLanguageModelProvider``) has nothing to disambiguate — the
    caller fills it in from context. A provider that reasons over a
    multi-segment :class:`AnalysisUnit` (e.g. an LLM-backed provider) should
    always set it explicitly, since the quote may come from any segment in
    the unit, not just the last one.
    """

    quote_start: int
    quote_end: int
    quoted_text: str
    relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTING
    confidence: float = 0.5
    rationale: str | None = None
    segment_id: str | None = None


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


@dataclass
class AnalysisUnit:
    """One or more transcript segments handed to a LanguageModelProvider in a
    single call. How segments get grouped into units is a policy decision
    (see ``app/services/context_strategy.py``): one unit per segment (no
    context), one unit per session (full transcript), or one unit per
    rolling time window are all valid strategies. The provider only sees
    what's in ``segments`` — it has no way to reach outside the unit.
    """

    segments: list[TranscriptSegment]

    @property
    def anchor(self) -> TranscriptSegment:
        """The most recent / primary segment in the unit — used as the
        default evidence target when a candidate doesn't specify one."""
        return self.segments[-1]


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

    def analyze_unit(self, unit: AnalysisUnit) -> list[ArtifactCandidate]:
        """Analyze a (possibly multi-segment) :class:`AnalysisUnit`.

        The default implementation is a graceful fallback for providers that
        have no notion of cross-segment context: it just calls
        ``analyze_segment`` once per segment in the unit and stamps each
        resulting evidence item with the segment it came from. This is what
        ``MockLanguageModelProvider`` gets automatically, so every context
        strategy (segment / window / full) keeps working even against a
        provider that can't actually use the extra context.

        A provider that *can* reason over multiple segments at once (e.g. a
        real LLM) should override this directly instead of implementing
        ``analyze_segment`` in terms of it — see
        ``OpenAICompatibleLanguageModelProvider``.
        """

        produced: list[ArtifactCandidate] = []
        for segment in unit.segments:
            candidates = self.analyze_segment(segment.text, speaker=segment.speaker)
            for candidate in candidates:
                for ev in candidate.evidence:
                    if ev.segment_id is None:
                        ev.segment_id = segment.id
            produced.extend(candidates)
        return produced

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
