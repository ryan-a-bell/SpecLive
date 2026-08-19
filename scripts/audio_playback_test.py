#!/usr/bin/env python3
"""Synthesize a discussion with Piper and stream it into the SpecLive audio socket.

There is no file-upload endpoint: the API ingests audio only over the WebSocket
at ``/api/v1/sessions/{id}/audio`` as raw **mono 16-bit little-endian PCM at
16 kHz**, in frames of at most five seconds. This harness closes that gap for
manual/CI testing without a microphone:

    discussion JSON  --Piper-->  wav  --resample-->  PCM16/16k/mono
        --> WebSocket frames --> transcript

It exercises the exact contract the browser uses: ``transcription.ready`` ->
``configure`` -> binary frames -> ``stop``, while a reader task prints every
``transcript.partial`` / ``transcript.final`` the server returns.

Speaker modes
-------------
* ``--speaker-mode manual`` (default): the harness stamps each turn's true
  speaker before streaming its audio. Good for validating the plumbing.
* ``--speaker-mode auto``: the harness reveals nothing; the server detects and
  groups voices on its own. Pair it with ``STT_PROVIDER=replay`` (a scripted
  diarization stand-in) to watch anonymous ``Voice N`` groups form, then add
  ``--apply-corrections`` to relabel each voice to its true speaker.

Requirements
------------
* ``pip install websockets``  (only extra Python dependency; REST uses stdlib)
* The ``piper`` binary on PATH (https://github.com/rhasspy/piper) and at least
  one voice model. Point at models with ``--voices-dir`` or per-speaker entries
  in the script's ``voices`` map. Override the synthesizer entirely with
  ``--tts-cmd`` (see below) to use ``say``, ``espeak-ng``, or a cloud engine.

The WAV -> PCM conversion is pure Python (``wave`` + ``audioop``); no ffmpeg.

Usage
-----
    python scripts/audio_playback_test.py \
        --script scripts/sample_discussion.json \
        --api-base http://localhost:8000 \
        --voices-dir ~/piper-voices

    # Bring your own synthesizer (must emit a WAV at {out}; {text} is the line):
    python scripts/audio_playback_test.py --script scripts/sample_discussion.json \
        --tts-cmd 'espeak-ng -w {out} {text}'

    # Watch speaker detection + grouping + correction play out (auto mode).
    # Start the API with:
    #   STT_PROVIDER=replay \
    #   REPLAY_SCRIPT=scripts/conversations/hpc_infrastructure.json uvicorn ...
    python scripts/audio_playback_test.py \
        --script scripts/conversations/hpc_infrastructure.json \
        --speaker-mode auto --apply-corrections --realtime
"""

from __future__ import annotations

import argparse
import asyncio
import audioop
import json
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path

try:
    import websockets
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("This harness needs the 'websockets' package: pip install websockets")

TARGET_RATE = 16000
TARGET_WIDTH = 2  # bytes per sample (s16le)
TARGET_CHANNELS = 1
# Server caps a frame at five seconds; stay under it so pacing has headroom.
FRAME_SECONDS = 4.0
FRAME_BYTES = int(FRAME_SECONDS * TARGET_RATE * TARGET_WIDTH)

VALID_SPEAKERS = {"facilitator", "customer", "participant", "system", "unknown"}


@dataclass
class Turn:
    speaker: str
    speaker_name: str
    text: str
    voice: str | None = None


# --------------------------------------------------------------------------- #
# Script loading
# --------------------------------------------------------------------------- #
def load_script(path: Path) -> tuple[dict, list[Turn], dict[str, str]]:
    data = json.loads(path.read_text())
    voices = data.get("voices", {})
    turns: list[Turn] = []
    for i, raw in enumerate(data.get("turns", [])):
        speaker = str(raw.get("speaker", "unknown")).lower()
        if speaker not in VALID_SPEAKERS:
            sys.exit(f"turn {i}: speaker '{speaker}' is not one of {sorted(VALID_SPEAKERS)}")
        name = str(raw.get("speaker_name") or speaker.title()).strip()
        text = str(raw.get("text", "")).strip()
        if not text:
            sys.exit(f"turn {i}: empty text")
        voice = raw.get("voice") or voices.get(speaker) or voices.get(name)
        turns.append(Turn(speaker=speaker, speaker_name=name, text=text, voice=voice))
    if not turns:
        sys.exit("script has no turns")
    meta = {
        "title": data.get("title", "Synthetic discovery session"),
        "customer": data.get("customer", "Synthetic Customer"),
        "facilitator": data.get("facilitator", "Facilitator"),
    }
    return meta, turns, voices


