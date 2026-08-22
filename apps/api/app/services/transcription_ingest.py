"""Shared transcription ingest: speaker resolution, persistence, and framing.

Both the live microphone WebSocket (`api/v1/audio.py`) and the file-upload REST
endpoint (`api/v1/transcribe.py`) turn provider-neutral ``TranscriptEvent``s into
persisted segments the exact same way. That logic lives here so the two entry
points cannot drift apart: a partial is streamed but never stored, a non-empty
final is persisted through :class:`TranscriptService` (which publishes the domain
event the analysis pipeline listens for), and speaker identity is resolved
identically whether the audio came from a mic or an uploaded recording.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from typing import TypedDict

from ..database import SessionLocal
from ..domain.enums import Speaker, SpeakerSource
from ..events import get_event_bus
from ..providers import TranscriptEvent
from ..providers.base import SpeechToTextProvider
from ..repositories import SqlAlchemySessionRepository
from .transcript_service import TranscriptService

#: One second of canonical SpecLive audio (16 kHz mono signed 16-bit PCM).
BYTES_PER_SECOND = 16000 * 2


class ResolvedIdentity(TypedDict):
    speaker: Speaker
    speaker_id: str | None
    speaker_name: str | None
    speaker_source: SpeakerSource
    speaker_confidence: float | None


@dataclass
class SpeakerContext:
    """Resolves each provider event to a stable speaker identity.

    In ``manual`` mode every segment is stamped with a facilitator-supplied
    identity. In ``auto`` mode a provider-detected voice id maps to a known
    role when it names one, otherwise to a stable ``Voice N`` grouping so the
    correction workflow can relabel a whole voice at once.
    """

    mode: str = "auto"
    speaker: Speaker = Speaker.UNKNOWN
    speaker_id: str | None = None
    speaker_name: str | None = None
    detected_names: dict[str, str] = field(default_factory=dict)

    def resolve(self, event: TranscriptEvent) -> ResolvedIdentity:
        if self.mode == "manual":
            return {
                "speaker": self.speaker,
                "speaker_id": self.speaker_id,
                "speaker_name": self.speaker_name,
                "speaker_source": SpeakerSource.MANUAL,
                "speaker_confidence": 1.0,
            }
        detected_id = event.speaker
        if not detected_id:
            return {
                "speaker": Speaker.UNKNOWN,
                "speaker_id": None,
                "speaker_name": None,
                "speaker_source": SpeakerSource.UNKNOWN,
                "speaker_confidence": None,
            }
        try:
            role = Speaker(detected_id)
            name = detected_id.replace("_", " ").title()
        except ValueError:
            role = Speaker.UNKNOWN
            name = self.detected_names.setdefault(
                detected_id, f"Voice {len(self.detected_names) + 1}"
            )
        return {
            "speaker": role,
            "speaker_id": detected_id,
            "speaker_name": name,
            "speaker_source": SpeakerSource.DETECTED,
            "speaker_confidence": event.speaker_confidence,
        }


def persist_final(session_id: str, event: TranscriptEvent, identity: ResolvedIdentity) -> None:
    """Store a finalized segment, publishing the event the pipeline reacts to."""

    with SessionLocal() as db:
        service = TranscriptService(SqlAlchemySessionRepository(db), get_event_bus())
        service.add_segment(
            session_id,
            segment_id=event.segment_id,
            speaker=identity["speaker"],
            speaker_id=identity["speaker_id"],
            speaker_name=identity["speaker_name"],
            speaker_source=identity["speaker_source"],
            speaker_confidence=identity["speaker_confidence"],
            text=event.text,
            start_time=event.start_time,
            end_time=event.end_time,
            is_final=True,
        )


def event_frame(
    session_id: str, event: TranscriptEvent, identity: ResolvedIdentity
) -> dict[str, object]:
    """Normalize a provider event into the wire shape clients consume."""

    return {
        "type": "transcript.final" if event.is_final else "transcript.partial",
        "session_id": session_id,
        "segment_id": event.segment_id,
        "text": event.text,
        "is_final": event.is_final,
        "speaker": identity["speaker"].value,
        "speaker_id": identity["speaker_id"],
        "speaker_name": identity["speaker_name"],
        "speaker_source": identity["speaker_source"].value,
        "speaker_confidence": identity["speaker_confidence"],
        "start_time": event.start_time,
        "end_time": event.end_time,
    }


def iter_pcm_frames(pcm: bytes, *, frame_bytes: int = BYTES_PER_SECOND) -> Iterable[bytes]:
    """Split canonical PCM into even-length frames a provider can stream.

    ``frame_bytes`` is rounded down to a whole sample so no frame ever splits a
    16-bit sample. A trailing partial sample (odd byte) is dropped.
    """

    step = max(2, frame_bytes - (frame_bytes % 2))
    usable = len(pcm) - (len(pcm) % 2)
    for start in range(0, usable, step):
        yield pcm[start : start + step]


async def transcribe_pcm(
    session_id: str,
    provider: SpeechToTextProvider,
    pcm: bytes,
    speaker_context: SpeakerContext,
    *,
    frame_bytes: int = BYTES_PER_SECOND,
) -> list[dict[str, object]]:
    """Run a bounded PCM buffer through a provider and persist its finals.

    Mirrors the live socket: a consumer drains provider events while frames are
    pushed, ``stop`` flushes the tail, and the consumer runs until the provider
    ends its stream. Returns the finalized segment frames in emission order.
    """

    finals: list[dict[str, object]] = []

    await provider.start(session_id)

    async def _consume() -> None:
        events: AsyncIterator[TranscriptEvent] = provider.events(session_id)
        async for event in events:
            identity = speaker_context.resolve(event)
            if event.is_final and event.text.strip():
                persist_final(session_id, event, identity)
                finals.append(event_frame(session_id, event, identity))

    consumer = asyncio.create_task(_consume())
    # Let the consumer start and subscribe to the provider's event stream before
    # any audio (or the terminal stop) is pushed — some providers hand off their
    # event queue on start and reclaim it on stop.
    await asyncio.sleep(0)
    try:
        for frame in iter_pcm_frames(pcm, frame_bytes=frame_bytes):
            if frame:
                await provider.push_audio(session_id, frame)
    finally:
        await provider.stop(session_id)
    await consumer
    return finals
