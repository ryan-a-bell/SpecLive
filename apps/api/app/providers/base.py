"""Provider interfaces.

These Protocols define the boundary between the application and external
services (speech-to-text, LLMs, embeddings, exporters). Implementations live in
sibling modules; the app never imports a concrete vendor SDK outside them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class TranscriptChunk:
    speaker: str
    text: str
    start_time: float
    end_time: float
    is_final: bool = True


@dataclass(slots=True)
class ArtifactCandidate:
    artifact_type: str
    title: str
    statement: str
    confidence: float
    rationale: str
    # Character offsets into the source segment text for the supporting quote.
    quote: str = ""
    quote_start: int = 0
    quote_end: int = 0
    relationship: str = "direct"


@runtime_checkable
class SpeechToTextProvider(Protocol):
    """Turns audio (or, in the mock, canned text) into transcript chunks."""

    async def transcribe(self, audio_ref: str) -> list[TranscriptChunk]: ...


@runtime_checkable
class LanguageModelProvider(Protocol):
    """Extracts candidate discovery artifacts from a transcript segment."""

    async def extract_artifacts(
        self, segment_text: str, speaker: str, context: str = ""
    ) -> list[ArtifactCandidate]: ...

    async def recommend_question(self, gaps: list[str], stage_prompt: str) -> str: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@runtime_checkable
class ArtifactExporter(Protocol):
    """Serializes a discovery package to a target format."""

    format: str
    content_type: str

    def export(self, package: dict) -> str: ...
