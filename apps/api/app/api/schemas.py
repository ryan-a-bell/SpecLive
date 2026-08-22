"""Request/response schemas for the REST API.

These are transport DTOs. They reference the domain enums but keep the wire shape
explicit and stable, decoupled from ORM/domain internals.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..domain.enums import (
    ArtifactType,
    EvidenceRelationship,
    SessionStatus,
    Speaker,
    SpeakerSource,
    ValidationState,
)


# --- sessions -------------------------------------------------------------
class SessionCreate(BaseModel):
    title: str
    customer: str
    facilitator: str
    script_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class SessionPatch(BaseModel):
    title: str | None = None
    status: SessionStatus | None = None
    script_id: str | None = None
    metadata: dict | None = None


# --- transcript -----------------------------------------------------------
class TranscriptSegmentCreate(BaseModel):
    speaker: Speaker
    text: str
    start_time: float | None = None
    end_time: float | None = None
    is_final: bool = True
    sequence_number: int | None = None
    speaker_id: str | None = None
    speaker_name: str | None = None
    speaker_source: SpeakerSource = SpeakerSource.MANUAL
    speaker_confidence: float | None = None


class TranscriptSpeakerCorrection(BaseModel):
    speaker: Speaker
    speaker_name: str = Field(min_length=1, max_length=255)
    apply_to_voice: bool = True


class TranscriptionAudioFormat(BaseModel):
    encoding: str = "pcm_s16le"
    sample_rate: int = 16000
    channels: int = 1


class TranscriptionCapability(BaseModel):
    available: bool
    supports_partials: bool
    supports_speaker_detection: bool
    audio: TranscriptionAudioFormat = Field(default_factory=TranscriptionAudioFormat)
    max_frame_seconds: int = 5


class FileTranscriptionResult(BaseModel):
    """Outcome of transcribing an uploaded recording (non-streaming)."""

    session_id: str
    source_filename: str | None = None
    audio_seconds: float
    segment_count: int
    segments: list[dict] = Field(default_factory=list)


class AnalysisSettingsInfo(BaseModel):
    """Read-only view of the deployment's requirement-derivation configuration.

    Deliberately excludes any secret (notably ``LLM_API_KEY``): this reports
    *what mode/provider is active* so the UI can show it, never credentials.
    Config is env-var-driven and immutable at runtime, so there is no PATCH
    counterpart — see GitHub issue on whether these should become editable.
    """

    context_mode: str
    window_seconds: float
    auto_analyze: bool
    llm_provider: str
    # Only populated for the openai_compatible provider; the base URL and model
    # are non-secret configuration, the API key is never included.
    llm_api_base: str | None = None
    llm_model: str | None = None


# --- artifacts ------------------------------------------------------------
class ArtifactCreate(BaseModel):
    artifact_type: ArtifactType
    title: str
    statement: str
    confidence: float = 0.0
    rationale: str | None = None
    parent_id: str | None = None
    branch_id: str | None = None
    validation_state: ValidationState = ValidationState.DETECTED


class ArtifactPatch(BaseModel):
    title: str | None = None
    statement: str | None = None
    confidence: float | None = None
    rationale: str | None = None
    artifact_type: ArtifactType | None = None
    parent_id: str | None = None
    change_reason: str | None = None


class EvidenceCreate(BaseModel):
    transcript_segment_id: str
    quote_start: int
    quote_end: int
    quoted_text: str
    relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTING
    confidence: float = 0.0
    rationale: str | None = None


class MergeRequest(BaseModel):
    into_artifact_id: str


class RejectRequest(BaseModel):
    reason: str | None = None


class ConfirmRequest(BaseModel):
    changed_by: str = "facilitator"
