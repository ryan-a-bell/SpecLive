"""Internal event abstraction.

Synchronous in this increment, but the `EventBus` interface is shaped so a
future queue-backed implementation (Redis, Kafka) is a drop-in replacement
(ADR-0005). Handlers are called in registration order; a failing handler is
logged and does not abort the publish.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.logging import get_logger

logger = get_logger("events")


class EventType:
    TRANSCRIPT_SEGMENT_RECEIVED = "transcript.segment.received"
    TRANSCRIPT_SEGMENT_FINALIZED = "transcript.segment.finalized"
    ARTIFACT_CANDIDATE_CREATED = "artifact.candidate.created"
    ARTIFACT_UPDATED = "artifact.updated"
    ARTIFACT_CONFIRMED = "artifact.confirmed"
    ARTIFACT_REJECTED = "artifact.rejected"
    EVIDENCE_LINK_CREATED = "evidence.link.created"
    BRANCH_CREATED = "branch.created"
    BRANCH_NODE_CREATED = "branch.node.created"
    SCRIPT_STAGE_COMPLETED = "script.stage.completed"
    QUESTION_RECOMMENDED = "question.recommended"
    COVERAGE_UPDATED = "coverage.updated"


@dataclass(slots=True)
class DomainEvent:
    type: str
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "session_id": self.session_id,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
        }


Handler = Callable[[DomainEvent], Awaitable[None] | None]


class EventBus:
    """In-process pub/sub. Interface is future-queue compatible."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        self._wildcard.append(handler)

    def unsubscribe_all(self, handler: Handler) -> None:
        if handler in self._wildcard:
            self._wildcard.remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        logger.info("event.published", type=event.type, session_id=event.session_id)
        for handler in [*self._handlers.get(event.type, []), *self._wildcard]:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:  # noqa: BLE001 - handler isolation is intentional
                logger.exception("event.handler_failed", type=event.type)


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus
