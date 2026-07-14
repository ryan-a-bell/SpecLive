"""Artifact CRUD and the lifecycle state machine.

The lifecycle rule (ADR-0007) is enforced here, not in the UI: a model-inferred
artifact can never reach CUSTOMER_CONFIRMED through a generic update. Only the
explicit `confirm` action — a deliberate human act — moves it there.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    CLOSABLE_STATES,
    CONFIRMABLE_STATES,
    PATCH_TRANSITIONS,
    ArtifactStatus,
    ValidationState,
)
from app.errors import InvalidTransitionError, NotFoundError, ValidationError
from app.events import DomainEvent, EventType, get_event_bus
from app.ids import next_artifact_id
from app.models import DiscoveryArtifact
from app.schemas import ArtifactCreate, ArtifactUpdate
from app.services import evidence_service, revision_service
from app.services.session_service import get_session


def get_artifact(db: Session, artifact_id: str) -> DiscoveryArtifact:
    artifact = db.get(DiscoveryArtifact, artifact_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    return artifact


def list_artifacts(db: Session, session_id: str) -> list[DiscoveryArtifact]:
    get_session(db, session_id)
    return list(
        db.scalars(
            select(DiscoveryArtifact)
            .where(DiscoveryArtifact.session_id == session_id)
            .order_by(DiscoveryArtifact.created_at)
        )
    )


async def create_artifact(
    db: Session,
    session_id: str,
    data: ArtifactCreate,
    *,
    initial_status: ArtifactStatus = ArtifactStatus.DETECTED,
    emit: bool = True,
) -> DiscoveryArtifact:
    get_session(db, session_id)
    if data.parent_id is not None and db.get(DiscoveryArtifact, data.parent_id) is None:
        raise ValidationError(f"Parent artifact {data.parent_id} not found")

    artifact = DiscoveryArtifact(
        id=next_artifact_id(db, session_id, data.artifact_type),
        session_id=session_id,
        artifact_type=data.artifact_type,
        title=data.title,
        statement=data.statement,
        status=initial_status,
        confidence=data.confidence,
        derivation_method=data.derivation_method,
        parent_id=data.parent_id,
        rationale=data.rationale,
    )
    db.add(artifact)
    db.flush()

    for link in data.evidence:
        evidence_service.create_link(db, artifact.id, link, emit=False)

    db.commit()
    db.refresh(artifact)

    if emit:
        await get_event_bus().publish(
            DomainEvent(
                type=EventType.ARTIFACT_CANDIDATE_CREATED,
                session_id=session_id,
                payload={"artifact_id": artifact.id, "artifact_type": artifact.artifact_type},
            )
        )
    return artifact


async def update_artifact(
    db: Session, artifact_id: str, data: ArtifactUpdate
) -> DiscoveryArtifact:
    artifact = get_artifact(db, artifact_id)
    before = _snapshot(artifact)

    if data.status is not None and data.status != artifact.status:
        _assert_patch_transition(artifact.status, data.status)
        artifact.status = data.status

    for field in ("title", "statement", "rationale", "parent_id"):
        value = getattr(data, field)
        if value is not None:
            setattr(artifact, field, value)
    if data.confidence is not None:
        artifact.confidence = data.confidence
    if data.validation_state is not None:
        artifact.validation_state = data.validation_state

    after = _snapshot(artifact)
    revision_service.record(
        db, artifact, before, after, changed_by=data.changed_by, reason=data.change_reason
    )
    db.commit()
    db.refresh(artifact)

    await get_event_bus().publish(
        DomainEvent(
            type=EventType.ARTIFACT_UPDATED,
            session_id=artifact.session_id,
            payload={"artifact_id": artifact.id, "status": artifact.status},
        )
    )
    return artifact


async def confirm_artifact(
    db: Session, artifact_id: str, changed_by: str, reason: str
) -> DiscoveryArtifact:
    artifact = get_artifact(db, artifact_id)
    if artifact.status not in CONFIRMABLE_STATES:
        raise InvalidTransitionError(
            f"Cannot confirm artifact in status '{artifact.status}'"
        )
    before = _snapshot(artifact)
    artifact.status = ArtifactStatus.CUSTOMER_CONFIRMED
    artifact.validation_state = ValidationState.VALIDATED
    after = _snapshot(artifact)
    revision_service.record(
        db, artifact, before, after, changed_by=changed_by,
        reason=reason or "Customer confirmation",
    )
    db.commit()
    db.refresh(artifact)

    await get_event_bus().publish(
        DomainEvent(
            type=EventType.ARTIFACT_CONFIRMED,
            session_id=artifact.session_id,
            payload={"artifact_id": artifact.id},
        )
    )
    return artifact


async def reject_artifact(
    db: Session, artifact_id: str, changed_by: str, reason: str
) -> DiscoveryArtifact:
    artifact = get_artifact(db, artifact_id)
    if artifact.status not in CLOSABLE_STATES:
        raise InvalidTransitionError(f"Cannot reject artifact in status '{artifact.status}'")
    before = _snapshot(artifact)
    artifact.status = ArtifactStatus.REJECTED
    after = _snapshot(artifact)
    revision_service.record(
        db, artifact, before, after, changed_by=changed_by, reason=reason or "Rejected"
    )
    db.commit()
    db.refresh(artifact)

    await get_event_bus().publish(
        DomainEvent(
            type=EventType.ARTIFACT_REJECTED,
            session_id=artifact.session_id,
            payload={"artifact_id": artifact.id},
        )
    )
    return artifact


async def merge_artifact(
    db: Session, artifact_id: str, target_id: str, changed_by: str, reason: str
) -> DiscoveryArtifact:
    """Merge `artifact_id` into `target_id`; evidence moves to the target."""
    if artifact_id == target_id:
        raise ValidationError("Cannot merge an artifact into itself")
    source = get_artifact(db, artifact_id)
    target = get_artifact(db, target_id)
    if source.status not in CLOSABLE_STATES:
        raise InvalidTransitionError(f"Cannot merge artifact in status '{source.status}'")

    evidence_service.reassign_links(db, source.id, target.id)

    before = _snapshot(source)
    source.status = ArtifactStatus.MERGED
    source.merged_into_id = target.id
    after = _snapshot(source)
    revision_service.record(
        db, source, before, after, changed_by=changed_by,
        reason=reason or f"Merged into {target.id}",
    )
    db.commit()
    db.refresh(target)

    await get_event_bus().publish(
        DomainEvent(
            type=EventType.ARTIFACT_UPDATED,
            session_id=target.session_id,
            payload={"artifact_id": target.id, "merged_from": source.id},
        )
    )
    return target


def _assert_patch_transition(current: ArtifactStatus, target: ArtifactStatus) -> None:
    allowed = PATCH_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Transition {current} -> {target} is not allowed via update. "
            "Use the confirm/reject/merge actions for lifecycle changes."
        )


def _snapshot(artifact: DiscoveryArtifact) -> dict:
    return {
        "title": artifact.title,
        "statement": artifact.statement,
        "status": str(artifact.status),
        "confidence": artifact.confidence,
        "validation_state": str(artifact.validation_state),
        "parent_id": artifact.parent_id,
        "rationale": artifact.rationale,
    }
