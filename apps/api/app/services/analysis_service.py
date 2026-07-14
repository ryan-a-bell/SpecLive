"""Derivation pipeline: transcript segment -> candidate artifacts + evidence.

Uses the injected LanguageModelProvider (mock by default). Emitted artifacts
start at INFERRED status with derivation_method=LLM, never confirmed — human
validation is required to advance them (ADR-0007).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.enums import ArtifactStatus, ArtifactType, DerivationMethod, EvidenceRelationship
from app.models import DiscoveryArtifact, EvidenceLink, TranscriptSegment
from app.providers import get_llm_provider
from app.providers.base import LanguageModelProvider
from app.schemas import ArtifactCreate, EvidenceLinkCreate
from app.services import artifact_service, transcript_service
from app.enums import SegmentStatus


async def analyze_segment(
    db: Session,
    segment: TranscriptSegment,
    *,
    llm: LanguageModelProvider | None = None,
) -> tuple[list[DiscoveryArtifact], list[EvidenceLink]]:
    llm = llm or get_llm_provider()
    transcript_service.set_status(db, segment, SegmentStatus.ANALYZING)

    candidates = await llm.extract_artifacts(segment.text, segment.speaker)
    created_artifacts: list[DiscoveryArtifact] = []
    created_links: list[EvidenceLink] = []

    for candidate in candidates:
        parent_id = _find_parent(db, segment.session_id, candidate.artifact_type)
        evidence = EvidenceLinkCreate(
            transcript_segment_id=segment.id,
            quoted_text=candidate.quote,
            quote_start=candidate.quote_start,
            quote_end=candidate.quote_end,
            relationship=EvidenceRelationship(candidate.relationship),
            confidence=candidate.confidence,
            rationale=candidate.rationale,
        )
        artifact = await artifact_service.create_artifact(
            db,
            segment.session_id,
            ArtifactCreate(
                artifact_type=ArtifactType(candidate.artifact_type),
                title=candidate.title,
                statement=candidate.statement,
                confidence=candidate.confidence,
                rationale=candidate.rationale,
                parent_id=parent_id,
                derivation_method=DerivationMethod.LLM,
                evidence=[evidence],
            ),
            initial_status=ArtifactStatus.INFERRED,
        )
        created_artifacts.append(artifact)
        created_links.extend(artifact.evidence_links)

    transcript_service.set_status(db, segment, SegmentStatus.ANALYZED)
    return created_artifacts, created_links


def _find_parent(db: Session, session_id: str, artifact_type: str) -> str | None:
    """Attach requirements/constraints/risks under the newest stakeholder need,
    and needs under the newest objective, to grow the discovery tree sensibly."""
    from sqlalchemy import select

    parent_type: ArtifactType | None = None
    if artifact_type in {
        ArtifactType.REQUIREMENT,
        ArtifactType.CONSTRAINT,
        ArtifactType.RISK,
        ArtifactType.ASSUMPTION,
        ArtifactType.OPEN_QUESTION,
        ArtifactType.SUCCESS_METRIC,
    }:
        parent_type = ArtifactType.STAKEHOLDER_NEED
    elif artifact_type == ArtifactType.STAKEHOLDER_NEED:
        parent_type = ArtifactType.OBJECTIVE

    if parent_type is None:
        return None
    parent = db.scalars(
        select(DiscoveryArtifact)
        .where(
            DiscoveryArtifact.session_id == session_id,
            DiscoveryArtifact.artifact_type == parent_type,
            DiscoveryArtifact.status != ArtifactStatus.REJECTED,
        )
        .order_by(DiscoveryArtifact.created_at.desc())
    ).first()
    return parent.id if parent else None
