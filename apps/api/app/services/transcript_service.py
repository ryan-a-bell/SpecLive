from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import SegmentStatus
from app.events import DomainEvent, EventType, get_event_bus
from app.ids import next_segment_id, next_sequence_number
from app.models import TranscriptSegment
from app.schemas import SegmentCreate
from app.services.session_service import get_session


async def add_segment(db: Session, session_id: str, data: SegmentCreate) -> TranscriptSegment:
    get_session(db, session_id)  # existence check
    sequence = next_sequence_number(db, session_id)
    # If explicit timings are absent, lay segments end-to-end at ~8s each.
    start = data.start_time if data.start_time is not None else float((sequence - 1) * 8)
    end = data.end_time if data.end_time is not None else start + 8.0
    segment = TranscriptSegment(
        id=next_segment_id(db, session_id),
        session_id=session_id,
        sequence_number=sequence,
        speaker=data.speaker,
        start_time=start,
        end_time=end,
        text=data.text,
        is_final=data.is_final,
        status=SegmentStatus.RECEIVED,
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)

    bus = get_event_bus()
    await bus.publish(
        DomainEvent(
            type=EventType.TRANSCRIPT_SEGMENT_RECEIVED,
            session_id=session_id,
            payload={"segment_id": segment.id, "text": segment.text, "speaker": segment.speaker},
        )
    )
    if segment.is_final:
        await bus.publish(
            DomainEvent(
                type=EventType.TRANSCRIPT_SEGMENT_FINALIZED,
                session_id=session_id,
                payload={"segment_id": segment.id},
            )
        )
    return segment


def list_segments(db: Session, session_id: str) -> list[TranscriptSegment]:
    get_session(db, session_id)
    return list(
        db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.session_id == session_id)
            .order_by(TranscriptSegment.sequence_number)
        )
    )


def get_segment(db: Session, segment_id: str) -> TranscriptSegment | None:
    return db.get(TranscriptSegment, segment_id)


def set_status(db: Session, segment: TranscriptSegment, status: SegmentStatus) -> None:
    segment.status = status
    db.commit()
