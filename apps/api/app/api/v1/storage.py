"""Content-storage endpoints: snapshot a conversation and inspect what's stored.

The raw recording captured on the live-mic path is not held server-side, so the
snapshot endpoint accepts an optional audio upload to persist alongside the
regenerated transcript / requirements / exports. Uploading a recording through
``POST /sessions/{id}/transcribe`` already triggers a best-effort snapshot with
that audio; this route is the explicit, on-demand equivalent.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..deps import Services, get_services
from ..schemas import StorageSnapshotResult, StoredContentInfo

router = APIRouter(prefix="/sessions", tags=["storage"])

# Same guardrail as the transcription upload path.
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


@router.post("/{session_id}/storage/snapshot", response_model=StorageSnapshotResult)
async def snapshot_storage(
    session_id: str,
    file: UploadFile | None = File(None),
    audio_filename: str | None = Form(None),
    svc: Services = Depends(get_services),
) -> StorageSnapshotResult:
    """Persist this conversation's content tree to the configured store."""

    audio: bytes | None = None
    filename = audio_filename
    content_type: str | None = None
    if file is not None:
        audio = await file.read()
        if len(audio) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Uploaded audio file is too large")
        filename = filename or file.filename
        content_type = file.content_type

    result = svc.storage.snapshot(
        session_id,
        audio=audio,
        audio_filename=filename,
        audio_content_type=content_type,
    )
    return StorageSnapshotResult(**result)


@router.get("/{session_id}/storage", response_model=StoredContentInfo)
def describe_storage(session_id: str, svc: Services = Depends(get_services)) -> StoredContentInfo:
    """List the content currently persisted for this conversation."""

    return StoredContentInfo(**svc.storage.describe(session_id))
