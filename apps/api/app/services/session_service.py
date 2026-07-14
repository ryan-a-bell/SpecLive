from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import ArtifactStatus, ArtifactType, SessionStatus
from app.errors import NotFoundError
from app.models import (
    DiscoveryArtifact,
    DiscoverySession,
    EvidenceLink,
    TranscriptSegment,
    utcnow,
)
from app.schemas import SessionCreate, SessionStats, SessionUpdate


def create_session(db: Session, data: SessionCreate) -> DiscoverySession:
    session = DiscoverySession(
        id=f"SESS-{uuid.uuid4().hex[:8]}",
        title=data.title,
        customer=data.customer,
        facilitator=data.facilitator,
        script_id=data.script_id,
        status=SessionStatus.ACTIVE,
        started_at=utcnow(),
        session_metadata=json.dumps(data.metadata),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session) -> list[DiscoverySession]:
    return list(db.scalars(select(DiscoverySession).order_by(DiscoverySession.created_at.desc())))


def get_session(db: Session, session_id: str) -> DiscoverySession:
    session = db.get(DiscoverySession, session_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return session


def update_session(db: Session, session_id: str, data: SessionUpdate) -> DiscoverySession:
    session = get_session(db, session_id)
    if data.title is not None:
        session.title = data.title
    if data.status is not None:
        session.status = data.status
        if data.status == SessionStatus.COMPLETED and session.ended_at is None:
            session.ended_at = utcnow()
    if data.current_stage_sequence is not None:
        session.current_stage_sequence = data.current_stage_sequence
    db.commit()
    db.refresh(session)
    return session


def session_stats(db: Session, session_id: str) -> SessionStats:
    def count(stmt) -> int:
        return db.scalar(stmt) or 0

    segment_count = count(
        select(func.count()).select_from(TranscriptSegment).where(
            TranscriptSegment.session_id == session_id
        )
    )
    artifact_count = count(
        select(func.count()).select_from(DiscoveryArtifact).where(
            DiscoveryArtifact.session_id == session_id
        )
    )
    reqs = select(func.count()).select_from(DiscoveryArtifact).where(
        DiscoveryArtifact.session_id == session_id,
        DiscoveryArtifact.artifact_type == ArtifactType.REQUIREMENT,
    )
    candidate_reqs = count(
        reqs.where(
            DiscoveryArtifact.status.notin_(
                [ArtifactStatus.CUSTOMER_CONFIRMED, ArtifactStatus.BASELINED,
                 ArtifactStatus.REJECTED, ArtifactStatus.MERGED]
            )
        )
    )
    confirmed_reqs = count(
        reqs.where(
            DiscoveryArtifact.status.in_(
                [ArtifactStatus.CUSTOMER_CONFIRMED, ArtifactStatus.BASELINED]
            )
        )
    )
    evidence_count = count(
        select(func.count())
        .select_from(EvidenceLink)
        .join(DiscoveryArtifact, EvidenceLink.artifact_id == DiscoveryArtifact.id)
        .where(DiscoveryArtifact.session_id == session_id)
    )
    open_questions = count(
        select(func.count()).select_from(DiscoveryArtifact).where(
            DiscoveryArtifact.session_id == session_id,
            DiscoveryArtifact.artifact_type == ArtifactType.OPEN_QUESTION,
            DiscoveryArtifact.status != ArtifactStatus.REJECTED,
        )
    )

    from app.services import coverage_service

    coverage_percent = coverage_service.coverage_percent(db, session_id)

    return SessionStats(
        segment_count=segment_count,
        artifact_count=artifact_count,
        candidate_requirement_count=candidate_reqs,
        confirmed_requirement_count=confirmed_reqs,
        evidence_link_count=evidence_count,
        open_question_count=open_questions,
        coverage_percent=coverage_percent,
    )
