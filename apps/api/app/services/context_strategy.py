"""Pluggable strategies for grouping a session's transcript segments into the
:class:`~app.providers.base.AnalysisUnit` calls sent to a LanguageModelProvider.

This is the "how much context does the model see" knob, kept independent of
which provider answers the call — any strategy works with any provider (a
provider that can't use extra context just falls back to per-segment analysis
inside a bigger unit, see ``LanguageModelProvider.analyze_unit``).

Three strategies ship today; add more by registering a new
``ContextStrategy`` subclass in ``_STRATEGIES`` below — nothing else in the
analysis pipeline needs to change.
"""

from __future__ import annotations

import abc

from ..domain.entities import TranscriptSegment
from ..providers.base import AnalysisUnit


class ContextStrategy(abc.ABC):
    """Groups a session's ordered transcript segments into analysis units."""

    @abc.abstractmethod
    def build_units(self, segments: list[TranscriptSegment]) -> list[AnalysisUnit]: ...


class PerSegmentStrategy(ContextStrategy):
    """One unit per segment — no surrounding context (the original/default
    behavior). Cheapest and trivially streamable (call it right after each
    ``transcript.final``), but the provider sees every utterance in
    isolation: cross-turn reasoning (e.g. a facilitator's paraphrase two
    turns after the customer's answer) is invisible.
    """

    def build_units(self, segments: list[TranscriptSegment]) -> list[AnalysisUnit]:
        return [AnalysisUnit(segments=[segment]) for segment in segments]


class FullTranscriptStrategy(ContextStrategy):
    """One unit containing every segment in the session. Best cross-turn
    reasoning and the fewest calls, at the cost of a prompt that grows with
    the session and evidence that has to be re-attributed across the whole
    transcript rather than a single known segment. Not incremental — a live
    session would need to re-run the whole transcript on every call.
    """

    def build_units(self, segments: list[TranscriptSegment]) -> list[AnalysisUnit]:
        if not segments:
            return []
        return [AnalysisUnit(segments=list(segments))]


class SlidingWindowStrategy(ContextStrategy):
    """Groups consecutive segments into non-overlapping, time-boxed windows
    (default 5 minutes of conversation each). A middle ground: each call
    sees several turns of real context, but the prompt size stays bounded
    regardless of session length, and it's still incremental — a window
    closes and can be analyzed as soon as its time budget is used up,
    without waiting for the whole session to end.

    Segments are grouped by wall-clock proximity (``start_time``), not
    segment count, so a slow-talking session and a fast one both get
    ``window_seconds`` of conversation per unit. A segment with no timing
    info becomes its own single-segment unit (nothing to window it against).
    """

    def __init__(self, window_seconds: float = 300.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window_seconds = window_seconds

    def build_units(self, segments: list[TranscriptSegment]) -> list[AnalysisUnit]:
        units: list[AnalysisUnit] = []
        current: list[TranscriptSegment] = []
        window_start: float | None = None

        def _flush() -> None:
            nonlocal current, window_start
            if current:
                units.append(AnalysisUnit(segments=current))
            current = []
            window_start = None

        for segment in segments:
            if segment.start_time is None:
                _flush()
                units.append(AnalysisUnit(segments=[segment]))
                continue
            if window_start is None:
                window_start = segment.start_time
            elif segment.start_time - window_start > self._window_seconds:
                _flush()
                window_start = segment.start_time
            current.append(segment)
        _flush()
        return units


_STRATEGIES: dict[str, type[ContextStrategy]] = {
    "segment": PerSegmentStrategy,
    "full": FullTranscriptStrategy,
    "window": SlidingWindowStrategy,
}


def get_context_strategy(name: str, *, window_seconds: float = 300.0) -> ContextStrategy:
    """Resolve a configured strategy name (``ANALYSIS_CONTEXT_MODE``) to an
    instance. Unknown names fail loudly rather than silently falling back —
    a misconfigured mode should never quietly downgrade to per-segment.
    """

    cls = _STRATEGIES.get(name)
    if cls is None:
        raise ValueError(
            f"Unsupported analysis context mode: {name!r} (expected one of "
            f"{sorted(_STRATEGIES)})"
        )
    if cls is SlidingWindowStrategy:
        return SlidingWindowStrategy(window_seconds=window_seconds)
    return cls()
