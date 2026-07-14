from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError, ValidationError
from app.events import DomainEvent, EventType, get_event_bus
from app.ids import new_evidence_id
from app.models import DiscoveryArtifact, EvidenceLink, TranscriptSegment
from app.schemas import EvidenceLinkCreate


def create_link(
    db: Session, artifact_id: str, data: EvidenceLinkCreate, *, emit: bool = True
) -> EvidenceLink:
    artifact = db.get(DiscoveryArtifact, artifact_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    segment = db.get(TranscriptSegment, data.transcript_segment_id)
    if segment is None:
        raise NotFoundError(f"Segment {data.transcript_segment_id} not found")
    if segment.session_id != artifact.session_id:
        raise ValidationError("Evidence segment and artifact belong to different sessions")

    quote = data.quoted_text
    start, end = data.quote_start, data.quote_end
    if not quote and end > start:
        quote = segment.text[start:end]
    if quote and quote not in segment.text:
        raise ValidationError("Quoted text does not appear in the referenced segment")

    link = EvidenceLink(
        id=new_evidence_id(),
        artifact_id=artifact_id,
        transcript_segment_id=data.transcript_segment_id,
        quote_start=start,
        quote_end=end,
        quoted_text=quote,
        relationship_type=data.relationship,
        confidence=data.confidence,
        rationale=data.rationale,
    )
    db.add(link)
    if emit:
        db.commit()
        db.refresh(link)
        # Fire-and-forget from a sync context: schedule if a loop is running.
        _emit_created(artifact.session_id, link)
    else:
        db.flush()
    return link


def list_links(db: Session, artifact_id: str) -> list[EvidenceLink]:
    return list(
        db.scalars(select(EvidenceLink).where(EvidenceLink.artifact_id == artifact_id))
    )


def reassign_links(db: Session, from_artifact_id: str, to_artifact_id: str) -> None:
    for link in list_links(db, from_artifact_id):
        link.artifact_id = to_artifact_id
    db.flush()


def _emit_created(session_id: str, link: EvidenceLink) -> None:
    import asyncio

    event = DomainEvent(
        type=EventType.EVIDENCE_LINK_CREATED,
        session_id=session_id,
        payload={"evidence_id": link.id, "artifact_id": link.artifact_id},
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(get_event_bus().publish(event))
    except RuntimeError:
        asyncio.run(get_event_bus().publish(event))
