"""Provider-neutral microphone audio ingestion WebSocket."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
from dataclasses import dataclass, field
from typing import TypedDict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...config import Settings, get_settings
from ...database import SessionLocal
from ...domain.enums import Speaker, SpeakerSource
from ...events import get_event_bus
from ...logging import get_logger
from ...providers import TranscriptEvent, get_stt_provider
from ...repositories import SqlAlchemySessionRepository
from ...services.transcript_service import TranscriptService
from ..schemas import TranscriptionCapability

router = APIRouter(tags=["transcription"])
logger = get_logger(__name__)

_AUDIO_FORMAT = {
    "encoding": "pcm_s16le",
    "sample_rate": 16000,
    "channels": 1,
}
_MAX_FRAME_BYTES = 16000 * 2 * 5  # five seconds of PCM per WebSocket frame


def _transcription_capability(settings: Settings) -> TranscriptionCapability:
    provider = settings.stt_provider
    if provider in {"local", "faster-whisper"}:
        available = importlib.util.find_spec("faster_whisper") is not None
        supports_partials = False
    elif provider == "openai":
        available = bool(settings.openai_api_key)
        supports_partials = True
    elif provider in {"wispr", "wispr-flow"}:
        available = bool(settings.wispr_flow_api_key and settings.wispr_flow_access_token)
        supports_partials = True
    elif provider == "mock":
        available = True
        supports_partials = True
    else:
        available = False
        supports_partials = False
    return TranscriptionCapability(
        available=available,
        supports_partials=supports_partials,
        supports_speaker_detection=(provider == "mock" or settings.stt_speaker_detection),
    )


@router.get("/transcription/status", response_model=TranscriptionCapability)
def transcription_status() -> TranscriptionCapability:
    """Return browser-relevant capabilities without exposing provider details."""

    return _transcription_capability(get_settings())


def _session_exists(session_id: str) -> bool:
    with SessionLocal() as db:
        return SqlAlchemySessionRepository(db).get_session(session_id) is not None


@dataclass
class _SpeakerContext:
    mode: str = "auto"
    speaker: Speaker = Speaker.UNKNOWN
    speaker_id: str | None = None
    speaker_name: str | None = None
    detected_names: dict[str, str] = field(default_factory=dict)

    def resolve(self, event: TranscriptEvent) -> _ResolvedIdentity:
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


class _ResolvedIdentity(TypedDict):
    speaker: Speaker
    speaker_id: str | None
    speaker_name: str | None
    speaker_source: SpeakerSource
    speaker_confidence: float | None


def _persist_final(
    session_id: str, event: TranscriptEvent, identity: _ResolvedIdentity
) -> None:
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


def _event_frame(
    session_id: str, event: TranscriptEvent, identity: _ResolvedIdentity
) -> dict[str, object]:
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


@router.websocket("/sessions/{session_id}/audio")
async def stream_audio(websocket: WebSocket, session_id: str) -> None:
    """Accept binary SpecLive PCM frames and return normalized transcript JSON."""

    await websocket.accept()
    if not _session_exists(session_id):
        await websocket.send_json(
            {"type": "transcription.error", "code": "session_not_found", "retryable": False}
        )
        await websocket.close(code=4404)
        return

    try:
        provider = get_stt_provider()
        await provider.start(session_id)
    except Exception:  # noqa: BLE001 - configuration/adapter boundary
        logger.exception("transcription.start_failed", session_id=session_id)
        await websocket.send_json(
            {
                "type": "transcription.error",
                "code": "provider_start_failed",
                "message": "Transcription service is unavailable",
                "retryable": False,
            }
        )
        await websocket.close(code=1011)
        return

    connected = True
    stop_requested = False
    speaker_context = _SpeakerContext()

    async def _send_events() -> None:
        async for event in provider.events(session_id):
            identity = speaker_context.resolve(event)
            if event.is_final and event.text.strip():
                _persist_final(session_id, event, identity)
            if connected:
                await websocket.send_json(_event_frame(session_id, event, identity))

    async def _receive_audio() -> None:
        nonlocal connected, stop_requested
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    connected = False
                    return
                pcm = message.get("bytes")
                if pcm is not None:
                    if len(pcm) > _MAX_FRAME_BYTES or len(pcm) % 2:
                        raise ValueError(
                            "Audio frames must be even-length PCM16 and at most 5 seconds"
                        )
                    await provider.push_audio(session_id, pcm)
                    continue
                raw = message.get("text")
                if raw is not None:
                    control = json.loads(raw)
                    if control.get("type") == "configure":
                        mode = control.get("speaker_mode")
                        if mode not in {"auto", "manual"}:
                            raise ValueError("speaker_mode must be 'auto' or 'manual'")
                        speaker_context.mode = mode
                        if mode == "manual":
                            speaker_context.speaker = Speaker(control.get("speaker", "unknown"))
                            speaker_context.speaker_id = (
                                str(control.get("speaker_id") or "") or None
                            )
                            speaker_context.speaker_name = (
                                str(control.get("speaker_name") or "").strip() or None
                            )
                            if speaker_context.speaker_name is None:
                                raise ValueError("Manual speaker_name is required")
                        await websocket.send_json(
                            {
                                "type": "transcription.configured",
                                "session_id": session_id,
                                "speaker_mode": mode,
                            }
                        )
                        continue
                    if control.get("type") == "stop":
                        stop_requested = True
                        return
                    if control.get("type") != "ping":
                        raise ValueError(
                            "Only 'configure', 'stop', and 'ping' control messages are supported"
                        )
        except WebSocketDisconnect:
            connected = False

    await websocket.send_json(
        {"type": "transcription.ready", "session_id": session_id, "audio": _AUDIO_FORMAT}
    )
    event_task = asyncio.create_task(_send_events())
    receive_task = asyncio.create_task(_receive_audio())
    await asyncio.sleep(0)  # let both tasks capture the active provider session

    try:
        done, _ = await asyncio.wait(
            {event_task, receive_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if event_task in done:
            await event_task
        if receive_task in done:
            await receive_task
    except Exception:  # noqa: BLE001 - normalize provider/transport failures
        logger.exception("transcription.stream_failed", session_id=session_id)
        if connected:
            with contextlib.suppress(Exception):
                await websocket.send_json(
                    {
                        "type": "transcription.error",
                        "code": "stream_failed",
                        "message": "Transcription service failed",
                        "retryable": True,
                    }
                )
    finally:
        receive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await receive_task
        with contextlib.suppress(Exception):
            await provider.stop(session_id)
        if not event_task.done():
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(event_task, timeout=2)
        if not event_task.done():
            event_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await event_task
        if connected:
            with contextlib.suppress(Exception):
                await websocket.send_json(
                    {
                        "type": "transcription.stopped",
                        "session_id": session_id,
                        "committed": stop_requested,
                    }
                )
                await websocket.close(code=1000)
