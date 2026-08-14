"""Builds the structured discovery package and renders it via an exporter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..domain.enums import ArtifactType, ValidationState
from ..exporters import get_exporter
from ..repositories import SessionRepository
from ..repositories.mappers import (
    artifact_to_domain,
    branch_to_domain,
    evidence_to_domain,
    session_to_domain,
)
from .errors import NotFoundError

_CONFIRMED = (ValidationState.CUSTOMER_CONFIRMED, ValidationState.BASELINED)
_HIDDEN = (ValidationState.REJECTED, ValidationState.MERGED)


class ExportService:
    def __init__(self, repo: SessionRepository) -> None:
        self._repo = repo

    def build_package(self, session_id: str) -> dict[str, Any]:
        session_row = self._repo.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session {session_id} not found")
        session = session_to_domain(session_row)

        artifacts = [
            a
            for a in (artifact_to_domain(r) for r in self._repo.list_artifacts(session_id))
            if a.validation_state not in _HIDDEN
        ]
        evidence = [evidence_to_domain(r) for r in self._repo.list_evidence(session_id)]
        ev_by_artifact: dict[str, list] = {}
        for link in evidence:
            ev_by_artifact.setdefault(link.artifact_id, []).append(link)

        def of_type(*types: ArtifactType) -> list[dict]:
            return [self._brief(a) for a in artifacts if a.artifact_type in types]

        requirements = [a for a in artifacts if a.artifact_type == ArtifactType.REQUIREMENT]
        confirmed_reqs = [self._brief(a) for a in requirements if a.validation_state in _CONFIRMED]
        candidate_reqs = [
            self._brief(a) for a in requirements if a.validation_state not in _CONFIRMED
        ]

        branches = self._repo.list_branches(session_id)
        branch_summary = [
            {
                **{
                    k: branch_to_domain(b).model_dump(mode="json")[k]
                    for k in ("id", "name", "topic", "status")
                },
                "node_count": len(self._repo.list_nodes(b.id)),
            }
            for b in branches
        ]

        traceability = [
            {
                "artifact_id": a.id,
                "title": a.title,
                "type": a.artifact_type.value,
                "validation_state": a.validation_state.value,
                "confidence": a.confidence,
                "evidence": [
                    {
                        "segment_id": link.transcript_segment_id,
                        "quoted_text": link.quoted_text,
                        "relationship": link.relationship.value,
                    }
                    for link in ev_by_artifact.get(a.id, [])
                ],
            }
            for a in artifacts
        ]

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "session": session.model_dump(mode="json"),
            "executive_summary": self._summary(session, confirmed_reqs, candidate_reqs, artifacts),
            "objectives": of_type(ArtifactType.OBJECTIVE),
            "stakeholder_needs": of_type(ArtifactType.STAKEHOLDER_NEED),
            "confirmed_requirements": confirmed_reqs,
            "candidate_requirements": candidate_reqs,
            "constraints": of_type(ArtifactType.CONSTRAINT),
            "assumptions": of_type(ArtifactType.ASSUMPTION),
            "risks": of_type(ArtifactType.RISK),
            "decisions": of_type(ArtifactType.DECISION),
            "open_questions": of_type(ArtifactType.OPEN_QUESTION),
            "success_metrics": of_type(ArtifactType.SUCCESS_METRIC),
            "branch_summary": branch_summary,
            "traceability": traceability,
        }

    def export(self, session_id: str, format_id: str = "json") -> tuple[str, str]:
        """Return ``(rendered_content, media_type)`` for the given format."""

        package = self.build_package(session_id)
        exporter = get_exporter(format_id)
        return exporter.export(package), exporter.media_type

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _brief(a) -> dict:  # type: ignore[no-untyped-def]
        return {
            "id": a.id,
            "title": a.title,
            "statement": a.statement,
            "confidence": a.confidence,
            "validation_state": a.validation_state.value,
        }

    @staticmethod
    def _summary(session, confirmed, candidate, artifacts) -> str:  # type: ignore[no-untyped-def]
        n_open = sum(1 for a in artifacts if a.artifact_type == ArtifactType.OPEN_QUESTION)
        return (
            f"Discovery session for {session.customer} ({session.title}). "
            f"{len(confirmed)} confirmed requirement(s) and {len(candidate)} candidate "
            f"requirement(s) were derived from the conversation, with {n_open} open "
            f"question(s) still to resolve. All items retain traceability to their source "
            f"transcript evidence. Candidate items require explicit customer confirmation "
            f"before baselining."
        )
