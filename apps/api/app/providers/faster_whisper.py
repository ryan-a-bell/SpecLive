"""Local chunked transcription using faster-whisper."""

from __future__ import annotations

import asyncio
import os
import tempfile
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .base import SpeechToTextProvider, TranscriptEvent


@dataclass
class _LocalSession:
    audio: asyncio.Queue[bytes | None]
    events: asyncio.Queue[TranscriptEvent | object]
    worker: asyncio.Task[None] | None = None
    error: Exception | None = None


class FasterWhisperProvider(SpeechToTextProvider):
    """Local CPU/GPU provider with fixed-duration pseudo-streaming chunks."""

    _END = object()

    def __init__(
        self,
        *,
        model_name: str = "small.en",
        device: str = "auto",
        compute_type: str = "default",
        chunk_seconds: float = 3.0,
        language: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._chunk_bytes = max(1, int(chunk_seconds * 16000 * 2))
        self._language = language
        self._model: Any = None
        self._model_lock = asyncio.Lock()
        self._sessions: dict[str, _LocalSession] = {}

    async def start(self, session_id: str) -> None:
        if session_id in self._sessions:
            raise RuntimeError(f"Transcription session {session_id} is already active")
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "Local transcription requires `pip install -e '.[local]'`"
                ) from exc
            self._model = await asyncio.to_thread(
                WhisperModel,
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
        audio: asyncio.Queue[bytes | None] = asyncio.Queue()
        events: asyncio.Queue[TranscriptEvent | object] = asyncio.Queue()
        state = _LocalSession(audio=audio, events=events)
        state.worker = asyncio.create_task(self._run_worker(state))
        self._sessions[session_id] = state

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        if pcm:
            await self._require_session(session_id).audio.put(pcm)

    async def events(self, session_id: str) -> AsyncIterator[TranscriptEvent]:
        state = self._require_session(session_id)
        while True:
            item = await state.events.get()
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
        await state.audio.put(None)
        assert state.worker is not None
        await state.worker

    async def _run_worker(self, state: _LocalSession) -> None:
        buffer = bytearray()
        elapsed = 0.0
        try:
            while True:
                chunk = await state.audio.get()
                if chunk is None:
                    if buffer:
                        await self._transcribe_chunk(state, bytes(buffer), elapsed)
                    break
                buffer.extend(chunk)
                while len(buffer) >= self._chunk_bytes:
                    pcm = bytes(buffer[: self._chunk_bytes])
                    del buffer[: self._chunk_bytes]
                    await self._transcribe_chunk(state, pcm, elapsed)
                    elapsed += len(pcm) / (16000 * 2)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - transferred to the consumer task
            state.error = exc
        finally:
            state.events.put_nowait(self._END)

    async def _transcribe_chunk(
        self, state: _LocalSession, pcm: bytes, start_time: float
    ) -> None:
        segment_id = str(uuid4())
        duration = len(pcm) / (16000 * 2)
        async with self._model_lock:
            text = await asyncio.to_thread(self._transcribe_sync, pcm)
        if text:
            state.events.put_nowait(
                TranscriptEvent(
                    segment_id=segment_id,
                    text=text,
                    is_final=True,
                    start_time=start_time,
                    end_time=start_time + duration,
                )
            )

    def _transcribe_sync(self, pcm: bytes) -> str:
        descriptor, path = tempfile.mkstemp(suffix=".wav")
        os.close(descriptor)
        try:
            with wave.open(path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(pcm)
            segments, _ = self._model.transcribe(
                path,
                language=self._language,
                vad_filter=True,
                beam_size=5,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            os.unlink(path)

    def _require_session(self, session_id: str) -> _LocalSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise RuntimeError(f"Transcription session {session_id} is not active") from exc
