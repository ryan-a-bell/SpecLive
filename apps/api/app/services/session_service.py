"""Session lifecycle operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ..db import models as m
from ..domain import entities as e
from ..domain.enums import SessionStatus
from ..events import EventBus
from ..repositories import SessionRepository
from ..repositories.mappers import session_to_domain
from .errors import NotFoundError


class SessionService:
    def __init__(self, repo: SessionRepository, bus: EventBus) -> None:
        self._repo = repo
        self._bus = bus

    def create(
        self,
        *,
        title: str,
        customer: str,
        facilitator: str,
        script_id: str | None = None,
        metadata: dict | None = None,
    ) -> e.DiscoverySession:
        row = m.DiscoverySessionORM(
            id=str(uuid4()),
            title=title,
            customer=customer,
            facilitator=facilitator,
            status=SessionStatus.ACTIVE.value,
            started_at=datetime.now(UTC),
            script_id=script_id,
            meta=metadata or {},
        )
        self._repo.add_session(row)
        self._repo.commit()
        return session_to_domain(row)

    def get(self, session_id: str) -> e.DiscoverySession:
        row = self._repo.get_session(session_id)
        if row is None:
            raise NotFoundError(f"Session {session_id} not found")
        return session_to_domain(row)

    def list(self) -> list[e.DiscoverySession]:
        return [session_to_domain(r) for r in self._repo.list_sessions()]

    def patch(self, session_id: str, **changes: object) -> e.DiscoverySession:
        row = self._repo.get_session(session_id)
        if row is None:
            raise NotFoundError(f"Session {session_id} not found")
        field_map = {"metadata": "meta"}
        for key, value in changes.items():
            if value is None:
                continue
            attr = field_map.get(key, key)
            if key == "status":
                value = SessionStatus(value).value
                if value == SessionStatus.COMPLETED.value:
                    row.ended_at = datetime.now(UTC)
            if key == "script_id" and value != row.script_id:
                # Switching scripts restarts advancement at the first stage.
                meta = dict(row.meta or {})
                meta["script_stage_index"] = 0
                row.meta = meta
            setattr(row, attr, value)
        self._repo.commit()
        return session_to_domain(row)
