"""Mocked vendor-protocol tests for hosted STT adapters."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from app.providers import openai_realtime, wispr_flow
from app.providers.openai_realtime import OpenAIRealtimeProvider
from app.providers.wispr_flow import WisprFlowProvider


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.incoming: asyncio.Queue[str | None] = asyncio.Queue()
        self.closed = False

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.incoming.put_nowait(None)

    def __aiter__(self) -> FakeSocket:
        return self

    async def __anext__(self) -> str:
        message = await self.incoming.get()
        if message is None:
            raise StopAsyncIteration
        return message

    def receive(self, message: dict[str, Any]) -> None:
        self.incoming.put_nowait(json.dumps(message))


async def _wait_for_sent(socket: FakeSocket, event_type: str) -> None:
    for _ in range(20):
        if any(message.get("type") == event_type for message in socket.sent):
            return
        await asyncio.sleep(0)
    raise AssertionError(f"Timed out waiting for {event_type}")


async def test_openai_protocol_is_normalized(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    socket = FakeSocket()

    async def fake_connect(*args, **kwargs):  # type: ignore[no-untyped-def]
        return socket

    monkeypatch.setattr(openai_realtime, "connect", fake_connect)
    provider = OpenAIRealtimeProvider(api_key="secret", model="test-transcribe")
    await provider.start("session")
    assert socket.sent[0]["session"]["audio"]["input"]["format"]["rate"] == 24000

    await provider.push_audio("session", b"\x00\x00" * 320)
    append = socket.sent[-1]
    assert append["type"] == "input_audio_buffer.append"
    assert len(base64.b64decode(append["audio"])) > 640

    events = provider.events("session")
    socket.receive(
        {
            "type": "conversation.item.input_audio_transcription.delta",
            "item_id": "vendor-item",
            "delta": "hello",
        }
    )
    partial = await anext(events)
    assert partial.text == "hello"
    assert partial.is_final is False
    assert partial.segment_id != "vendor-item"

    stop_task = asyncio.create_task(provider.stop("session"))
    await _wait_for_sent(socket, "input_audio_buffer.commit")
    socket.receive(
        {
            "type": "conversation.item.input_audio_transcription.completed",
            "item_id": "vendor-item",
            "transcript": "hello world",
        }
    )
    final = await anext(events)
    assert final.segment_id == partial.segment_id
    assert final.text == "hello world"
    assert final.is_final is True
    await stop_task


async def test_wispr_protocol_is_normalized(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    socket = FakeSocket()

    async def fake_connect(*args, **kwargs):  # type: ignore[no-untyped-def]
        return socket

    monkeypatch.setattr(wispr_flow, "connect", fake_connect)
    provider = WisprFlowProvider(api_key="org-secret", access_token="session-secret")
    await provider.start("session")
    assert socket.sent[0]["type"] == "auth"
    assert socket.sent[0]["access_token"] == "session-secret"

    await provider.push_audio("session", b"\x00\x00" * 1600)
    append = socket.sent[-1]
    assert append["type"] == "append"
    assert append["audio_packets"]["packet_duration"] == 0.1

    events = provider.events("session")
    socket.receive({"status": "text", "final": False, "body": {"text": "partial"}})
    partial = await anext(events)
    assert partial.text == "partial"
    assert partial.is_final is False

    stop_task = asyncio.create_task(provider.stop("session"))
    await _wait_for_sent(socket, "commit")
    socket.receive({"status": "text", "final": True, "body": {"text": "complete"}})
    final = await anext(events)
    assert final.segment_id == partial.segment_id
    assert final.text == "complete"
    assert final.is_final is True
    await stop_task
