"""Builds the discovery tree projection from artifacts + evidence."""

from __future__ import annotations

from typing import Any

from ..domain.enums import ArtifactType, ValidationState
from ..repositories import SessionRepository
from ..repositories.mappers import artifact_to_domain

# Artifact types that can appear as top-level roots when they have no parent.
_ROOT_ORDER = [ArtifactType.OBJECTIVE, ArtifactType.STAKEHOLDER_NEED]


class TreeService:
    def __init__(self, repo: SessionRepository) -> None:
        self._repo = repo

    def build(self, session_id: str) -> dict[str, Any]:
        artifacts = [artifact_to_domain(r) for r in self._repo.list_artifacts(session_id)]
        evidence = self._repo.list_evidence(session_id)
        evidence_counts: dict[str, int] = {}
        for link in evidence:
            evidence_counts[link.artifact_id] = evidence_counts.get(link.artifact_id, 0) + 1

        by_id = {a.id: a for a in artifacts}
        children: dict[str | None, list[str]] = {}
        for a in artifacts:
            # Hide merged/rejected artifacts from the live tree.
            if a.validation_state in (ValidationState.MERGED, ValidationState.REJECTED):
                continue
            parent = a.parent_id if a.parent_id in by_id else None
            children.setdefault(parent, []).append(a.id)

        def node(artifact_id: str) -> dict[str, Any]:
            a = by_id[artifact_id]
            return {
                "id": a.id,
                "type": a.artifact_type.value,
                "title": a.title,
                "statement": a.statement,
                "status": a.status.value,
                "confidence": a.confidence,
                "validation_state": a.validation_state.value,
                "evidence_count": evidence_counts.get(a.id, 0),
                "parent_id": a.parent_id,
                "children": [node(cid) for cid in children.get(artifact_id, [])],
            }

        roots = [node(rid) for rid in children.get(None, [])]
        roots.sort(key=lambda n: _root_rank(n["type"]))
        return {"session_id": session_id, "roots": roots}


def _root_rank(type_value: str) -> int:
    order = [t.value for t in _ROOT_ORDER]
    return order.index(type_value) if type_value in order else len(order)
