"""Bidirectional mapping between ORM rows and domain entities."""

from __future__ import annotations

from ..db import models as m
from ..domain import entities as e
from ..domain.enums import (
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


def session_to_domain(row: m.DiscoverySessionORM) -> e.DiscoverySession:
    return e.DiscoverySession(
        id=row.id,
        title=row.title,
        customer=row.customer,
        facilitator=row.facilitator,
        status=SessionStatus(row.status),
        started_at=row.started_at,
        ended_at=row.ended_at,
        script_id=row.script_id,
        metadata=row.meta or {},
        created_at=row.created_at,
    )


def segment_to_domain(row: m.TranscriptSegmentORM) -> e.TranscriptSegment:
    return e.TranscriptSegment(
        id=row.id,
        session_id=row.session_id,
        sequence_number=row.sequence_number,
        speaker=Speaker(row.speaker),
        speaker_id=row.speaker_id,
        speaker_name=row.speaker_name,
        speaker_source=SpeakerSource(row.speaker_source),
        speaker_confidence=row.speaker_confidence,
        start_time=row.start_time,
        end_time=row.end_time,
        text=row.text,
        is_final=row.is_final,
        created_at=row.created_at,
    )


def artifact_to_domain(row: m.DiscoveryArtifactORM) -> e.DiscoveryArtifact:
    return e.DiscoveryArtifact(
        id=row.id,
        session_id=row.session_id,
        artifact_type=ArtifactType(row.artifact_type),
        title=row.title,
        statement=row.statement,
        status=ArtifactStatus(row.status),
        confidence=row.confidence,
        validation_state=ValidationState(row.validation_state),
        derivation_method=DerivationMethod(row.derivation_method),
        parent_id=row.parent_id,
        branch_id=row.branch_id,
        rationale=row.rationale,
        superseded_by=row.superseded_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def evidence_to_domain(row: m.EvidenceLinkORM) -> e.EvidenceLink:
    return e.EvidenceLink(
        id=row.id,
        artifact_id=row.artifact_id,
        transcript_segment_id=row.transcript_segment_id,
        quote_start=row.quote_start,
        quote_end=row.quote_end,
        quoted_text=row.quoted_text,
        relationship=EvidenceRelationship(row.relationship_type),
        confidence=row.confidence,
        rationale=row.rationale,
        created_at=row.created_at,
    )


def branch_to_domain(row: m.ConversationBranchORM) -> e.ConversationBranch:
    return e.ConversationBranch(
        id=row.id,
        session_id=row.session_id,
        parent_branch_id=row.parent_branch_id,
        source_stage_id=row.source_stage_id,
        name=row.name,
        topic=row.topic,
        status=BranchStatus(row.status),
        created_from_segment_id=row.created_from_segment_id,
        merge_target_stage_id=row.merge_target_stage_id,
        created_at=row.created_at,
    )


def node_to_domain(row: m.ConversationNodeORM) -> e.ConversationNode:
    return e.ConversationNode(
        id=row.id,
        branch_id=row.branch_id,
        node_type=ConversationNodeType(row.node_type),
        label=row.label,
        transcript_segment_id=row.transcript_segment_id,
        artifact_id=row.artifact_id,
        parent_node_id=row.parent_node_id,
        sequence=row.sequence,
        created_at=row.created_at,
    )


def stage_to_domain(row: m.ScriptStageORM) -> e.ScriptStage:
    return e.ScriptStage(
        id=row.id,
        script_id=row.script_id,
        sequence=row.sequence,
        title=row.title,
        objective=row.objective,
        primary_prompt=row.primary_prompt,
        alternative_prompts=list(row.alternative_prompts or []),
        completion_criteria=list(row.completion_criteria or []),
    )


def script_to_domain(row: m.ScriptDefinitionORM) -> e.ScriptDefinition:
    return e.ScriptDefinition(
        id=row.id,
        name=row.name,
        version=row.version,
        description=row.description,
        archived=row.archived,
        stages=[stage_to_domain(s) for s in row.stages],
    )


def revision_to_domain(row: m.ArtifactRevisionORM) -> e.ArtifactRevision:
    return e.ArtifactRevision(
        id=row.id,
        artifact_id=row.artifact_id,
        revision_number=row.revision_number,
        previous_value=row.previous_value or {},
        new_value=row.new_value or {},
        changed_by=row.changed_by,
        change_reason=row.change_reason,
        created_at=row.created_at,
    )
