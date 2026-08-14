"""Provider-neutral audio WebSocket contract tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.api.v1 import audio
from app.config import Settings
from app.providers.base import SpeechToTextProvider, TranscriptEvent


class EchoSpeechProvider(SpeechToTextProvider):
    _END = object()

    def __init__(self) -> None:
        self.queues: dict[str, asyncio.Queue[TranscriptEvent | object]] = {}

    async def start(self, session_id: str) -> None:
        self.queues[session_id] = asyncio.Queue()

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        assert pcm == b"\x00\x00" * 160
        self.queues[session_id].put_nowait(
            TranscriptEvent(
                segment_id=f"echo-{session_id}",
                text="live words",
                is_final=False,
                speaker="voice-7",
                speaker_confidence=0.91,
            )
        )

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
        queue.put_nowait(
            TranscriptEvent(
                segment_id=f"echo-{session_id}",
                text="live words finalized",
                is_final=True,
                speaker="voice-7",
                speaker_confidence=0.91,
            )
        )
        queue.put_nowait(self._END)


def _create_session(client) -> str:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/v1/sessions",
        json={"title": "Audio", "customer": "Acme", "facilitator": "Ryan"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_audio_socket_normalizes_and_persists_final(
    client, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    provider = EchoSpeechProvider()
    monkeypatch.setattr(audio, "get_stt_provider", lambda: provider)

    with client.websocket_connect(f"/api/v1/sessions/{session_id}/audio") as socket:
        ready = socket.receive_json()
        assert ready == {
            "type": "transcription.ready",
            "session_id": session_id,
            "audio": {"encoding": "pcm_s16le", "sample_rate": 16000, "channels": 1},
        }

        socket.send_json({"type": "configure", "speaker_mode": "auto"})
        assert socket.receive_json()["type"] == "transcription.configured"

        socket.send_bytes(b"\x00\x00" * 160)
        partial = socket.receive_json()
        assert partial["type"] == "transcript.partial"
        assert partial["segment_id"] == f"echo-{session_id}"
        assert partial["text"] == "live words"
        assert partial["speaker_id"] == "voice-7"
        assert partial["speaker_name"] == "Voice 1"
        assert partial["speaker_source"] == "detected"

        socket.send_json({"type": "stop"})
        final = socket.receive_json()
        assert final["type"] == "transcript.final"
        assert final["segment_id"] == f"echo-{session_id}"
        assert final["text"] == "live words finalized"
        assert socket.receive_json()["type"] == "transcription.stopped"

    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
    assert transcript[-1]["id"] == f"echo-{session_id}"
    assert transcript[-1]["text"] == "live words finalized"
    assert transcript[-1]["is_final"] is True
    assert transcript[-1]["speaker_id"] == "voice-7"
    assert transcript[-1]["speaker_name"] == "Voice 1"

    correction = client.patch(
        f"/api/v1/sessions/{session_id}/transcript/echo-{session_id}/speaker",
        json={"speaker": "customer", "speaker_name": "Maya", "apply_to_voice": True},
    )
    assert correction.status_code == 200
    assert correction.json()[0]["speaker"] == "customer"
    assert correction.json()[0]["speaker_name"] == "Maya"
    assert correction.json()[0]["speaker_source"] == "corrected"


def test_audio_socket_can_stamp_a_manual_speaker(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    monkeypatch.setattr(audio, "get_stt_provider", lambda: EchoSpeechProvider())

    with client.websocket_connect(f"/api/v1/sessions/{session_id}/audio") as socket:
        socket.receive_json()
        socket.send_json(
            {
                "type": "configure",
                "speaker_mode": "manual",
                "speaker": "facilitator",
                "speaker_id": "manual:ryan",
                "speaker_name": "Ryan",
            }
        )
        assert socket.receive_json()["speaker_mode"] == "manual"
        socket.send_bytes(b"\x00\x00" * 160)
        partial = socket.receive_json()
        assert partial["speaker"] == "facilitator"
        assert partial["speaker_name"] == "Ryan"
        assert partial["speaker_source"] == "manual"
        socket.send_json({"type": "stop"})
        assert socket.receive_json()["type"] == "transcript.final"
        assert socket.receive_json()["type"] == "transcription.stopped"


def test_audio_socket_rejects_unknown_session(client) -> None:  # type: ignore[no-untyped-def]
    with client.websocket_connect("/api/v1/sessions/missing/audio") as socket:
        error = socket.receive_json()
        assert error["type"] == "transcription.error"
        assert error["code"] == "session_not_found"


def test_transcription_status_is_provider_neutral(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/api/v1/transcription/status")
    assert response.status_code == 200
    assert response.json() == {
        "available": True,
        "supports_partials": True,
        "supports_speaker_detection": True,
        "audio": {"encoding": "pcm_s16le", "sample_rate": 16000, "channels": 1},
        "max_frame_seconds": 5,
    }
    assert "provider" not in response.text.lower()


def test_managed_capability_only_exposes_browser_relevant_features() -> None:
    capability = audio._transcription_capability(
        Settings(stt_provider="openai", openai_api_key="test-key")
    )
    assert capability.available is True
    assert capability.supports_partials is True
    assert capability.supports_speaker_detection is False
    assert "openai" not in capability.model_dump_json().lower()
