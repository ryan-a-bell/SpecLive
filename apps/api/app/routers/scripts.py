from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ScriptAdvance, ScriptRead, ScriptStateRead
from app.services import script_service

# Global script catalog.
router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])
# Session-scoped script state.
session_router = APIRouter(prefix="/api/v1/sessions", tags=["scripts"])


@router.get("", response_model=list[ScriptRead])
def list_scripts(db: Session = Depends(get_db)) -> list[ScriptRead]:
    return [ScriptRead.model_validate(s) for s in script_service.list_scripts(db)]


@router.get("/{script_id}", response_model=ScriptRead)
def get_script(script_id: str, db: Session = Depends(get_db)) -> ScriptRead:
    return ScriptRead.model_validate(script_service.get_script(db, script_id))


@session_router.get("/{session_id}/script", response_model=ScriptStateRead)
def script_state(session_id: str, db: Session = Depends(get_db)) -> ScriptStateRead:
    return script_service.get_state(db, session_id)


@session_router.post("/{session_id}/script/advance", response_model=ScriptStateRead)
async def advance_script(
    session_id: str, payload: ScriptAdvance, db: Session = Depends(get_db)
) -> ScriptStateRead:
    return await script_service.advance(db, session_id, payload.target_sequence)
