from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    ArtifactAction,
    ArtifactCreate,
    ArtifactMerge,
    ArtifactRead,
    ArtifactUpdate,
    EvidenceLinkCreate,
    EvidenceLinkRead,
    RevisionRead,
)
from app.services import artifact_service, evidence_service, revision_service

# Session-scoped collection routes.
session_router = APIRouter(prefix="/api/v1/sessions", tags=["artifacts"])
# Artifact-scoped item routes.
router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


@session_router.get("/{session_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(session_id: str, db: Session = Depends(get_db)) -> list[ArtifactRead]:
    return [
        ArtifactRead.model_validate(a) for a in artifact_service.list_artifacts(db, session_id)
    ]


@session_router.post("/{session_id}/artifacts", response_model=ArtifactRead, status_code=201)
async def create_artifact(
    session_id: str, payload: ArtifactCreate, db: Session = Depends(get_db)
) -> ArtifactRead:
    artifact = await artifact_service.create_artifact(db, session_id, payload)
    return ArtifactRead.model_validate(artifact)


@router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: str, db: Session = Depends(get_db)) -> ArtifactRead:
    return ArtifactRead.model_validate(artifact_service.get_artifact(db, artifact_id))


@router.patch("/{artifact_id}", response_model=ArtifactRead)
async def update_artifact(
    artifact_id: str, payload: ArtifactUpdate, db: Session = Depends(get_db)
) -> ArtifactRead:
    return ArtifactRead.model_validate(
        await artifact_service.update_artifact(db, artifact_id, payload)
    )


@router.post("/{artifact_id}/confirm", response_model=ArtifactRead)
async def confirm_artifact(
    artifact_id: str, payload: ArtifactAction, db: Session = Depends(get_db)
) -> ArtifactRead:
    return ArtifactRead.model_validate(
        await artifact_service.confirm_artifact(
            db, artifact_id, payload.changed_by, payload.change_reason
        )
    )


@router.post("/{artifact_id}/reject", response_model=ArtifactRead)
async def reject_artifact(
    artifact_id: str, payload: ArtifactAction, db: Session = Depends(get_db)
) -> ArtifactRead:
    return ArtifactRead.model_validate(
        await artifact_service.reject_artifact(
            db, artifact_id, payload.changed_by, payload.change_reason
        )
    )


@router.post("/{artifact_id}/merge", response_model=ArtifactRead)
async def merge_artifact(
    artifact_id: str, payload: ArtifactMerge, db: Session = Depends(get_db)
) -> ArtifactRead:
    return ArtifactRead.model_validate(
        await artifact_service.merge_artifact(
            db, artifact_id, payload.target_id, payload.changed_by, payload.change_reason
        )
    )


@router.get("/{artifact_id}/revisions", response_model=list[RevisionRead])
def list_revisions(artifact_id: str, db: Session = Depends(get_db)) -> list[RevisionRead]:
    return [RevisionRead.model_validate(r) for r in revision_service.list_revisions(db, artifact_id)]


@router.post("/{artifact_id}/evidence", response_model=EvidenceLinkRead, status_code=201)
def add_evidence(
    artifact_id: str, payload: EvidenceLinkCreate, db: Session = Depends(get_db)
) -> EvidenceLinkRead:
    link = evidence_service.create_link(db, artifact_id, payload)
    return EvidenceLinkRead.model_validate(link)