# --------------------------------------------------------------------------- #
# Text-to-speech + resampling
# --------------------------------------------------------------------------- #
def synthesize(turn: Turn, out_wav: Path, args: argparse.Namespace) -> None:
    """Render one line of dialogue to a WAV file at ``out_wav``."""
    if args.tts_cmd:
        # Both fields are shlex-quoted, so each expands to a single safe shell
        # token — do NOT wrap {text} in your own quotes in the template.
        cmd = args.tts_cmd.format(out=shlex.quote(str(out_wav)), text=shlex.quote(turn.text))
        subprocess.run(cmd, shell=True, check=True)
        return

    model_args: list[str] = []
    if turn.voice:
        model = turn.voice
        if not model.endswith(".onnx"):
            model = f"{model}.onnx"
        if args.voices_dir and not Path(model).is_absolute():
            model = str(Path(args.voices_dir).expanduser() / model)
        model_args = ["--model", model]
    piper_cmd = [args.piper, *model_args, "--output_file", str(out_wav)]
    proc = subprocess.run(piper_cmd, input=turn.text.encode(), capture_output=True)
    if proc.returncode != 0:
        sys.exit(
            f"piper failed for {turn.speaker_name}: "
            f"{proc.stderr.decode(errors='replace').strip()}\n"
            f"command: {' '.join(shlex.quote(c) for c in piper_cmd)}"
        )


def wav_to_pcm16_16k_mono(path: Path) -> bytes:
    """Read a WAV of any rate/width/channels and return mono s16le at 16 kHz."""
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if width != TARGET_WIDTH:
        frames = audioop.lin2lin(frames, width, TARGET_WIDTH)
        width = TARGET_WIDTH
    if channels == 2:
        frames = audioop.tomono(frames, width, 0.5, 0.5)
    elif channels != 1:
        sys.exit(f"unsupported channel count: {channels}")
    if rate != TARGET_RATE:
        frames, _ = audioop.ratecv(frames, width, 1, rate, TARGET_RATE, None)
    return frames


def render_turn(turn: Turn, args: argparse.Namespace) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "turn.wav"
        synthesize(turn, out, args)
        return wav_to_pcm16_16k_mono(out)


def frames_of(pcm: bytes) -> list[bytes]:
    if len(pcm) % 2:  # keep sample alignment the server requires
        pcm = pcm[:-1]
    return [pcm[i : i + FRAME_BYTES] for i in range(0, len(pcm), FRAME_BYTES)] or [b""]


