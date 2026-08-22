"""Decode uploaded audio files to canonical SpecLive PCM.

Canonical audio everywhere in this app is mono, signed 16-bit little-endian PCM
sampled at 16 kHz — the format every ``SpeechToTextProvider`` consumes. An
uploaded recording (MP3, M4A, WAV, …) is compressed and/or in some other
sample rate/channel layout, so it is decoded here once, at the edge, before it
enters the provider-neutral ingest path.

WAV/PCM is decoded natively with the standard library so the upload endpoint
works with no system dependencies. Compressed formats are decoded by shelling
out to ``ffmpeg`` when it is available; when it is not, a clear
:class:`AudioDecodeUnavailable` is raised so callers can return an actionable
error instead of a generic failure.
"""

from __future__ import annotations

import audioop
import io
import shutil
import subprocess
import wave

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH = 2  # bytes (signed 16-bit)

# ffmpeg is trusted local tooling, but cap runtime so a pathological upload
# cannot wedge a worker.
_FFMPEG_TIMEOUT_SECONDS = 120


class AudioDecodeError(ValueError):
    """The uploaded bytes could not be decoded to canonical PCM."""


class AudioDecodeUnavailable(AudioDecodeError):
    """Decoding this format needs ffmpeg, which is not installed."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _looks_like_wav(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _to_canonical(pcm: bytes, *, sample_rate: int, channels: int, width: int) -> bytes:
    """Convert arbitrary linear PCM to 16 kHz mono signed-16-bit."""

    if width != TARGET_SAMPLE_WIDTH:
        pcm = audioop.lin2lin(pcm, width, TARGET_SAMPLE_WIDTH)
        width = TARGET_SAMPLE_WIDTH
    if channels == 2:
        pcm = audioop.tomono(pcm, width, 0.5, 0.5)
    elif channels != 1:
        raise AudioDecodeError(f"Unsupported channel count: {channels}")
    if sample_rate != TARGET_SAMPLE_RATE:
        pcm, _ = audioop.ratecv(pcm, width, 1, sample_rate, TARGET_SAMPLE_RATE, None)
    return pcm


def _decode_wav(data: bytes) -> bytes:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:  # pragma: no cover - defensive
        raise AudioDecodeError(f"Invalid WAV audio: {exc}") from exc
    if not frames:
        raise AudioDecodeError("WAV audio contained no samples")
    return _to_canonical(frames, sample_rate=rate, channels=channels, width=width)


def _decode_with_ffmpeg(data: bytes) -> bytes:
    if not ffmpeg_available():
        raise AudioDecodeUnavailable(
            "Decoding compressed audio requires ffmpeg, which is not installed. "
            "Upload a 16 kHz mono PCM WAV file, or install ffmpeg on the API host."
        )
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ac", str(TARGET_CHANNELS),
                "-ar", str(TARGET_SAMPLE_RATE),
                "pipe:1",
            ],
            input=data,
            capture_output=True,
            timeout=_FFMPEG_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioDecodeError("Audio decoding timed out") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
        raise AudioDecodeError(
            f"Could not decode audio: {detail or 'unsupported or corrupt file'}"
        ) from exc
    if not result.stdout:
        raise AudioDecodeError("Audio decoding produced no audio")
    return result.stdout


def decode_to_pcm16(data: bytes) -> bytes:
    """Decode an uploaded audio file to canonical 16 kHz mono PCM16 bytes.

    Raises :class:`AudioDecodeUnavailable` when a compressed file needs ffmpeg
    and it is missing, and :class:`AudioDecodeError` for empty or invalid audio.
    """

    if not data:
        raise AudioDecodeError("Uploaded file was empty")
    if _looks_like_wav(data):
        return _decode_wav(data)
    return _decode_with_ffmpeg(data)
