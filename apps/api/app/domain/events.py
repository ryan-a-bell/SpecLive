"""Domain events.

Events are the internal contract that lets the MVP run synchronously today while
remaining compatible with a queue-backed bus later. Services publish events; the
streaming layer and (future) async workers subscribe.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
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


class DomainEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EventType
    session_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_wire(self) -> dict[str, Any]:
        """Serializable form for websocket / queue transport."""

        return {
            "id": self.id,
            "type": self.type.value,
            "session_id": self.session_id,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
        }
