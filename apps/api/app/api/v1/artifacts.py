"""Artifact, evidence, and lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...domain import entities as e
from ..deps import Services, get_services
from ..schemas import (
    ArtifactCreate,
    ArtifactPatch,
    ConfirmRequest,
    EvidenceCreate,
    MergeRequest,
    RejectRequest,
)

router = APIRouter(tags=["artifacts"])


@router.get("/sessions/{session_id}/artifacts", response_model=list[e.DiscoveryArtifact])
def list_artifacts(
    session_id: str, svc: Services = Depends(get_services)
) -> list[e.DiscoveryArtifact]:
    return svc.artifacts.list_for_session(session_id)


@router.post(
    "/sessions/{session_id}/artifacts", response_model=e.DiscoveryArtifact, status_code=201
)
def create_artifact(
    session_id: str, body: ArtifactCreate, svc: Services = Depends(get_services)
) -> e.DiscoveryArtifact:
    return svc.artifacts.create(
        session_id,
        artifact_type=body.artifact_type,
        title=body.title,
        statement=body.statement,
        confidence=body.confidence,
        rationale=body.rationale,
        parent_id=body.parent_id,
        branch_id=body.branch_id,
        validation_state=body.validation_state,
        actor_is_human=True,
    )


@router.get("/artifacts/{artifact_id}", response_model=e.DiscoveryArtifact)
def get_artifact(artifact_id: str, svc: Services = Depends(get_services)) -> e.DiscoveryArtifact:
    return svc.artifacts.get(artifact_id)


@router.patch("/artifacts/{artifact_id}", response_model=e.DiscoveryArtifact)
def patch_artifact(
    artifact_id: str, body: ArtifactPatch, svc: Services = Depends(get_services)
) -> e.DiscoveryArtifact:
    changes = body.model_dump(exclude_unset=True)
    change_reason = changes.pop("change_reason", None)
    return svc.artifacts.update(artifact_id, change_reason=change_reason, **changes)


@router.get("/artifacts/{artifact_id}/evidence", response_model=list[e.EvidenceLink])
def list_evidence(artifact_id: str, svc: Services = Depends(get_services)) -> list[e.EvidenceLink]:
    return svc.artifacts.evidence_for(artifact_id)


@router.post("/artifacts/{artifact_id}/evidence", response_model=e.EvidenceLink, status_code=201)
def add_evidence(
    artifact_id: str, body: EvidenceCreate, svc: Services = Depends(get_services)
) -> e.EvidenceLink:
    return svc.artifacts.add_evidence(
        artifact_id,
        transcript_segment_id=body.transcript_segment_id,
        quote_start=body.quote_start,
        quote_end=body.quote_end,
        quoted_text=body.quoted_text,
        relationship=body.relationship,
        confidence=body.confidence,
        rationale=body.rationale,
    )


@router.get("/artifacts/{artifact_id}/revisions", response_model=list[e.ArtifactRevision])
def list_revisions(
    artifact_id: str, svc: Services = Depends(get_services)
) -> list[e.ArtifactRevision]:
    return svc.artifacts.revisions_for(artifact_id)


@router.post("/artifacts/{artifact_id}/confirm", response_model=e.DiscoveryArtifact)
def confirm_artifact(
    artifact_id: str, body: ConfirmRequest | None = None, svc: Services = Depends(get_services)
) -> e.DiscoveryArtifact:
    changed_by = body.changed_by if body else "facilitator"
    return svc.artifacts.confirm(artifact_id, changed_by=changed_by)


@router.post("/artifacts/{artifact_id}/reject", response_model=e.DiscoveryArtifact)
def reject_artifact(
    artifact_id: str, body: RejectRequest | None = None, svc: Services = Depends(get_services)
) -> e.DiscoveryArtifact:
    reason = body.reason if body else None
    return svc.artifacts.reject(artifact_id, reason=reason)


@router.post("/artifacts/{artifact_id}/merge", response_model=e.DiscoveryArtifact)
def merge_artifact(
    artifact_id: str, body: MergeRequest, svc: Services = Depends(get_services)
) -> e.DiscoveryArtifact:
    return svc.artifacts.merge(artifact_id, into_artifact_id=body.into_artifact_id)
