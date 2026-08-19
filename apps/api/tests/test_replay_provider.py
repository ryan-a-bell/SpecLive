"""Tests for the scripted replay STT provider (deterministic diarization stand-in)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.providers.base import TranscriptEvent
from app.providers.replay import ReplaySpeechToTextProvider

_SCRIPT = {
    "title": "t",
    "turns": [
        {"speaker": "facilitator", "speaker_name": "Ryan", "text": "one"},
        {"speaker": "customer", "speaker_name": "Maya", "text": "two"},
        {"speaker": "facilitator", "speaker_name": "Ryan", "text": "three"},
        {"speaker": "participant", "speaker_name": "Dev", "text": "four"},
    ],
}

_SECONDS = 1.0
_BYTES_PER_TURN = int(_SECONDS * 16000 * 2)


def _write(tmp_path: Path, data: dict) -> str:
    path = tmp_path / "script.json"
    path.write_text(json.dumps(data))
    return str(path)


def _consume(provider: ReplaySpeechToTextProvider, session: str) -> asyncio.Task:
    """Start draining events concurrently, the way audio.py does (before stop())."""
    collected: list[TranscriptEvent] = []

    async def run() -> list[TranscriptEvent]:
        async for event in provider.events(session):
            collected.append(event)
        return collected

    return asyncio.ensure_future(run())


def test_load_assigns_stable_anonymous_voices_in_order(tmp_path: Path) -> None:
    provider = ReplaySpeechToTextProvider(script_path=_write(tmp_path, _SCRIPT))
    voices = [t.voice_id for t in provider._turns]
    # Two Ryan turns share one anonymous id; three distinct speakers -> spk-1..3.
    assert voices == ["spk-1", "spk-2", "spk-1", "spk-3"]
    assert all(v.startswith("spk-") for v in voices)


async def test_stream_emits_one_detected_final_per_turn_in_order(tmp_path: Path) -> None:
    provider = ReplaySpeechToTextProvider(
        script_path=_write(tmp_path, _SCRIPT), seconds_per_turn=_SECONDS
    )
    await provider.start("s")
    consumer = _consume(provider, "s")
    await asyncio.sleep(0)  # let the consumer capture the session before stop()
    # Enough audio for every turn at once.
    await provider.push_audio("s", b"\x00" * (_BYTES_PER_TURN * len(_SCRIPT["turns"])))
    await provider.stop("s")

    events = await consumer
    assert [e.text for e in events] == ["one", "two", "three", "four"]
    assert [e.speaker for e in events] == ["spk-1", "spk-2", "spk-1", "spk-3"]
    assert all(e.is_final for e in events)
    assert all(0.0 < e.speaker_confidence <= 1.0 for e in events)
    # Monotonic, non-overlapping synthetic timestamps.
    assert [e.start_time for e in events] == [0.0, 1.0, 2.0, 3.0]


async def test_pacing_gates_on_received_audio_and_stop_flushes(tmp_path: Path) -> None:
    provider = ReplaySpeechToTextProvider(
        script_path=_write(tmp_path, _SCRIPT), seconds_per_turn=_SECONDS
    )
    await provider.start("s")
    consumer = _consume(provider, "s")
    await asyncio.sleep(0)  # let the consumer capture the session before stop()

    # Only two turns' worth of audio so far -> only two turns are due.
    await provider.push_audio("s", b"\x00" * (_BYTES_PER_TURN * 2))
    assert provider._sessions["s"].emitted == 2

    # stop() must flush the remaining turns before ending.
    await provider.stop("s")
    events = await consumer
    assert len(events) == len(_SCRIPT["turns"])


def test_empty_script_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ReplaySpeechToTextProvider(script_path=_write(tmp_path, {"turns": []}))
