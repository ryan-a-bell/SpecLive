"""Typed domain entities (Pydantic v2 models).

These are the canonical in-memory representations used by services. Persistence
(SQLAlchemy) and transport (API schemas) map to/from these but do not replace
them. Entities carry no framework or provider dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    ArtifactStatus,
    ArtifactType,
    BranchStatus,
    ConversationNodeType,
    DerivationMethod,
    EvidenceRelationship,
    SessionStatus,
    Speaker,
    SpeakerSource,
    ValidationState,
)


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=False)


class DiscoverySession(DomainModel):
    id: str = Field(default_factory=_uuid)
    title: str
    customer: str
    facilitator: str
    status: SessionStatus = SessionStatus.DRAFT
    started_at: datetime | None = None
    ended_at: datetime | None = None
    script_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class TranscriptSegment(DomainModel):
    id: str = Field(default_factory=_uuid)
    session_id: str
    sequence_number: int
    speaker: Speaker
    speaker_id: str | None = None
    speaker_name: str | None = None
    speaker_source: SpeakerSource = SpeakerSource.UNKNOWN
    speaker_confidence: float | None = None
    start_time: float | None = None  # seconds from session start
    end_time: float | None = None
    text: str
    is_final: bool = True
    created_at: datetime = Field(default_factory=_now)


class DiscoveryArtifact(DomainModel):
    id: str = Field(default_factory=_uuid)
    session_id: str
    artifact_type: ArtifactType
    title: str
    statement: str
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    confidence: float = 0.0  # 0.0–1.0
    validation_state: ValidationState = ValidationState.DETECTED
    derivation_method: DerivationMethod = DerivationMethod.MANUAL
    parent_id: str | None = None
    branch_id: str | None = None
    rationale: str | None = None
    superseded_by: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class EvidenceLink(DomainModel):
    id: str = Field(default_factory=_uuid)
    artifact_id: str
    transcript_segment_id: str
    quote_start: int  # character offset within the segment text
    quote_end: int
    quoted_text: str
    relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTING
    confidence: float = 0.0
    rationale: str | None = None
    created_at: datetime = Field(default_factory=_now)


class ScriptStage(DomainModel):
    id: str = Field(default_factory=_uuid)
    script_id: str
    sequence: int
    title: str
    objective: str
    primary_prompt: str
    alternative_prompts: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)


class ScriptDefinition(DomainModel):
    id: str = Field(default_factory=_uuid)
    name: str
    version: str = "1.0.0"
    description: str = ""
    archived: bool = False
    stages: list[ScriptStage] = Field(default_factory=list)


class ConversationBranch(DomainModel):
    id: str = Field(default_factory=_uuid)
    session_id: str
    parent_branch_id: str | None = None
    source_stage_id: str | None = None
    name: str
    topic: str
    status: BranchStatus = BranchStatus.OPEN
    created_from_segment_id: str | None = None
    merge_target_stage_id: str | None = None
    created_at: datetime = Field(default_factory=_now)


class ConversationNode(DomainModel):
    id: str = Field(default_factory=_uuid)
    branch_id: str
    node_type: ConversationNodeType
    label: str
    transcript_segment_id: str | None = None
    artifact_id: str | None = None
    parent_node_id: str | None = None
    sequence: int = 0
    created_at: datetime = Field(default_factory=_now)


class ArtifactRevision(DomainModel):
    id: str = Field(default_factory=_uuid)
    artifact_id: str
    revision_number: int
    previous_value: dict[str, object]
    new_value: dict[str, object]
    changed_by: str
    change_reason: str | None = None
    created_at: datetime = Field(default_factory=_now)
