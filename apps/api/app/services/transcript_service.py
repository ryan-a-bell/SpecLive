"""Transcript ingestion."""

from __future__ import annotations

from uuid import uuid4

from ..db import models as m
from ..domain import entities as e
from ..domain.enums import Speaker
from ..domain.events import DomainEvent, EventType
from ..events import EventBus
from ..repositories import SessionRepository
from ..repositories.mappers import segment_to_domain
from .errors import NotFoundError


class TranscriptService:
    def __init__(self, repo: SessionRepository, bus: EventBus) -> None:
        self._repo = repo
        self._bus = bus

    def add_segment(
        self,
        session_id: str,
        *,
        speaker: Speaker,
        text: str,
        start_time: float | None = None,
        end_time: float | None = None,
        is_final: bool = True,
        sequence_number: int | None = None,
        segment_id: str | None = None,
    ) -> e.TranscriptSegment:
        if self._repo.get_session(session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")
        seq = (
            sequence_number if sequence_number is not None else self._repo.next_sequence(session_id)
        )
        row = m.TranscriptSegmentORM(
            id=segment_id or str(uuid4()),
            session_id=session_id,
            sequence_number=seq,
            speaker=Speaker(speaker).value,
            start_time=start_time,
            end_time=end_time,
            text=text,
            is_final=is_final,
        )
        self._repo.add_segment(row)
        self._repo.commit()
        segment = segment_to_domain(row)
        self._bus.publish(
            DomainEvent(
                type=(
                    EventType.TRANSCRIPT_SEGMENT_FINALIZED
                    if is_final
                    else EventType.TRANSCRIPT_SEGMENT_RECEIVED
                ),
                session_id=session_id,
                payload=segment.model_dump(mode="json"),
            )
        )
        return segment

    def list_segments(self, session_id: str) -> list[e.TranscriptSegment]:
        if self._repo.get_session(session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")
        return [segment_to_domain(r) for r in self._repo.list_segments(session_id)]
