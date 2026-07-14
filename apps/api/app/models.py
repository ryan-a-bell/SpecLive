"""SQLAlchemy ORM models.

Domain entities only — no provider-specific logic lives here (ADR-0004).
Persistence-neutral business rules live in `app/services`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.enums import (
    ArtifactStatus,
    ArtifactType,
    BranchStatus,
    DerivationMethod,
    EvidenceRelationship,
    NodeType,
    SegmentStatus,
    SessionStatus,
    ValidationState,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DiscoverySession(Base):
    __tablename__ = "discovery_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    customer: Mapped[str] = mapped_column(String(255))
    facilitator: Mapped[str] = mapped_column(String(255))
    status: Mapped[SessionStatus] = mapped_column(String(32), default=SessionStatus.DRAFT)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    script_id: Mapped[str | None] = mapped_column(ForeignKey("script_definitions.id"))
    current_stage_sequence: Mapped[int] = mapped_column(Integer, default=0)
    session_metadata: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[DiscoveryArtifact]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    branches: Mapped[list[ConversationBranch]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    script: Mapped[ScriptDefinition | None] = relationship()


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_sessions.id", ondelete="CASCADE")
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(128))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(default=True)
    status: Mapped[SegmentStatus] = mapped_column(String(32), default=SegmentStatus.RECEIVED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[DiscoverySession] = relationship(back_populates="segments")

    __table_args__ = (UniqueConstraint("session_id", "sequence_number"),)


class DiscoveryArtifact(Base):
    __tablename__ = "discovery_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_sessions.id", ondelete="CASCADE")
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    statement: Mapped[str] = mapped_column(Text)
    status: Mapped[ArtifactStatus] = mapped_column(String(32), default=ArtifactStatus.DETECTED)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validation_state: Mapped[ValidationState] = mapped_column(
        String(32), default=ValidationState.UNVALIDATED
    )
    derivation_method: Mapped[DerivationMethod] = mapped_column(
        String(32), default=DerivationMethod.HEURISTIC
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_artifacts.id", ondelete="SET NULL")
    )
    superseded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_artifacts.id", ondelete="SET NULL")
    )
    merged_into_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_artifacts.id", ondelete="SET NULL")
    )
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    session: Mapped[DiscoverySession] = relationship(back_populates="artifacts")
    children: Mapped[list[DiscoveryArtifact]] = relationship(
        back_populates="parent", foreign_keys=[parent_id], remote_side=[id]
    )
    parent: Mapped[DiscoveryArtifact | None] = relationship(
        back_populates="children", foreign_keys=[parent_id], remote_side=[id]
    )
    evidence_links: Mapped[list[EvidenceLink]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )
    revisions: Mapped[list[ArtifactRevision]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_artifacts.id", ondelete="CASCADE")
    )
    transcript_segment_id: Mapped[str] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    quote_start: Mapped[int] = mapped_column(Integer, default=0)
    quote_end: Mapped[int] = mapped_column(Integer, default=0)
    quoted_text: Mapped[str] = mapped_column(Text, default="")
    relationship_type: Mapped[EvidenceRelationship] = mapped_column(
        String(32), default=EvidenceRelationship.DIRECT
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    artifact: Mapped[DiscoveryArtifact] = relationship(back_populates="evidence_links")
    segment: Mapped[TranscriptSegment] = relationship()


class ArtifactRevision(Base):
    __tablename__ = "artifact_revisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_artifacts.id", ondelete="CASCADE")
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    previous_value: Mapped[str] = mapped_column(Text, default="{}")
    new_value: Mapped[str] = mapped_column(Text, default="{}")
    changed_by: Mapped[str] = mapped_column(String(128), default="system")
    change_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    artifact: Mapped[DiscoveryArtifact] = relationship(back_populates="revisions")

    __table_args__ = (UniqueConstraint("artifact_id", "revision_number"),)


class ScriptDefinition(Base):
    __tablename__ = "script_definitions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    description: Mapped[str] = mapped_column(Text, default="")

    stages: Mapped[list[ScriptStage]] = relationship(
        back_populates="script",
        cascade="all, delete-orphan",
        order_by="ScriptStage.sequence",
    )


class ScriptStage(Base):
    __tablename__ = "script_stages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    script_id: Mapped[str] = mapped_column(
        ForeignKey("script_definitions.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    objective: Mapped[str] = mapped_column(Text, default="")
    primary_prompt: Mapped[str] = mapped_column(Text)
    alternative_prompts: Mapped[str] = mapped_column(Text, default="[]")
    completion_criteria: Mapped[str] = mapped_column(Text, default="")

    script: Mapped[ScriptDefinition] = relationship(back_populates="stages")

    __table_args__ = (UniqueConstraint("script_id", "sequence"),)


class ConversationBranch(Base):
    __tablename__ = "conversation_branches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_sessions.id", ondelete="CASCADE")
    )
    parent_branch_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_branches.id", ondelete="SET NULL")
    )
    source_stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("script_stages.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[BranchStatus] = mapped_column(String(32), default=BranchStatus.OPEN)
    is_main: Mapped[bool] = mapped_column(default=False)
    created_from_segment_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="SET NULL")
    )
    merge_target_stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("script_stages.id", ondelete="SET NULL")
    )
    lane: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[DiscoverySession] = relationship(back_populates="branches")
    nodes: Mapped[list[ConversationNode]] = relationship(
        back_populates="branch",
        cascade="all, delete-orphan",
        order_by="ConversationNode.sequence",
    )


class ConversationNode(Base):
    __tablename__ = "conversation_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    branch_id: Mapped[str] = mapped_column(
        ForeignKey("conversation_branches.id", ondelete="CASCADE")
    )
    node_type: Mapped[NodeType] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(512))
    transcript_segment_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="SET NULL")
    )
    artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_artifacts.id", ondelete="SET NULL")
    )
    parent_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversation_nodes.id", ondelete="SET NULL")
    )
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    branch: Mapped[ConversationBranch] = relationship(back_populates="nodes")