# --------------------------------------------------------------------------- #
# REST: create (or reuse) a session
# --------------------------------------------------------------------------- #
def create_session(api_base: str, meta: dict) -> str:
    body = json.dumps(meta).encode()
    req = urllib.request.Request(
        f"{api_base}/api/v1/sessions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["id"]
    except urllib.error.URLError as exc:
        sys.exit(f"could not create session at {api_base}: {exc}")


def ws_url(api_base: str, session_id: str) -> str:
    scheme = "wss" if api_base.startswith("https") else "ws"
    host = api_base.split("://", 1)[-1].rstrip("/")
    return f"{scheme}://{host}/api/v1/sessions/{session_id}/audio"


# --------------------------------------------------------------------------- #
# WebSocket streaming
# --------------------------------------------------------------------------- #
async def reader(ws, stop: asyncio.Event) -> None:
    """Print transcript events until the socket says it stopped."""
    try:
        async for message in ws:
            evt = json.loads(message)
            kind = evt.get("type", "")
            if kind in {"transcript.partial", "transcript.final"}:
                tag = "FINAL" if evt.get("is_final") else "partial"
                who = evt.get("speaker_name") or evt.get("speaker") or "?"
                src = evt.get("speaker_source", "?")
                conf = evt.get("speaker_confidence")
                meta = f"{src}" + (f" {conf:.2f}" if isinstance(conf, (int, float)) else "")
                print(f"  [{tag:7}] {who:8} ({meta}): {evt.get('text', '').strip()}")
            elif kind == "transcription.error":
                print(f"  [error] {evt.get('code')}: {evt.get('message', '')}")
            elif kind == "transcription.stopped":
                print(f"  [stopped] committed={evt.get('committed')}")
                stop.set()
                return
    except websockets.ConnectionClosed:
        stop.set()


async def stream(
    session_id: str,
    api_base: str,
    turns: list[Turn],
    rendered: list[bytes],
    realtime: bool,
    speaker_mode: str,
) -> None:
    url = ws_url(api_base, session_id)
    async with websockets.connect(url, max_size=None) as ws:
        ready = json.loads(await ws.recv())
        if ready.get("type") != "transcription.ready":
            sys.exit(f"unexpected handshake: {ready}")
        print(f"connected: {ready.get('audio')} | speaker_mode={speaker_mode}")

        stop = asyncio.Event()
        reader_task = asyncio.create_task(reader(ws, stop))

        if speaker_mode == "auto":
            # Let the server's detection group voices on its own; the harness
            # does not reveal who is speaking. Audio for all turns streams back
            # to back — the STT provider attributes each utterance.
            await ws.send(json.dumps({"type": "configure", "speaker_mode": "auto"}))

        for turn, pcm in zip(turns, rendered, strict=True):
            if speaker_mode == "manual":
                voice_id = "synthetic:" + turn.speaker_name.lower().replace(" ", "_")
                await ws.send(
                    json.dumps(
                        {
                            "type": "configure",
                            "speaker_mode": "manual",
                            "speaker": turn.speaker,
                            "speaker_id": voice_id,
                            "speaker_name": turn.speaker_name,
                        }
                    )
                )
            print(f"> {turn.speaker_name} ({turn.speaker}): {turn.text[:70]}...")
            for frame in frames_of(pcm):
                if not frame:
                    continue
                await ws.send(frame)
                if realtime:
                    await asyncio.sleep(len(frame) / (TARGET_RATE * TARGET_WIDTH))

        await ws.send(json.dumps({"type": "stop"}))
        try:
            await asyncio.wait_for(stop.wait(), timeout=30)
        except TimeoutError:
            print("  [warn] timed out waiting for transcription.stopped")
        reader_task.cancel()


# --------------------------------------------------------------------------- #
# Correction workflow (auto mode): relabel detected voices to true speakers
# --------------------------------------------------------------------------- #
def _get_transcript(api_base: str, session_id: str) -> list[dict]:
    with urllib.request.urlopen(f"{api_base}/api/v1/sessions/{session_id}/transcript") as resp:
        return json.loads(resp.read())


def apply_corrections(api_base: str, session_id: str, turns: list[Turn]) -> None:
    """Map each detected voice to its ground-truth speaker and relabel it.

    Segments persist in turn order, so the i-th segment corresponds to the i-th
    scripted turn. We take the first segment of each detected ``speaker_id`` and
    PATCH it with ``apply_to_voice`` so the whole voice is relabeled at once —
    exactly the human-correction loop the auto path is built around.
    """
    segments = _get_transcript(api_base, session_id)
    if not segments:
        print("  [correct] no persisted segments to correct")
        return
    if len(segments) != len(turns):
        print(
            f"  [correct] warning: {len(segments)} segments vs {len(turns)} turns; "
            "pairing by position as far as they align"
        )

    print("\ndetected voices:")
    first_seg: dict[str, tuple[str, Turn]] = {}
    for seg, turn in zip(segments, turns, strict=False):
        voice = seg.get("speaker_id")
        if voice and voice not in first_seg:
            first_seg[voice] = (seg["id"], turn)
            print(f"  {voice} -> truth {turn.speaker_name} ({turn.speaker})")

    for voice, (seg_id, turn) in first_seg.items():
        body = json.dumps(
            {
                "speaker": turn.speaker,
                "speaker_name": turn.speaker_name,
                "apply_to_voice": True,
            }
        ).encode()
        req = urllib.request.Request(
            f"{api_base}/api/v1/sessions/{session_id}/transcript/{seg_id}/speaker",
            data=body,
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        with urllib.request.urlopen(req) as resp:
            updated = json.loads(resp.read())
        print(f"  corrected {voice} -> {turn.speaker_name}: {len(updated)} segment(s) relabeled")

    print("\ncorrected transcript:")
    for seg in _get_transcript(api_base, session_id):
        print(
            f"  [{seg.get('speaker_source'):9}] {seg.get('speaker_name'):8}: "
            f"{seg.get('text', '').strip()[:70]}"
        )


# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--script",
        type=Path,
        required=True,
        help="discussion JSON (see scripts/sample_discussion.json)",
    )
    parser.add_argument(
        "--api-base",
        default="http://localhost:8000",
        help="SpecLive API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--session-id", default=None, help="reuse an existing session instead of creating one"
    )
    parser.add_argument("--piper", default="piper", help="piper binary (default: %(default)s)")
    parser.add_argument(
        "--voices-dir", default=None, help="directory holding piper .onnx voice models"
    )
    parser.add_argument(
        "--tts-cmd",
        default=None,
        help="override synthesizer; a shell template with {out} and {text}",
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="pace frames at wall-clock speed to mimic live playback",
    )
    parser.add_argument(
        "--speaker-mode",
        choices=("manual", "auto"),
        default="manual",
        help="manual: stamp the true speaker per turn; auto: let the server detect "
        "and group voices (use with STT_PROVIDER=replay). Default: %(default)s",
    )
    parser.add_argument(
        "--apply-corrections",
        action="store_true",
        help="auto mode only: after streaming, relabel each detected voice to its "
        "true speaker via the correction endpoint and print the regrouped transcript",
    )
    args = parser.parse_args()

    meta, turns, _ = load_script(args.script)

    print(
        f"rendering {len(turns)} turns with {'custom tts-cmd' if args.tts_cmd else args.piper} ..."
    )
    rendered = [render_turn(turn, args) for turn in turns]
    total_s = sum(len(p) for p in rendered) / (TARGET_RATE * TARGET_WIDTH)
    print(f"synthesized {total_s:.1f}s of audio")

    session_id = args.session_id or create_session(args.api_base, meta)
    print(f"session: {session_id}")

    asyncio.run(
        stream(session_id, args.api_base, turns, rendered, args.realtime, args.speaker_mode)
    )

    if args.apply_corrections:
        if args.speaker_mode != "auto":
            print("  [correct] --apply-corrections has no effect outside auto mode; skipping")
        else:
            apply_corrections(args.api_base, session_id, turns)

    print(f"\ndone. transcript: {args.api_base}/api/v1/sessions/{session_id}/transcript")


if __name__ == "__main__":
    main()
