"""OpenAI Realtime transcription adapter.

The public SpecLive stream is 16 kHz PCM16. This adapter resamples it to the
24 kHz PCM format required by the OpenAI Realtime transcription session.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import sys
from array import array
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from websockets.asyncio.client import connect

from .base import SpeechToTextProvider, TranscriptEvent


class _PcmResampler:
    """Small streaming linear resampler for mono PCM16."""

    def __init__(self, input_rate: int, output_rate: int) -> None:
        self._step = input_rate / output_rate
        self._samples: list[int] = []
        self._position = 0.0

    def convert(self, pcm: bytes) -> bytes:
        values = array("h")
        values.frombytes(pcm)
        if sys.byteorder != "little":
            values.byteswap()
        self._samples.extend(values)
        output = array("h")
        while self._position < len(self._samples) - 1:
            left = math.floor(self._position)
            fraction = self._position - left
            value = self._samples[left] + fraction * (
                self._samples[left + 1] - self._samples[left]
            )
            output.append(round(max(-32768, min(32767, value))))
            self._position += self._step
        consumed = math.floor(self._position)
        if consumed:
            self._samples = self._samples[consumed:]
            self._position -= consumed
        if sys.byteorder != "little":
            output.byteswap()
        return output.tobytes()


@dataclass
class _OpenAISession:
    socket: Any
    queue: asyncio.Queue[TranscriptEvent | object]
    receiver: asyncio.Task[None] | None = None
    resampler: _PcmResampler = field(default_factory=lambda: _PcmResampler(16000, 24000))
    partials: dict[str, str] = field(default_factory=dict)
    segment_ids: dict[str, str] = field(default_factory=dict)
    final_received: asyncio.Event = field(default_factory=asyncio.Event)
    pushed_audio: bool = False
    error: Exception | None = None


class OpenAIRealtimeProvider(SpeechToTextProvider):
    """Server-side adapter for OpenAI Realtime speech-to-text."""

    _END = object()

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-live-transcribe",
        websocket_url: str = "wss://api.openai.com/v1/realtime",
        language: str | None = None,
        prompt: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when STT_PROVIDER=openai")
        self._api_key = api_key
        self._model = model
        self._websocket_url = websocket_url
        self._language = language
        self._prompt = prompt
        self._sessions: dict[str, _OpenAISession] = {}

    async def start(self, session_id: str) -> None:
        if session_id in self._sessions:
            raise RuntimeError(f"Transcription session {session_id} is already active")
        url = f"{self._websocket_url}?model={quote(self._model)}"
        socket = await connect(
            url,
            additional_headers={"Authorization": f"Bearer {self._api_key}"},
            max_size=4 * 1024 * 1024,
        )
        state = _OpenAISession(socket=socket, queue=asyncio.Queue())
        self._sessions[session_id] = state
        transcription: dict[str, object] = {"model": self._model, "delay": "low"}
        if self._language:
            transcription["languages"] = [self._language]
        if self._prompt:
            transcription["prompt"] = self._prompt
        await socket.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "type": "transcription",
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcm", "rate": 24000},
                                "transcription": transcription,
                                "turn_detection": None,
                            }
                        },
                    },
                }
            )
        )
        state.receiver = asyncio.create_task(self._receive(state))

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        state = self._require_session(session_id)
        if not pcm:
            return
        converted = state.resampler.convert(pcm)
        if not converted:
            return
        state.pushed_audio = True
        await state.socket.send(
            json.dumps(
                {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(converted).decode("ascii"),
                }
            )
        )

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
            if state.pushed_audio:
                state.final_received.clear()
                await state.socket.send(json.dumps({"type": "input_audio_buffer.commit"}))
                await asyncio.wait_for(state.final_received.wait(), timeout=30)
        finally:
            await state.socket.close()
            if state.receiver is not None:
                await asyncio.gather(state.receiver, return_exceptions=True)

    async def _receive(self, state: _OpenAISession) -> None:
        try:
            async for raw in state.socket:
                message = json.loads(raw)
                event_type = message.get("type")
                if event_type == "conversation.item.input_audio_transcription.delta":
                    item_id = str(message.get("item_id", "current"))
                    segment_id = state.segment_ids.setdefault(item_id, str(uuid4()))
                    text = state.partials.get(item_id, "") + str(message.get("delta", ""))
                    state.partials[item_id] = text
                    if text:
                        state.queue.put_nowait(
                            TranscriptEvent(segment_id=segment_id, text=text, is_final=False)
                        )
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    item_id = str(message.get("item_id", "current"))
                    segment_id = state.segment_ids.pop(item_id, None) or str(uuid4())
                    text = str(message.get("transcript", ""))
                    state.partials.pop(item_id, None)
                    if text:
                        state.queue.put_nowait(
                            TranscriptEvent(segment_id=segment_id, text=text, is_final=True)
                        )
                    state.final_received.set()
                elif event_type == "error":
                    error = message.get("error", {})
                    detail = error.get("message", "unknown")
                    raise RuntimeError(f"OpenAI transcription error: {detail}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - transferred to the consumer task
            state.error = exc
            state.final_received.set()
        finally:
            state.queue.put_nowait(self._END)

    def _require_session(self, session_id: str) -> _OpenAISession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise RuntimeError(f"Transcription session {session_id} is not active") from exc
