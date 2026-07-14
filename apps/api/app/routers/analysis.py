from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AnalyzeRequest, AnalyzeResult, ArtifactRead, EvidenceLinkRead
from app.services import analysis_service, export_service, transcript_service

router = APIRouter(prefix="/api/v1/sessions", tags=["analysis"])


@router.post("/{session_id}/analyze", response_model=AnalyzeResult)
async def analyze(
    session_id: str, payload: AnalyzeRequest, db: Session = Depends(get_db)
) -> AnalyzeResult:
    segments = transcript_service.list_segments(db, session_id)
    if payload.segment_ids:
        wanted = set(payload.segment_ids)
        segments = [s for s in segments if s.id in wanted]

    artifacts: list = []
    links: list = []
    for segment in segments:
        a, ls = await analysis_service.analyze_segment(db, segment)
        artifacts.extend(a)
        links.extend(ls)

    return AnalyzeResult(
        created_artifacts=[ArtifactRead.model_validate(a) for a in artifacts],
        created_evidence_links=[EvidenceLinkRead.model_validate(link) for link in links],
    )


@router.get("/{session_id}/export")
def export(
    session_id: str,
    fmt: str = Query("json", pattern="^(json|markdown)$"),
    download: bool = Query(False),
    db: Session = Depends(get_db),
) -> Response:
    envelope = export_service.export_package(db, session_id, fmt)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{envelope.filename}"'
    return Response(content=envelope.body, media_type=envelope.content_type, headers=headers)
