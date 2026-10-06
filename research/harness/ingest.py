"""Load a corpus ``transcript.json`` into a live session as ordered segments.

The transcript format is the one already used by ``scripts/conversations/*``:
a ``turns`` array of ``{speaker, speaker_name, text}``. One segment is created
per turn, in order, so a gold label's ``turn_index`` maps deterministically to
the created segment's id.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.enums import Speaker

from _bootstrap import Context

_SPEAKER_MAP = {
    "facilitator": Speaker.FACILITATOR,
    "customer": Speaker.CUSTOMER,
    "participant": Speaker.PARTICIPANT,
}


def load_transcript(path: Path) -> dict:
    return json.loads(path.read_text())


def ingest(
    ctx: Context,
    transcript: dict,
    *,
    words_per_minute: float | None = None,
    gap_seconds: float = 0.5,
) -> list:
    """Create the session and its segments; return segments in turn order.

    The returned list is indexed by ``turn_index`` (position in
    ``transcript['turns']``), so ``segments[i].id`` is the segment for turn i.

    Timing: by default each turn gets synthetic 30s spacing (kept stable so the
    scoring harness's window strategy is meaningful). Pass ``words_per_minute``
    to instead estimate each turn's duration from its word count and accumulate
    (with ``gap_seconds`` between turns) — a more realistic clock that matches a
    word-count ``time_range`` computed the same way.
    """

    session = ctx.sessions.create(
        title=transcript.get("title", "research-case"),
        customer=transcript.get("customer", "unknown"),
        facilitator=transcript.get("facilitator", "unknown"),
    )
    ctx.session_id = session.id  # type: ignore[attr-defined]

    segments = []
    clock = 0.0
    for i, turn in enumerate(transcript["turns"]):
        speaker = _SPEAKER_MAP.get(turn["speaker"], Speaker.UNKNOWN)
        if words_per_minute:
            start = clock
            end = start + len((turn["text"] or "").split()) / words_per_minute * 60.0
            clock = end + gap_seconds
        else:
            start, end = float(i * 30), float(i * 30 + 25)  # synthetic 30s spacing
        seg = ctx.transcript.add_segment(
            session.id,
            speaker=speaker,
            text=turn["text"],
            start_time=start,
            end_time=end,
            speaker_name=turn.get("speaker_name"),
        )
        segments.append(seg)
    return segments
