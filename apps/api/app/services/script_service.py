from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.events import DomainEvent, EventType, get_event_bus
from app.models import ScriptDefinition, ScriptStage
from app.schemas import ScriptStageRead, ScriptStateRead
from app.services.session_service import get_session


def list_scripts(db: Session) -> list[ScriptDefinition]:
    return list(db.scalars(select(ScriptDefinition)))


def get_script(db: Session, script_id: str) -> ScriptDefinition:
    script = db.get(ScriptDefinition, script_id)
    if script is None:
        raise NotFoundError(f"Script {script_id} not found")
    return script


def stage_to_read(stage: ScriptStage) -> ScriptStageRead:
    return ScriptStageRead(
        id=stage.id,
        sequence=stage.sequence,
        title=stage.title,
        objective=stage.objective,
        primary_prompt=stage.primary_prompt,
        alternative_prompts=json.loads(stage.alternative_prompts or "[]"),
        completion_criteria=stage.completion_criteria,
    )


def get_state(db: Session, session_id: str) -> ScriptStateRead:
    session = get_session(db, session_id)
    if session.script_id is None:
        return ScriptStateRead(
            script_id=None,
            current_sequence=0,
            total_stages=0,
            current_stage=None,
            completed_stages=[],
            recommended_question=None,
        )
    script = get_script(db, session.script_id)
    stages = sorted(script.stages, key=lambda s: s.sequence)
    current_seq = session.current_stage_sequence
    current = next((s for s in stages if s.sequence == current_seq), None)
    return ScriptStateRead(
        script_id=script.id,
        current_sequence=current_seq,
        total_stages=len(stages),
        current_stage=stage_to_read(current) if current else None,
        completed_stages=[s.sequence for s in stages if s.sequence < current_seq],
        recommended_question=current.primary_prompt if current else None,
        alternative_prompts=json.loads(current.alternative_prompts or "[]") if current else [],
    )


async def advance(db: Session, session_id: str, target_sequence: int | None) -> ScriptStateRead:
    session = get_session(db, session_id)
    completed_seq = session.current_stage_sequence
    if target_sequence is not None:
        session.current_stage_sequence = target_sequence
    else:
        session.current_stage_sequence += 1
    db.commit()

    await get_event_bus().publish(
        DomainEvent(
            type=EventType.SCRIPT_STAGE_COMPLETED,
            session_id=session_id,
            payload={"completed_sequence": completed_seq,
                     "current_sequence": session.current_stage_sequence},
        )
    )
    return get_state(db, session_id)
