from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ids import new_revision_id, next_revision_number
from app.models import ArtifactRevision, DiscoveryArtifact


def record(
    db: Session,
    artifact: DiscoveryArtifact,
    before: dict,
    after: dict,
    *,
    changed_by: str,
    reason: str,
) -> ArtifactRevision | None:
    """Append an immutable revision capturing the changed fields only."""
    changed_before = {k: v for k, v in before.items() if before[k] != after.get(k)}
    changed_after = {k: v for k, v in after.items() if before.get(k) != after[k]}
    if not changed_after:
        return None

    revision = ArtifactRevision(
        id=new_revision_id(),
        artifact_id=artifact.id,
        revision_number=next_revision_number(db, artifact.id),
        previous_value=json.dumps(changed_before),
        new_value=json.dumps(changed_after),
        changed_by=changed_by,
        change_reason=reason,
    )
    db.add(revision)
    db.flush()
    return revision


def list_revisions(db: Session, artifact_id: str) -> list[ArtifactRevision]:
    return list(
        db.scalars(
            select(ArtifactRevision)
            .where(ArtifactRevision.artifact_id == artifact_id)
            .order_by(ArtifactRevision.revision_number)
        )
    )
