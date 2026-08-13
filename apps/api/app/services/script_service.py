"""Discovery-script access and per-session advancement.

Advancement state (which stage a given session is on) is stored in the session
``metadata`` under ``script_stage_index`` to avoid a dedicated table in this
increment.
"""

from __future__ import annotations

from ..domain import entities as e
from ..domain.events import DomainEvent, EventType
from ..events import EventBus
from ..repositories import SessionRepository
from ..repositories.mappers import script_to_domain
from .errors import NotFoundError, ValidationError

_STAGE_INDEX_KEY = "script_stage_index"


class ScriptService:
    def __init__(self, repo: SessionRepository, bus: EventBus) -> None:
        self._repo = repo
        self._bus = bus

    def list_scripts(self) -> list[e.ScriptDefinition]:
        return [script_to_domain(s) for s in self._repo.list_scripts()]

    def get_script(self, script_id: str) -> e.ScriptDefinition:
        row = self._repo.get_script(script_id)
        if row is None:
            raise NotFoundError(f"Script {script_id} not found")
        return script_to_domain(row)

    def current_stage_index(self, session_id: str) -> int:
        session = self._repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        return int((session.meta or {}).get(_STAGE_INDEX_KEY, 0))

    def state(self, session_id: str) -> dict:
        session = self._repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        if not session.script_id:
            raise ValidationError("Session has no script attached")
        script = self.get_script(session.script_id)
        idx = self.current_stage_index(session_id)
        stages = script.stages
        current = stages[idx] if 0 <= idx < len(stages) else None
        return {
            "script": script.model_dump(mode="json"),
            "current_index": idx,
            "current_stage": current.model_dump(mode="json") if current else None,
            "completed_stage_ids": [s.id for s in stages[:idx]],
            "total_stages": len(stages),
        }

    def advance(self, session_id: str) -> dict:
        session = self._repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        state = self.state(session_id)
        idx = state["current_index"]
        completed_stage = state["current_stage"]
        total = state["total_stages"]
        if idx < total - 1:
            idx += 1
        meta = dict(session.meta or {})
        meta[_STAGE_INDEX_KEY] = idx
        session.meta = meta
        self._repo.commit()
        if completed_stage is not None:
            self._bus.publish(
                DomainEvent(
                    type=EventType.SCRIPT_STAGE_COMPLETED,
                    session_id=session_id,
                    payload={
                        "stage_id": completed_stage["id"],
                        "sequence": completed_stage["sequence"],
                    },
                )
            )
        return self.state(session_id)
