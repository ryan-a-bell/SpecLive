from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    SessionCreate,
    SessionRead,
    SessionUpdate,
)
from app.services import session_service

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _read(db: Session, obj) -> SessionRead:
    data = SessionRead.model_validate(obj)
    data.stats = session_service.session_stats(db, obj.id)
    return data


@router.post("", response_model=SessionRead, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionRead:
    session = session_service.create_session(db, payload)
    return _read(db, session)


@router.get("", response_model=list[SessionRead])
def list_sessions(db: Session = Depends(get_db)) -> list[SessionRead]:
    return [_read(db, s) for s in session_service.list_sessions(db)]


@router.get("/{session_id}", response_model=SessionRead)
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionRead:
    return _read(db, session_service.get_session(db, session_id))


@router.patch("/{session_id}", response_model=SessionRead)
def update_session(
    session_id: str, payload: SessionUpdate, db: Session = Depends(get_db)
) -> SessionRead:
    return _read(db, session_service.update_session(db, session_id, payload))
