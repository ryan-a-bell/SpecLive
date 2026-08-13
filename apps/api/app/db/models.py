"""SQLAlchemy ORM models mapping the domain entities to relational tables.

Enum columns are stored as strings (the enum ``value``) for portability across
PostgreSQL and the SQLite fallback. JSON columns use the generic ``JSON`` type.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class DiscoverySessionORM(Base):
    __tablename__ = "discovery_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    customer: Mapped[str] = mapped_column(String(255))
    facilitator: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    script_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    segments: Mapped[list[TranscriptSegmentORM]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[DiscoveryArtifactORM]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    branches: Mapped[list[ConversationBranchORM]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class TranscriptSegmentORM(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("discovery_sessions.id"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[DiscoverySessionORM] = relationship(back_populates="segments")


class DiscoveryArtifactORM(Base):
    __tablename__ = "discovery_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("discovery_sessions.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(500))
    statement: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="candidate")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validation_state: Mapped[str] = mapped_column(String(32), default="detected")
    derivation_method: Mapped[str] = mapped_column(String(32), default="manual")
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[DiscoverySessionORM] = relationship(back_populates="artifacts")
    evidence_links: Mapped[list[EvidenceLinkORM]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )
    revisions: Mapped[list[ArtifactRevisionORM]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )


class EvidenceLinkORM(Base):
    __tablename__ = "evidence_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("discovery_artifacts.id"), index=True)
    transcript_segment_id: Mapped[str] = mapped_column(
        ForeignKey("transcript_segments.id"), index=True
    )
    quote_start: Mapped[int] = mapped_column(Integer)
    quote_end: Mapped[int] = mapped_column(Integer)
    quoted_text: Mapped[str] = mapped_column(Text)
    relationship_type: Mapped[str] = mapped_column("relationship", String(32), default="supporting")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    artifact: Mapped[DiscoveryArtifactORM] = relationship(back_populates="evidence_links")


class ArtifactRevisionORM(Base):
    __tablename__ = "artifact_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("discovery_artifacts.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    previous_value: Mapped[dict] = mapped_column(JSON, default=dict)
    new_value: Mapped[dict] = mapped_column(JSON, default=dict)
    changed_by: Mapped[str] = mapped_column(String(255))
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    artifact: Mapped[DiscoveryArtifactORM] = relationship(back_populates="revisions")


class ScriptDefinitionORM(Base):
    __tablename__ = "script_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    description: Mapped[str] = mapped_column(Text, default="")

    stages: Mapped[list[ScriptStageORM]] = relationship(
        back_populates="script", cascade="all, delete-orphan", order_by="ScriptStageORM.sequence"
    )


class ScriptStageORM(Base):
    __tablename__ = "script_stages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    script_id: Mapped[str] = mapped_column(ForeignKey("script_definitions.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    objective: Mapped[str] = mapped_column(Text)
    primary_prompt: Mapped[str] = mapped_column(Text)
    alternative_prompts: Mapped[list] = mapped_column(JSON, default=list)
    completion_criteria: Mapped[list] = mapped_column(JSON, default=list)

    script: Mapped[ScriptDefinitionORM] = relationship(back_populates="stages")


class ConversationBranchORM(Base):
    __tablename__ = "conversation_branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("discovery_sessions.id"), index=True)
    parent_branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_stage_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_from_segment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    merge_target_stage_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[DiscoverySessionORM] = relationship(back_populates="branches")
    nodes: Mapped[list[ConversationNodeORM]] = relationship(
        back_populates="branch",
        cascade="all, delete-orphan",
        order_by="ConversationNodeORM.sequence",
    )


class ConversationNodeORM(Base):
    __tablename__ = "conversation_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(ForeignKey("conversation_branches.id"), index=True)
    node_type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(500))
    transcript_segment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    parent_node_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    branch: Mapped[ConversationBranchORM] = relationship(back_populates="nodes")
