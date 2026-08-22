"""Unit tests for the pluggable analysis context-grouping strategies."""

from __future__ import annotations

import pytest

from app.domain.entities import TranscriptSegment
from app.domain.enums import Speaker
from app.services.context_strategy import (
    FullTranscriptStrategy,
    PerSegmentStrategy,
    SlidingWindowStrategy,
    get_context_strategy,
)


def _segment(
    seq: int, *, start_time: float | None, speaker: Speaker = Speaker.CUSTOMER
) -> TranscriptSegment:
    return TranscriptSegment(
        session_id="S1",
        sequence_number=seq,
        speaker=speaker,
        text=f"segment {seq}",
        start_time=start_time,
        end_time=(start_time + 1) if start_time is not None else None,
    )


def test_per_segment_strategy_makes_one_unit_per_segment() -> None:
    segments = [_segment(i, start_time=float(i)) for i in range(3)]
    units = PerSegmentStrategy().build_units(segments)
    assert len(units) == 3
    assert [u.segments for u in units] == [[s] for s in segments]
    for unit, seg in zip(units, segments, strict=True):
        assert unit.anchor is seg


def test_full_transcript_strategy_makes_one_unit_with_everything() -> None:
    segments = [_segment(i, start_time=float(i)) for i in range(5)]
    units = FullTranscriptStrategy().build_units(segments)
    assert len(units) == 1
    assert units[0].segments == segments
    assert units[0].anchor is segments[-1]


def test_full_transcript_strategy_empty_session() -> None:
    assert FullTranscriptStrategy().build_units([]) == []


def test_sliding_window_groups_by_time_not_count() -> None:
    # Five segments spread across ~12 minutes; a 5-minute (300s) window
    # should produce three non-overlapping groups.
    times = [0, 60, 310, 320, 700]
    segments = [_segment(i, start_time=float(t)) for i, t in enumerate(times)]
    units = SlidingWindowStrategy(window_seconds=300).build_units(segments)

    assert len(units) == 3
    assert [s.sequence_number for s in units[0].segments] == [0, 1]
    assert [s.sequence_number for s in units[1].segments] == [2, 3]
    assert [s.sequence_number for s in units[2].segments] == [4]


def test_sliding_window_segments_without_timing_are_isolated() -> None:
    segments = [
        _segment(0, start_time=0.0),
        _segment(1, start_time=None),
        _segment(2, start_time=1.0),
    ]
    units = SlidingWindowStrategy(window_seconds=300).build_units(segments)
    # The untimed segment must not get silently merged into a neighboring
    # window (there's nothing to compare it against).
    assert len(units) == 3
    assert units[1].segments == [segments[1]]


def test_sliding_window_rejects_nonpositive_window() -> None:
    with pytest.raises(ValueError):
        SlidingWindowStrategy(window_seconds=0)


def test_get_context_strategy_resolves_known_modes() -> None:
    assert isinstance(get_context_strategy("segment"), PerSegmentStrategy)
    assert isinstance(get_context_strategy("full"), FullTranscriptStrategy)
    window = get_context_strategy("window", window_seconds=120)
    assert isinstance(window, SlidingWindowStrategy)
    assert window._window_seconds == 120  # noqa: SLF001 - test-only introspection


def test_get_context_strategy_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        get_context_strategy("bogus")
