"""Pydantic request/response schemas — the API contract layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    ArtifactStatus,
    ArtifactType,
    BranchStatus,
    CoverageState,
    DerivationMethod,
    EvidenceRelationship,
    NodeType,
    SegmentStatus,
    SessionStatus,
    ValidationState,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Sessions -------------------------------------------------------------


class SessionCreate(BaseModel):
    title: str
    customer: str
    facilitator: str
    script_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    title: str | None = None
    status: SessionStatus | None = None
    current_stage_sequence: int | None = None


class SessionStats(BaseModel):
    segment_count: int = 0
    artifact_count: int = 0
    candidate_requirement_count: int = 0
    confirmed_requirement_count: int = 0
    evidence_link_count: int = 0
    open_question_count: int = 0
    coverage_percent: int = 0


class SessionRead(ORMModel):
    id: str
    title: str
    customer: str
    facilitator: str
    status: SessionStatus
    started_at: datetime | None
    ended_at: datetime | None
    script_id: str | None
    current_stage_sequence: int
    created_at: datetime
    stats: SessionStats | None = None


# --- Transcript -----------------------------------------------------------


class SegmentCreate(BaseModel):
    speaker: str
    text: str
    start_time: float | None = None
    end_time: float | None = None
    is_final: bool = True
    analyze: bool = True


class SegmentRead(ORMModel):
    id: str
    session_id: str
    sequence_number: int
    speaker: str
    start_time: float
    end_time: float
    text: str
    is_final: bool
    status: SegmentStatus
    created_at: datetime


# --- Evidence -------------------------------------------------------------


class EvidenceLinkCreate(BaseModel):
    transcript_segment_id: str
    quoted_text: str = ""
    quote_start: int = 0
    quote_end: int = 0
    relationship: EvidenceRelationship = EvidenceRelationship.DIRECT
    confidence: float = 0.0
    rationale: str = ""


class EvidenceLinkRead(ORMModel):
    id: str
    artifact_id: str
    transcript_segment_id: str
    quote_start: int
    quote_end: int
    quoted_text: str
    relationship_type: EvidenceRelationship = Field(serialization_alias="relationship")
    confidence: float
    rationale: str


# --- Artifacts ------------------------------------------------------------


class ArtifactCreate(BaseModel):
    artifact_type: ArtifactType
    title: str
    statement: str
    confidence: float = 0.0
    parent_id: str | None = None
    rationale: str = ""
    derivation_method: DerivationMethod = DerivationMethod.MANUAL
    evidence: list[EvidenceLinkCreate] = Field(default_factory=list)


class ArtifactUpdate(BaseModel):
    title: str | None = None
    statement: str | None = None
    status: ArtifactStatus | None = None
    confidence: float | None = None
    validation_state: ValidationState | None = None
    parent_id: str | None = None
    rationale: str | None = None
    change_reason: str = ""
    changed_by: str = "facilitator"


class ArtifactAction(BaseModel):
    changed_by: str = "facilitator"
    change_reason: str = ""


class ArtifactMerge(ArtifactAction):
    target_id: str


class ArtifactRead(ORMModel):
    id: str
    session_id: str
    artifact_type: ArtifactType
    title: str
    statement: str
    status: ArtifactStatus
    confidence: float
    validation_state: ValidationState
    derivation_method: DerivationMethod
    parent_id: str | None
    superseded_by_id: str | None
    merged_into_id: str | None
    rationale: str
    created_at: datetime
    updated_at: datetime
    evidence_links: list[EvidenceLinkRead] = Field(default_factory=list)


class RevisionRead(ORMModel):
    id: str
    artifact_id: str
    revision_number: int
    previous_value: str
    new_value: str
    changed_by: str
    change_reason: str
    created_at: datetime


# --- Discovery tree -------------------------------------------------------


class TreeNode(BaseModel):
    id: str
    artifact_type: ArtifactType
    title: str
    statement: str
    status: ArtifactStatus
    confidence: float
    validation_state: ValidationState
    evidence_count: int
    parent_id: str | None
    children: list[TreeNode] = Field(default_factory=list)


class DiscoveryTree(BaseModel):
    session_id: str
    roots: list[TreeNode]


# --- Scripts --------------------------------------------------------------


class ScriptStageRead(ORMModel):
    id: str
    sequence: int
    title: str
    objective: str
    primary_prompt: str
    alternative_prompts: list[str]
    completion_criteria: str


class ScriptRead(ORMModel):
    id: str
    name: str
    version: str
    description: str
    stages: list[ScriptStageRead]


class ScriptStateRead(BaseModel):
    script_id: str | None
    current_sequence: int
    total_stages: int
    current_stage: ScriptStageRead | None
    completed_stages: list[int]
    recommended_question: str | None
    alternative_prompts: list[str] = Field(default_factory=list)


class ScriptAdvance(BaseModel):
    target_sequence: int | None = None
    completed_stage_id: str | None = None


# --- Conversation graph ---------------------------------------------------


class ConversationNodeRead(ORMModel):
    id: str
    node_type: NodeType
    label: str
    transcript_segment_id: str | None
    artifact_id: str | None
    parent_node_id: str | None
    sequence: int


class BranchRead(ORMModel):
    id: str
    name: str
    topic: str
    status: BranchStatus
    is_main: bool
    parent_branch_id: str | None
    source_stage_id: str | None
    created_from_segment_id: str | None
    merge_target_stage_id: str | None
    lane: int
    nodes: list[ConversationNodeRead] = Field(default_factory=list)


class BranchCreate(BaseModel):
    name: str
    topic: str = ""
    source_stage_id: str | None = None
    created_from_segment_id: str | None = None
    parent_branch_id: str | None = None
    merge_target_stage_id: str | None = None


class ConversationGraph(BaseModel):
    session_id: str
    stages: list[ScriptStageRead]
    current_stage_sequence: int
    branches: list[BranchRead]


# --- Coverage -------------------------------------------------------------


class CoverageCell(BaseModel):
    stage_sequence: int
    topic: str
    state: CoverageState
    title: str = ""
    detail: str = ""


class CoverageGap(BaseModel):
    title: str
    detail: str
    severity: str = "medium"


class CoverageMatrix(BaseModel):
    session_id: str
    topics: list[str]
    stages: list[ScriptStageRead]
    cells: list[CoverageCell]
    gaps: list[CoverageGap]
    coverage_percent: int


# --- Analysis / export ----------------------------------------------------


class AnalyzeRequest(BaseModel):
    segment_ids: list[str] | None = None


class AnalyzeResult(BaseModel):
    created_artifacts: list[ArtifactRead]
    created_evidence_links: list[EvidenceLinkRead]


class ExportEnvelope(BaseModel):
    format: str
    filename: str
    content_type: str
    body: str
