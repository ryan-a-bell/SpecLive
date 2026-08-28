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


def ingest(ctx: Context, transcript: dict) -> list:
    """Create the session and its segments; return segments in turn order.

    The returned list is indexed by ``turn_index`` (position in
    ``transcript['turns']``), so ``segments[i].id`` is the segment for turn i.
    """

    session = ctx.sessions.create(
        title=transcript.get("title", "research-case"),
        customer=transcript.get("customer", "unknown"),
        facilitator=transcript.get("facilitator", "unknown"),
    )
    ctx.session_id = session.id  # type: ignore[attr-defined]

    segments = []
    for i, turn in enumerate(transcript["turns"]):
        speaker = _SPEAKER_MAP.get(turn["speaker"], Speaker.UNKNOWN)
        seg = ctx.transcript.add_segment(
            session.id,
            speaker=speaker,
            text=turn["text"],
            start_time=float(i * 30),  # synthetic 30s spacing → windows are meaningful
            end_time=float(i * 30 + 25),
            speaker_name=turn.get("speaker_name"),
        )
        segments.append(seg)
    return segments
