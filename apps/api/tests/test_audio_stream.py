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
                segment_id="echo-segment",
                text="live words",
                is_final=False,
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
                segment_id="echo-segment",
                text="live words finalized",
                is_final=True,
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

        socket.send_bytes(b"\x00\x00" * 160)
        partial = socket.receive_json()
        assert partial["type"] == "transcript.partial"
        assert partial["segment_id"] == "echo-segment"
        assert partial["text"] == "live words"

        socket.send_json({"type": "stop"})
        final = socket.receive_json()
        assert final["type"] == "transcript.final"
        assert final["segment_id"] == "echo-segment"
        assert final["text"] == "live words finalized"
        assert socket.receive_json()["type"] == "transcription.stopped"

    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
    assert transcript[-1]["id"] == "echo-segment"
    assert transcript[-1]["text"] == "live words finalized"
    assert transcript[-1]["is_final"] is True


def test_audio_socket_rejects_unknown_session(client) -> None:  # type: ignore[no-untyped-def]
    with client.websocket_connect("/api/v1/sessions/missing/audio") as socket:
        error = socket.receive_json()
        assert error["type"] == "transcription.error"
        assert error["code"] == "session_not_found"


def test_transcription_status_is_provider_neutral(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/api/v1/transcription/status")
    assert response.status_code == 200
    assert response.json() == {
        "available": False,
        "supports_partials": False,
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
    assert "openai" not in capability.model_dump_json().lower()
