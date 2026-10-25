"""Discovery-script access and per-session advancement.

Advancement state (which stage a given session is on) is stored in the session
``metadata`` under ``script_stage_index`` to avoid a dedicated table in this
increment.
"""

from __future__ import annotations

from uuid import uuid4

from ..db import models as m
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

    def list_scripts(self, *, include_archived: bool = False) -> list[e.ScriptDefinition]:
        return [
            script_to_domain(s) for s in self._repo.list_scripts(include_archived=include_archived)
        ]

    def get_script(self, script_id: str) -> e.ScriptDefinition:
        row = self._repo.get_script(script_id)
        if row is None:
            raise NotFoundError(f"Script {script_id} not found")
        return script_to_domain(row)

    @staticmethod
    def _clean_stages(stages: list[dict]) -> list[dict]:
        if not stages:
            raise ValidationError("A discovery script must contain at least one stage")
        cleaned: list[dict] = []
        for stage in stages:
            title = str(stage.get("title", "")).strip()
            prompt = str(stage.get("primary_prompt", "")).strip()
            if not title or not prompt:
                raise ValidationError("Every script stage needs a title and primary prompt")
            cleaned.append(
                {
                    **stage,
                    "title": title,
                    "objective": str(stage.get("objective", "")).strip(),
                    "primary_prompt": prompt,
                    "alternative_prompts": [
                        str(value).strip()
                        for value in stage.get("alternative_prompts", [])
                        if str(value).strip()
                    ],
                    "completion_criteria": [
                        str(value).strip()
                        for value in stage.get("completion_criteria", [])
                        if str(value).strip()
                    ],
                }
            )
        return cleaned

    @staticmethod
    def _stage_rows(
        script_id: str,
        stages: list[dict],
        *,
        existing_ids: set[str] | None = None,
    ) -> list[m.ScriptStageORM]:
        allowed_ids = existing_ids or set()
        rows: list[m.ScriptStageORM] = []
        for sequence, stage in enumerate(stages):
            requested_id = stage.get("id")
            stage_id = requested_id if requested_id in allowed_ids else str(uuid4())
            rows.append(
                m.ScriptStageORM(
                    id=stage_id,
                    script_id=script_id,
                    sequence=sequence,
                    title=stage["title"],
                    objective=stage["objective"],
                    primary_prompt=stage["primary_prompt"],
                    alternative_prompts=stage["alternative_prompts"],
                    completion_criteria=stage["completion_criteria"],
                )
            )
        return rows

    def create(
        self,
        *,
        name: str,
        version: str,
        description: str,
        stages: list[dict],
    ) -> e.ScriptDefinition:
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("A discovery script needs a name")
        script_id = str(uuid4())
        cleaned = self._clean_stages(stages)
        row = m.ScriptDefinitionORM(
            id=script_id,
            name=clean_name,
            version=version.strip() or "1.0.0",
            description=description.strip(),
            archived=False,
        )
        row.stages = self._stage_rows(script_id, cleaned)
        self._repo.add_script(row)
        self._repo.commit()
        return script_to_domain(row)

    def update(
        self,
        script_id: str,
        *,
        name: str,
        version: str,
        description: str,
        stages: list[dict],
    ) -> e.ScriptDefinition:
        row = self._repo.get_script(script_id)
        if row is None:
            raise NotFoundError(f"Script {script_id} not found")
        if row.archived:
            raise ValidationError("Archived scripts cannot be edited")
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("A discovery script needs a name")
        cleaned = self._clean_stages(stages)
        existing_ids = {stage.id for stage in row.stages}
        row.name = clean_name
        row.version = version.strip() or "1.0.0"
        row.description = description.strip()
        row.stages = self._stage_rows(script_id, cleaned, existing_ids=existing_ids)
        self._repo.commit()
        return script_to_domain(row)

    def archive(self, script_id: str) -> e.ScriptDefinition:
        row = self._repo.get_script(script_id)
        if row is None:
            raise NotFoundError(f"Script {script_id} not found")
        if any(session.script_id == script_id for session in self._repo.list_sessions()):
            raise ValidationError("A script attached to a conversation cannot be archived")
        row.archived = True
        self._repo.commit()
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
