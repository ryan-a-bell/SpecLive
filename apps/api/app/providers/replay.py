"""Scripted replay speech-to-text — a deterministic diarization stand-in.

This is a **test/demo provider**, not a recognizer. Seeded with a conversation
fixture (the same JSON the playback harness streams), it replays each turn's
text as an *anonymous detected voice* — ``spk-1``, ``spk-2``, … assigned in the
order speakers first appear — paced by how much audio has arrived. It never
looks at the audio content.

That is exactly enough to exercise the ``auto`` speaker path end to end: the
audio socket maps each stable ``spk-N`` to a ``Voice N`` grouping, persists it
as a ``detected`` segment with a confidence, and the correction workflow can
then relabel a whole voice at once — all without a real diarization engine.
Swap in pyannote/whisperx later behind the same ``SpeechToTextProvider`` port.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from .base import SpeechToTextProvider, TranscriptEvent

_BYTES_PER_SECOND = 16000 * 2  # 16 kHz mono s16le


@dataclass
class _ScriptTurn:
    text: str
    voice_id: str
    confidence: float


@dataclass
class _ReplaySession:
    events: asyncio.Queue[TranscriptEvent | object]
    bytes_seen: int = 0
    emitted: int = 0
    clock: float = 0.0
    finished: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ReplaySpeechToTextProvider(SpeechToTextProvider):
    """Replays a scripted conversation as anonymous detected voices."""

    _END = object()

    def __init__(self, *, script_path: str, seconds_per_turn: float = 2.5) -> None:
        self._bytes_per_turn = max(1, int(seconds_per_turn * _BYTES_PER_SECOND))
        self._seconds_per_turn = seconds_per_turn
        self._turns = self._load(script_path)
        self._sessions: dict[str, _ReplaySession] = {}

    @staticmethod
    def _load(script_path: str) -> list[_ScriptTurn]:
        data = json.loads(Path(script_path).read_text())
        raw_turns = data.get("turns", [])
        if not raw_turns:
            raise ValueError(f"replay script {script_path} has no turns")
        # Anonymous, stable voice ids in first-appearance order — a diarizer
        # knows clusters, not names, so the human labels them afterward.
        voice_ids: dict[str, str] = {}
        confidences: dict[str, float] = {}
        turns: list[_ScriptTurn] = []
        for raw in raw_turns:
            name = str(raw.get("speaker_name") or raw.get("speaker") or "unknown")
            text = str(raw.get("text", "")).strip()
            if not text:
                continue
            if name not in voice_ids:
                voice_ids[name] = f"spk-{len(voice_ids) + 1}"
                # Deterministic, plausible per-voice confidence.
                confidences[name] = round(0.83 + (len(voice_ids) % 4) * 0.03, 2)
            turns.append(
                _ScriptTurn(text=text, voice_id=voice_ids[name], confidence=confidences[name])
            )
        return turns

    async def start(self, session_id: str) -> None:
        if session_id in self._sessions:
            raise RuntimeError(f"Transcription session {session_id} is already active")
        self._sessions[session_id] = _ReplaySession(events=asyncio.Queue())

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        state = self._require(session_id)
        if not pcm:
            return
        async with state._lock:
            state.bytes_seen += len(pcm)
            due = min(len(self._turns), state.bytes_seen // self._bytes_per_turn)
            self._emit_through(state, due)

    async def events(self, session_id: str) -> AsyncIterator[TranscriptEvent]:
        state = self._require(session_id)
        while True:
            item = await state.events.get()
            if item is self._END:
                break
            assert isinstance(item, TranscriptEvent)
            yield item

    async def stop(self, session_id: str) -> None:
        state = self._sessions.pop(session_id, None)
        if state is None:
            return
        async with state._lock:
            self._emit_through(state, len(self._turns))  # flush any remaining turns
            if not state.finished:
                state.finished = True
                state.events.put_nowait(self._END)

    def _emit_through(self, state: _ReplaySession, target: int) -> None:
        while state.emitted < target:
            turn = self._turns[state.emitted]
            start = state.clock
            state.clock += self._seconds_per_turn
            state.events.put_nowait(
                TranscriptEvent(
                    segment_id=str(uuid4()),
                    text=turn.text,
                    is_final=True,
                    speaker=turn.voice_id,
                    speaker_confidence=turn.confidence,
                    start_time=round(start, 2),
                    end_time=round(state.clock, 2),
                )
            )
            state.emitted += 1

    def _require(self, session_id: str) -> _ReplaySession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise RuntimeError(f"Transcription session {session_id} is not active") from exc
