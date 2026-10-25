"""File-upload transcription: process a recorded audio file like a live session.

The live path streams microphone PCM over a WebSocket. This endpoint accepts an
uploaded recording (MP3, M4A, WAV, …), decodes it to canonical PCM once, and
runs it through the *same* provider-neutral ingest pipeline — so an uploaded
file produces the same persisted segments, domain events, derived artifacts, and
evidence as a live conversation, with whatever ``STT_PROVIDER`` is configured.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...domain.enums import Speaker
from ...logging import get_logger
from ...providers import get_stt_provider
from ...services.audio_decode import (
    AudioDecodeError,
    AudioDecodeUnavailable,
    decode_to_pcm16,
)
from ...services.transcription_ingest import (
    BYTES_PER_SECOND,
    SpeakerContext,
    transcribe_pcm,
)
from ..schemas import FileTranscriptionResult

router = APIRouter(tags=["transcription"])
logger = get_logger(__name__)

# Guardrail so a single upload cannot exhaust worker memory. ~100 MB of a
# compressed file is already many hours of speech.
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _session_exists(session_id: str) -> bool:
    from ...database import SessionLocal
    from ...repositories import SqlAlchemySessionRepository

    with SessionLocal() as db:
        return SqlAlchemySessionRepository(db).get_session(session_id) is not None


def _persist_recording(
    session_id: str, audio: bytes, *, filename: str | None, content_type: str | None
) -> None:
    """Best-effort: store the uploaded recording + regenerated content sidecars.

    A storage failure must never fail the transcription that already succeeded,
    so any error here is logged and swallowed. The explicit
    ``POST /sessions/{id}/storage/snapshot`` endpoint surfaces errors instead.
    """

    from ...config import get_settings
    from ...database import SessionLocal
    from ...repositories import SqlAlchemySessionRepository
    from ...services.export_service import ExportService
    from ...services.storage_service import ConversationStorageService
    from ...storage import get_content_store

    try:
        with SessionLocal() as db:
            repo = SqlAlchemySessionRepository(db)
            service = ConversationStorageService(
                repo, ExportService(repo), get_content_store(), get_settings()
            )
            service.snapshot(
                session_id,
                audio=audio,
                audio_filename=filename,
                audio_content_type=content_type,
            )
    except Exception:  # noqa: BLE001 - storage is best-effort on this path
        logger.exception("file_transcription.storage_snapshot_failed", session_id=session_id)


def _build_speaker_context(
    speaker_mode: str, speaker: str, speaker_id: str | None, speaker_name: str | None
) -> SpeakerContext:
    if speaker_mode not in {"auto", "manual"}:
        raise HTTPException(status_code=422, detail="speaker_mode must be 'auto' or 'manual'")
    if speaker_mode == "auto":
        return SpeakerContext(mode="auto")
    name = (speaker_name or "").strip()
    if not name:
        raise HTTPException(
            status_code=422, detail="speaker_name is required when speaker_mode is 'manual'"
        )
    try:
        role = Speaker(speaker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown speaker role: {speaker}") from exc
    return SpeakerContext(
        mode="manual",
        speaker=role,
        speaker_id=(speaker_id or None),
        speaker_name=name,
    )


@router.post(
    "/sessions/{session_id}/transcribe",
    response_model=FileTranscriptionResult,
    status_code=201,
)
async def transcribe_file(
    session_id: str,
    file: UploadFile = File(...),
    speaker_mode: str = Form("auto"),
    speaker: str = Form(Speaker.UNKNOWN.value),
    speaker_id: str | None = Form(None),
    speaker_name: str | None = Form(None),
) -> FileTranscriptionResult:
    """Transcribe an uploaded recording through the configured STT provider."""

    if not _session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    speaker_context = _build_speaker_context(speaker_mode, speaker, speaker_id, speaker_name)

    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded audio file is too large")

    try:
        pcm = decode_to_pcm16(data)
    except AudioDecodeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AudioDecodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        provider = get_stt_provider()
    except Exception as exc:  # noqa: BLE001 - configuration/adapter boundary
        logger.exception("file_transcription.provider_unavailable", session_id=session_id)
        raise HTTPException(status_code=503, detail="Transcription service is unavailable") from exc

    try:
        segments = await transcribe_pcm(session_id, provider, pcm, speaker_context)
    except Exception as exc:  # noqa: BLE001 - normalize provider failures
        logger.exception("file_transcription.failed", session_id=session_id)
        raise HTTPException(status_code=502, detail="Transcription failed") from exc

    # Persist the recording and regenerated content sidecars to the configured
    # store. Best-effort: never fail a completed transcription over storage.
    _persist_recording(session_id, data, filename=file.filename, content_type=file.content_type)

    return FileTranscriptionResult(
        session_id=session_id,
        source_filename=file.filename,
        audio_seconds=round(len(pcm) / BYTES_PER_SECOND, 2),
        segment_count=len(segments),
        segments=segments,
    )
