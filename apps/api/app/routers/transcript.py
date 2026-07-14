from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import SegmentCreate, SegmentRead
from app.services import analysis_service, transcript_service

router = APIRouter(prefix="/api/v1/sessions", tags=["transcript"])


@router.post("/{session_id}/transcript", response_model=SegmentRead, status_code=201)
async def add_segment(
    session_id: str, payload: SegmentCreate, db: Session = Depends(get_db)
) -> SegmentRead:
    segment = await transcript_service.add_segment(db, session_id, payload)
    if payload.analyze and segment.is_final:
        await analysis_service.analyze_segment(db, segment)
        db.refresh(segment)
    return SegmentRead.model_validate(segment)


@router.get("/{session_id}/transcript", response_model=list[SegmentRead])
def list_transcript(session_id: str, db: Session = Depends(get_db)) -> list[SegmentRead]:
    return [
        SegmentRead.model_validate(s) for s in transcript_service.list_segments(db, session_id)
    ]
