"""Wispr Flow WebSocket transcription adapter."""

from __future__ import annotations

import asyncio
import base64
import json
import math
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from websockets.asyncio.client import connect

from .base import SpeechToTextProvider, TranscriptEvent


@dataclass
class _WisprSession:
    socket: Any
    queue: asyncio.Queue[TranscriptEvent | object]
    receiver: asyncio.Task[None] | None = None
    packet_count: int = 0
    final_received: asyncio.Event | None = None
    error: Exception | None = None
    segment_id: str = ""


class WisprFlowProvider(SpeechToTextProvider):
    """Server-side adapter for the Wispr Flow streaming API."""

    _END = object()

    def __init__(
        self,
        *,
        api_key: str,
        access_token: str,
        websocket_url: str = "wss://platform-api.wisprflow.ai/api/v1/dash/ws",
        language: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("WISPR_FLOW_API_KEY is required when STT_PROVIDER=wispr")
        if not access_token:
            raise ValueError("WISPR_FLOW_ACCESS_TOKEN is required when STT_PROVIDER=wispr")
        self._api_key = api_key
        self._access_token = access_token
        self._websocket_url = websocket_url
        self._language = language
        self._sessions: dict[str, _WisprSession] = {}

    async def start(self, session_id: str) -> None:
        if session_id in self._sessions:
            raise RuntimeError(f"Transcription session {session_id} is already active")
        credential = f"Bearer {self._api_key}"
        socket = await connect(
            f"{self._websocket_url}?api_key={quote(credential)}",
            max_size=4 * 1024 * 1024,
        )
        state = _WisprSession(
            socket=socket,
            queue=asyncio.Queue(),
            final_received=asyncio.Event(),
            segment_id=str(uuid4()),
        )
        self._sessions[session_id] = state
        message: dict[str, object] = {
            "type": "auth",
            "access_token": self._access_token,
            "context": {
                "app": {"name": "SpecLive", "type": "ai"},
                "dictionary_context": [],
                "textbox_contents": {
                    "before_text": "",
                    "selected_text": "",
                    "after_text": "",
                },
            },
        }
        if self._language:
            message["language"] = [self._language]
        await socket.send(json.dumps(message))
        state.receiver = asyncio.create_task(self._receive(state))

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        state = self._require_session(session_id)
        if not pcm:
            return
        duration = len(pcm) / (16000 * 2)
        await state.socket.send(
            json.dumps(
                {
                    "type": "append",
                    "position": state.packet_count,
                    "audio_packets": {
                        "packets": [base64.b64encode(pcm).decode("ascii")],
                        "volumes": [self._rms(pcm)],
                        "packet_duration": duration,
                        "audio_encoding": "wav",
                        "byte_encoding": "base64",
                    },
                }
            )
        )
        state.packet_count += 1

    async def events(self, session_id: str) -> AsyncIterator[TranscriptEvent]:
        state = self._require_session(session_id)
        while True:
            item = await state.queue.get()
            if item is self._END:
                if state.error is not None:
                    raise state.error
                break
            assert isinstance(item, TranscriptEvent)
            yield item

    async def stop(self, session_id: str) -> None:
        state = self._sessions.pop(session_id, None)
        if state is None:
            return
        try:
            if state.packet_count:
                await state.socket.send(
                    json.dumps({"type": "commit", "total_packets": state.packet_count})
                )
                assert state.final_received is not None
                await asyncio.wait_for(state.final_received.wait(), timeout=30)
        finally:
            await state.socket.close()
            if state.receiver is not None:
                await asyncio.gather(state.receiver, return_exceptions=True)

    async def _receive(self, state: _WisprSession) -> None:
        try:
            async for raw in state.socket:
                message = json.loads(raw)
                status = message.get("status")
                if status == "text":
                    body = message.get("body", {})
                    text = str(body.get("text", ""))
                    is_final = bool(message.get("final", False))
                    if text:
                        state.queue.put_nowait(
                            TranscriptEvent(
                                segment_id=state.segment_id,
                                text=text,
                                is_final=is_final,
                            )
                        )
                    if is_final and state.final_received is not None:
                        state.final_received.set()
                elif status == "error" or message.get("error"):
                    detail = message.get("error") or message.get("message") or "unknown"
                    raise RuntimeError(f"Wispr Flow transcription error: {detail}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - transferred to the consumer task
            state.error = exc
            if state.final_received is not None:
                state.final_received.set()
        finally:
            state.queue.put_nowait(self._END)

    def _require_session(self, session_id: str) -> _WisprSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise RuntimeError(f"Transcription session {session_id} is not active") from exc

    @staticmethod
    def _rms(pcm: bytes) -> float:
        if len(pcm) < 2:
            return 0.0
        total = 0
        count = len(pcm) // 2
        for offset in range(0, count * 2, 2):
            value = int.from_bytes(pcm[offset : offset + 2], "little", signed=True) / 32768
            total += value * value
        return math.sqrt(total / count)
