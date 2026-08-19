# Dev scripts

## `audio_playback_test.py` — synthetic discussion playback

Streams a **synthetic multi-speaker discussion** into the live transcription
socket so you can exercise the whole audio → transcript → persistence path
without a microphone.

There is **no file-upload endpoint** — the API ingests audio only over the
WebSocket at `/api/v1/sessions/{id}/audio` as raw **mono 16-bit little-endian
PCM at 16 kHz**, in frames of at most five seconds. So you can't "upload an
mp3": the harness synthesizes speech, resamples to that exact PCM format, and
streams it frame by frame, driving the same `ready → configure → frames → stop`
handshake the browser uses.

```
discussion JSON ──TTS──▶ wav ──resample──▶ PCM16/16k/mono ──▶ WS frames ──▶ transcript
```

### Requirements

- `pip install websockets` (the only extra Python dependency; the REST call and
  the WAV → PCM conversion use the standard library — no `ffmpeg`).
- A running API (`make api` or `make up`).
- A synthesizer. Default is [**Piper**](https://github.com/rhasspy/piper)
  (offline). Install the binary and one or more voice models, then point at them
  with `--voices-dir` and the `voices` map in the script. Or override the
  synthesizer entirely with `--tts-cmd` to use `say`, `espeak-ng`, or a cloud
  engine.

### Usage

```bash
# Piper (per-speaker voices from the script's "voices" map)
python scripts/audio_playback_test.py \
    --script scripts/sample_discussion.json \
    --api-base http://localhost:8000 \
    --voices-dir ~/piper-voices \
    --realtime            # optional: pace frames at wall-clock speed

# Bring your own synthesizer ({out} = target wav path, {text} = the line;
# both are shell-quoted for you — don't add your own quotes around {text})
python scripts/audio_playback_test.py \
    --script scripts/sample_discussion.json \
    --tts-cmd 'espeak-ng -w {out} {text}'
```

The harness creates a session (or reuse one with `--session-id`), prints every
`transcript.partial` / `transcript.final` the server returns, and finishes with a
link to the persisted transcript.

### Bundled conversations

Ready-to-stream synthetic discovery calls live in
[`conversations/`](conversations/):

| File | Speakers | Topic |
|------|----------|-------|
| [`iot_warehouse_ml_pipeline.json`](conversations/iot_warehouse_ml_pipeline.json) | 2 (Ryan ↔ Priya) | Setting up an ML pipeline for an IoT warehouse — predictive maintenance, edge inference, drift/retraining, data residency |
| [`hpc_infrastructure.json`](conversations/hpc_infrastructure.json) | 3 (Ryan / Marcus / Elena) | HPC infrastructure — scheduling, parallel storage, power & cooling, interconnect, multi-tenant isolation |

Each is written as a real facilitator-led discovery dialogue, so it also gives
the derivation layer objectives, requirements, constraints, and risks to chew on.

### Watching speaker detection play out (auto mode)

The `mock` provider only emits canned text and `faster-whisper` emits no speaker
labels, so neither shows multi-speaker grouping. The **`replay`** provider is a
deterministic diarization stand-in: seeded with a conversation, it replays each
turn as an *anonymous detected voice* (`spk-1`, `spk-2`, … → `Voice 1`,
`Voice 2`, …), paced by incoming audio. That drives the whole `auto` path —
stable voice grouping, confidence, and the correction workflow — without a real
diarization engine.

```bash
# 1. Start the API with the replay provider pointed at a conversation
STT_PROVIDER=replay \
REPLAY_SCRIPT="$PWD/scripts/conversations/hpc_infrastructure.json" \
REPLAY_SECONDS_PER_TURN=2.5 \
  uvicorn app.main:app --port 8000        # (run from apps/api)

# 2. Stream it in auto mode and relabel each detected voice to its true speaker
python scripts/audio_playback_test.py \
    --script scripts/conversations/hpc_infrastructure.json \
    --api-base http://localhost:8000 \
    --speaker-mode auto --apply-corrections --realtime
```

You'll see anonymous `Voice 1/2/3` groups form as the conversation streams, then
`--apply-corrections` maps each voice to its ground-truth speaker in one call
per voice (`apply_to_voice`) and prints the regrouped transcript — the full
detect → group → correct loop. Point `REPLAY_SCRIPT` at the 2-speaker
conversation to see two voices instead of three.

When you're ready for a **real** diarizer, implement `SpeechToTextProvider` with
pyannote/whisperx and register it in `registry.py` — the harness and auto path
stay exactly the same.

### Discussion script format

See [`sample_discussion.json`](sample_discussion.json). Each turn's `speaker`
must be one of the domain speaker roles (`facilitator`, `customer`,
`participant`, `system`, `unknown`); in manual mode the harness stamps it as the
speaker for that turn's audio, and in auto mode it becomes the ground truth used
by `--apply-corrections`.

```json
{
  "title": "…", "customer": "…", "facilitator": "…",
  "voices": { "facilitator": "en_US-ryan-high", "customer": "en_US-amy-medium" },
  "turns": [
    { "speaker": "facilitator", "speaker_name": "Ryan", "text": "…" },
    { "speaker": "customer", "speaker_name": "Maya", "text": "…", "voice": "en_US-amy-medium" }
  ]
}
```

### Real transcription (faster-whisper / whisper.cpp)

With `STT_PROVIDER=mock` (the default) the server returns canned transcript text,
which is enough to validate the audio plumbing. To transcribe the synthesized
speech for real, run the API with `STT_PROVIDER=local` (faster-whisper — install
with `pip install -e '.[local]'`). A `whisper.cpp` adapter would slot in the same
way: implement `SpeechToTextProvider` and register it in
`apps/api/app/providers/registry.py` — no change to this harness needed.
