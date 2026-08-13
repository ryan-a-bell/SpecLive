"""Artifact CRUD, evidence linking, revisions, and lifecycle transitions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ..db import models as m
from ..domain import entities as e
from ..domain.enums import (
    ArtifactType,
    DerivationMethod,
    EvidenceRelationship,
    ValidationState,
)
from ..domain.events import DomainEvent, EventType
from ..domain.lifecycle import assert_transition, status_for
from ..events import EventBus
from ..repositories import SessionRepository
from ..repositories.mappers import artifact_to_domain, evidence_to_domain, revision_to_domain
from .errors import NotFoundError, ValidationError


class ArtifactService:
    def __init__(self, repo: SessionRepository, bus: EventBus) -> None:
        self._repo = repo
        self._bus = bus

    # --- reads ------------------------------------------------------------
    def get(self, artifact_id: str) -> e.DiscoveryArtifact:
        row = self._require(artifact_id)
        return artifact_to_domain(row)

    def list_for_session(self, session_id: str) -> list[e.DiscoveryArtifact]:
        return [artifact_to_domain(r) for r in self._repo.list_artifacts(session_id)]

    def evidence_for(self, artifact_id: str) -> list[e.EvidenceLink]:
        self._require(artifact_id)
        return [evidence_to_domain(r) for r in self._repo.list_evidence_for_artifact(artifact_id)]

    def list_evidence_for_session(self, session_id: str) -> list[e.EvidenceLink]:
        return [evidence_to_domain(r) for r in self._repo.list_evidence(session_id)]

    def revisions_for(self, artifact_id: str) -> list[e.ArtifactRevision]:
        self._require(artifact_id)
        return [revision_to_domain(r) for r in self._repo.list_revisions(artifact_id)]

    # --- writes -----------------------------------------------------------
    def create(
        self,
        session_id: str,
        *,
        artifact_type: ArtifactType,
        title: str,
        statement: str,
        confidence: float = 0.0,
        rationale: str | None = None,
        parent_id: str | None = None,
        branch_id: str | None = None,
        validation_state: ValidationState = ValidationState.DETECTED,
        derivation_method: DerivationMethod = DerivationMethod.MANUAL,
        actor_is_human: bool = True,
    ) -> e.DiscoveryArtifact:
        if self._repo.get_session(session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")
        # Automated derivations may only propose detected/inferred artifacts.
        assert_transition(ValidationState.DETECTED, validation_state, actor_is_human=actor_is_human)
        row = m.DiscoveryArtifactORM(
            id=str(uuid4()),
            session_id=session_id,
            artifact_type=ArtifactType(artifact_type).value,
            title=title,
            statement=statement,
            status=status_for(validation_state).value,
            confidence=confidence,
            validation_state=ValidationState(validation_state).value,
            derivation_method=DerivationMethod(derivation_method).value,
            parent_id=parent_id,
            branch_id=branch_id,
            rationale=rationale,
        )
        self._repo.add_artifact(row)
        self._repo.commit()
        artifact = artifact_to_domain(row)
        self._bus.publish(
            DomainEvent(
                type=EventType.ARTIFACT_CANDIDATE_CREATED,
                session_id=session_id,
                payload=artifact.model_dump(mode="json"),
            )
        )
        return artifact

    def add_evidence(
        self,
        artifact_id: str,
        *,
        transcript_segment_id: str,
        quote_start: int,
        quote_end: int,
        quoted_text: str,
        relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTING,
        confidence: float = 0.0,
        rationale: str | None = None,
    ) -> e.EvidenceLink:
        self._require(artifact_id)
        if quote_start < 0 or quote_end < quote_start:
            raise ValidationError("Invalid quote offsets: require 0 <= quote_start <= quote_end")
        row = m.EvidenceLinkORM(
            id=str(uuid4()),
            artifact_id=artifact_id,
            transcript_segment_id=transcript_segment_id,
            quote_start=quote_start,
            quote_end=quote_end,
            quoted_text=quoted_text,
            relationship_type=EvidenceRelationship(relationship).value,
            confidence=confidence,
            rationale=rationale,
        )
        self._repo.add_evidence(row)
        self._repo.commit()
        link = evidence_to_domain(row)
        self._bus.publish(
            DomainEvent(
                type=EventType.EVIDENCE_LINK_CREATED,
                session_id=self._require(artifact_id).session_id,
                payload=link.model_dump(mode="json"),
            )
        )
        return link

    def update(
        self,
        artifact_id: str,
        *,
        changed_by: str = "facilitator",
        change_reason: str | None = None,
        **changes: object,
    ) -> e.DiscoveryArtifact:
        row = self._require(artifact_id)
        before = artifact_to_domain(row).model_dump(mode="json")
        editable = {"title", "statement", "confidence", "rationale", "artifact_type", "parent_id"}
        for key, value in changes.items():
            if value is None or key not in editable:
                continue
            if key == "artifact_type":
                value = ArtifactType(value).value
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        self._record_revision(row, before, changed_by, change_reason)
        self._repo.commit()
        artifact = artifact_to_domain(row)
        self._publish_updated(artifact)
        return artifact

    def transition(
        self,
        artifact_id: str,
        target: ValidationState,
        *,
        actor_is_human: bool = True,
        changed_by: str = "facilitator",
        change_reason: str | None = None,
    ) -> e.DiscoveryArtifact:
        row = self._require(artifact_id)
        current = ValidationState(row.validation_state)
        assert_transition(current, target, actor_is_human=actor_is_human)
        before = artifact_to_domain(row).model_dump(mode="json")
        row.validation_state = target.value
        row.status = status_for(target).value
        row.updated_at = datetime.now(UTC)
        self._record_revision(
            row, before, changed_by, change_reason or f"transition to {target.value}"
        )
        self._repo.commit()
        artifact = artifact_to_domain(row)
        event_type = {
            ValidationState.CUSTOMER_CONFIRMED: EventType.ARTIFACT_CONFIRMED,
            ValidationState.BASELINED: EventType.ARTIFACT_CONFIRMED,
            ValidationState.REJECTED: EventType.ARTIFACT_REJECTED,
        }.get(target, EventType.ARTIFACT_UPDATED)
        self._bus.publish(
            DomainEvent(
                type=event_type,
                session_id=row.session_id,
                payload=artifact.model_dump(mode="json"),
            )
        )
        return artifact

    def confirm(self, artifact_id: str, *, changed_by: str = "facilitator") -> e.DiscoveryArtifact:
        """Explicit human confirmation — the only path to customer_confirmed."""

        return self.transition(
            artifact_id,
            ValidationState.CUSTOMER_CONFIRMED,
            actor_is_human=True,
            changed_by=changed_by,
        )

    def reject(
        self, artifact_id: str, *, changed_by: str = "facilitator", reason: str | None = None
    ) -> e.DiscoveryArtifact:
        return self.transition(
            artifact_id,
            ValidationState.REJECTED,
            actor_is_human=True,
            changed_by=changed_by,
            change_reason=reason,
        )

    def merge(
        self,
        artifact_id: str,
        *,
        into_artifact_id: str,
        changed_by: str = "facilitator",
    ) -> e.DiscoveryArtifact:
        """Merge ``artifact_id`` into ``into_artifact_id``.

        Evidence from the merged artifact is re-pointed at the survivor, and the
        merged artifact transitions to MERGED / superseded_by the survivor.
        """

        source = self._require(artifact_id)
        target = self._require(into_artifact_id)
        for link in self._repo.list_evidence_for_artifact(source.id):
            link.artifact_id = target.id
        before = artifact_to_domain(source).model_dump(mode="json")
        source.validation_state = ValidationState.MERGED.value
        source.status = status_for(ValidationState.MERGED).value
        source.superseded_by = target.id
        source.updated_at = datetime.now(UTC)
        self._record_revision(source, before, changed_by, f"merged into {target.id}")
        self._repo.commit()
        merged = artifact_to_domain(source)
        self._publish_updated(merged)
        return merged

    # --- helpers ----------------------------------------------------------
    def _require(self, artifact_id: str) -> m.DiscoveryArtifactORM:
        row = self._repo.get_artifact(artifact_id)
        if row is None:
            raise NotFoundError(f"Artifact {artifact_id} not found")
        return row

    def _record_revision(
        self,
        row: m.DiscoveryArtifactORM,
        before: dict,
        changed_by: str,
        reason: str | None,
    ) -> None:
        after = artifact_to_domain(row).model_dump(mode="json")
        n = len(self._repo.list_revisions(row.id)) + 1
        self._repo.add_revision(
            m.ArtifactRevisionORM(
                id=str(uuid4()),
                artifact_id=row.id,
                revision_number=n,
                previous_value=before,
                new_value=after,
                changed_by=changed_by,
                change_reason=reason,
            )
        )

    def _publish_updated(self, artifact: e.DiscoveryArtifact) -> None:
        self._bus.publish(
            DomainEvent(
                type=EventType.ARTIFACT_UPDATED,
                session_id=artifact.session_id,
                payload=artifact.model_dump(mode="json"),
            )
        )
