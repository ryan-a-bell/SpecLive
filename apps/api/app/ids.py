"""Human-readable, per-session sequential identifiers.

Artifacts get codes like REQ-002, NEED-001 (matching the prototype). Segments
get SEG-101+. IDs are unique within a session, which is enough for the demo and
keeps the UI legible; a global UUID column could be layered on later.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import ARTIFACT_CODE_PREFIX, ArtifactType
from app.models import ArtifactRevision, DiscoveryArtifact, TranscriptSegment

SEGMENT_START = 100


def next_segment_id(db: Session, session_id: str) -> str:
    count = db.scalar(
        select(func.count())
        .select_from(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
    )
    return f"SEG-{SEGMENT_START + (count or 0) + 1}"


def next_sequence_number(db: Session, session_id: str) -> int:
    current = db.scalar(
        select(func.max(TranscriptSegment.sequence_number)).where(
            TranscriptSegment.session_id == session_id
        )
    )
    return (current or 0) + 1


def next_artifact_id(db: Session, session_id: str, artifact_type: ArtifactType) -> str:
    prefix = ARTIFACT_CODE_PREFIX[artifact_type]
    count = db.scalar(
        select(func.count())
        .select_from(DiscoveryArtifact)
        .where(
            DiscoveryArtifact.session_id == session_id,
            DiscoveryArtifact.artifact_type == artifact_type,
        )
    )
    return f"{prefix}-{(count or 0) + 1:03d}"


def next_revision_number(db: Session, artifact_id: str) -> int:
    current = db.scalar(
        select(func.max(ArtifactRevision.revision_number)).where(
            ArtifactRevision.artifact_id == artifact_id
        )
    )
    return (current or 0) + 1


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def new_evidence_id() -> str:
    return new_id("EV")


def new_revision_id() -> str:
    return new_id("REV")


def new_branch_id() -> str:
    return new_id("BR")


def new_node_id() -> str:
    return new_id("ND")
