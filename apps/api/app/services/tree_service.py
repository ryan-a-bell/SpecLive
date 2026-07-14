from __future__ import annotations

from sqlalchemy.orm import Session

from app.enums import ArtifactStatus
from app.models import DiscoveryArtifact
from app.schemas import DiscoveryTree, TreeNode
from app.services import artifact_service

# Ordering of sibling types so a need's children render requirement, constraint,
# risk, assumption, question — matching the prototype tree.
_TYPE_ORDER = {
    "objective": 0,
    "stakeholder_need": 1,
    "requirement": 2,
    "constraint": 3,
    "risk": 4,
    "assumption": 5,
    "success_metric": 6,
    "open_question": 7,
    "decision": 8,
    "integration": 9,
    "stakeholder": 10,
}

_HIDDEN = {ArtifactStatus.REJECTED, ArtifactStatus.MERGED, ArtifactStatus.SUPERSEDED}


def build_tree(db: Session, session_id: str) -> DiscoveryTree:
    artifacts = [
        a for a in artifact_service.list_artifacts(db, session_id) if a.status not in _HIDDEN
    ]
    by_id = {a.id: a for a in artifacts}
    children: dict[str | None, list[DiscoveryArtifact]] = {}
    for a in artifacts:
        parent = a.parent_id if a.parent_id in by_id else None
        children.setdefault(parent, []).append(a)

    def to_node(artifact: DiscoveryArtifact) -> TreeNode:
        kids = sorted(
            children.get(artifact.id, []),
            key=lambda a: (_TYPE_ORDER.get(str(a.artifact_type), 99), a.created_at),
        )
        return TreeNode(
            id=artifact.id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            statement=artifact.statement,
            status=artifact.status,
            confidence=artifact.confidence,
            validation_state=artifact.validation_state,
            evidence_count=len(artifact.evidence_links),
            parent_id=artifact.parent_id,
            children=[to_node(k) for k in kids],
        )

    roots = sorted(
        children.get(None, []),
        key=lambda a: (_TYPE_ORDER.get(str(a.artifact_type), 99), a.created_at),
    )
    return DiscoveryTree(session_id=session_id, roots=[to_node(r) for r in roots])
