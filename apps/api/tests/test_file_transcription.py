"""File-upload transcription endpoint + audio decode contract tests."""

from __future__ import annotations

import asyncio
import io
import wave
from collections.abc import AsyncIterator

import pytest

from app.api.v1 import transcribe
from app.providers.base import SpeechToTextProvider, TranscriptEvent
from app.services import audio_decode
from app.services.audio_decode import AudioDecodeError, decode_to_pcm16
from app.services.transcription_ingest import iter_pcm_frames


def _wav_bytes(seconds: float, *, rate: int = 44100, channels: int = 2) -> bytes:
    frames = int(seconds * rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * frames * channels)
    return buffer.getvalue()


def _create_session(client) -> str:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/v1/sessions",
        json={"title": "Upload", "customer": "Acme", "facilitator": "Ryan"},
    )
    assert response.status_code == 201
    return response.json()["id"]


class _BoundedProvider(SpeechToTextProvider):
    """Emits a single final segment once audio has been pushed, then ends."""

    _END = object()

    def __init__(self) -> None:
        self.queues: dict[str, asyncio.Queue[TranscriptEvent | object]] = {}
        self.frames: dict[str, int] = {}

    async def start(self, session_id: str) -> None:
        self.queues[session_id] = asyncio.Queue()
        self.frames[session_id] = 0

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        assert len(pcm) % 2 == 0
        self.frames[session_id] += 1

    async def events(self, session_id: str) -> AsyncIterator[TranscriptEvent]:
        queue = self.queues[session_id]
        while True:
            item = await queue.get()
            if item is self._END:
                return
            assert isinstance(item, TranscriptEvent)
            yield item

    async def stop(self, session_id: str) -> None:
        queue = self.queues[session_id]
        if self.frames.get(session_id):
            queue.put_nowait(
                TranscriptEvent(
                    segment_id=f"file-{session_id}",
                    text="recorded words",
                    is_final=True,
                    speaker="customer",
                    speaker_confidence=0.88,
                )
            )
        queue.put_nowait(self._END)


# --- endpoint behavior ----------------------------------------------------
def test_upload_runs_through_pipeline_and_persists(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    monkeypatch.setattr(transcribe, "get_stt_provider", _BoundedProvider)

    response = client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"file": ("call.wav", _wav_bytes(2.0), "audio/wav")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["session_id"] == session_id
    assert body["source_filename"] == "call.wav"
    assert body["segment_count"] == 1
    assert body["segments"][0]["text"] == "recorded words"
    assert body["segments"][0]["speaker"] == "customer"
    # Decoded to 16 kHz mono, so ~2s regardless of the source 44.1 kHz stereo.
    assert body["audio_seconds"] == pytest.approx(2.0, abs=0.1)

    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
    assert transcript[-1]["id"] == f"file-{session_id}"
    assert transcript[-1]["text"] == "recorded words"
    assert transcript[-1]["is_final"] is True
    assert transcript[-1]["speaker"] == "customer"


def test_upload_works_with_default_configured_provider(client) -> None:  # type: ignore[no-untyped-def]
    """No monkeypatch: exercises whatever STT_PROVIDER is configured (mock)."""

    session_id = _create_session(client)
    response = client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"file": ("call.wav", _wav_bytes(1.0), "audio/wav")},
    )
    assert response.status_code == 201
    assert response.json()["segment_count"] >= 1


def test_upload_can_stamp_a_manual_speaker(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    monkeypatch.setattr(transcribe, "get_stt_provider", _BoundedProvider)

    response = client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"file": ("call.wav", _wav_bytes(1.0), "audio/wav")},
        data={"speaker_mode": "manual", "speaker": "customer", "speaker_name": "Maya"},
    )
    assert response.status_code == 201
    assert response.json()["segments"][0]["speaker_name"] == "Maya"
    assert response.json()["segments"][0]["speaker_source"] == "manual"


def test_manual_mode_requires_a_name(client) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    response = client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"file": ("call.wav", _wav_bytes(1.0), "audio/wav")},
        data={"speaker_mode": "manual", "speaker": "customer"},
    )
    assert response.status_code == 422


def test_upload_rejects_unknown_session(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/v1/sessions/missing/transcribe",
        files={"file": ("call.wav", _wav_bytes(1.0), "audio/wav")},
    )
    assert response.status_code == 404


def test_empty_upload_is_rejected(client) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    response = client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 422


def test_compressed_upload_without_ffmpeg_returns_503(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    monkeypatch.setattr(audio_decode.shutil, "which", lambda _: None)

    # Non-WAV bytes route to the ffmpeg path, which is unavailable here.
    response = client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"file": ("call.mp3", b"ID3\x03\x00\x00\x00fake mp3 payload", "audio/mpeg")},
    )
    assert response.status_code == 503
    assert "ffmpeg" in response.json()["detail"].lower()


# --- decode + framing units ----------------------------------------------
def test_decode_wav_resamples_to_canonical_pcm() -> None:
    pcm = decode_to_pcm16(_wav_bytes(1.0, rate=48000, channels=2))
    # 1 second of 16 kHz mono s16le is 32000 bytes (± a sample from resampling).
    assert abs(len(pcm) - 32000) <= 4
    assert len(pcm) % 2 == 0


def test_decode_rejects_empty_bytes() -> None:
    with pytest.raises(AudioDecodeError):
        decode_to_pcm16(b"")


def test_iter_pcm_frames_drops_trailing_odd_byte() -> None:
    frames = list(iter_pcm_frames(b"\x01\x02\x03\x04\x05", frame_bytes=2))
    assert frames == [b"\x01\x02", b"\x03\x04"]
    assert all(len(f) % 2 == 0 for f in frames)
