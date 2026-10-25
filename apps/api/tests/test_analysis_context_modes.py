"""AnalysisService should call the provider once per unit the configured
context strategy produces, and attribute each evidence item to whichever
segment the provider says it came from (not just the unit's anchor segment).
"""

from __future__ import annotations

from app.domain.enums import ArtifactType, DerivationMethod, EvidenceRelationship
from app.events import get_event_bus
from app.providers.base import (
    AnalysisUnit,
    ArtifactCandidate,
    EvidenceCandidate,
    LanguageModelProvider,
)
from app.repositories import SqlAlchemySessionRepository
from app.services.analysis_service import AnalysisService
from app.services.artifact_service import ArtifactService
from app.services.context_strategy import FullTranscriptStrategy, PerSegmentStrategy
from app.services.session_service import SessionService
from app.services.transcript_service import TranscriptService


class _RecordingLLM(LanguageModelProvider):
    """Fakes a context-aware provider: records every unit it's asked to
    analyze, and (if given >1 segments) cites evidence from the FIRST
    segment in the unit rather than the last — this is exactly the kind of
    cross-turn attribution a single-segment provider could never produce,
    and is what proves the unit's context actually reached the provider.
    """

    def __init__(self) -> None:
        self.calls: list[AnalysisUnit] = []

    def analyze_segment(self, text: str, *, speaker: str) -> list[ArtifactCandidate]:
        raise AssertionError("analyze_segment should not be called directly by AnalysisService")

    def analyze_unit(self, unit: AnalysisUnit) -> list[ArtifactCandidate]:
        self.calls.append(unit)
        cited = unit.segments[0]
        return [
            ArtifactCandidate(
                artifact_type=ArtifactType.REQUIREMENT,
                title="Derived from unit",
                statement="Statement",
                confidence=0.9,
                rationale="test",
                derivation_method=DerivationMethod.LLM,
                evidence=[
                    EvidenceCandidate(
                        quote_start=0,
                        quote_end=len(cited.text),
                        quoted_text=cited.text,
                        relationship=EvidenceRelationship.DIRECT,
                        confidence=0.9,
                        segment_id=cited.id,
                    )
                ],
            )
        ]

    def recommend_questions(self, context: str, *, gaps: list[str]) -> list[str]:
        return []


def _seed_session(db):  # type: ignore[no-untyped-def]
    repo = SqlAlchemySessionRepository(db)
    bus = get_event_bus()
    sessions = SessionService(repo, bus)
    transcript = TranscriptService(repo, bus)
    artifacts = ArtifactService(repo, bus)

    session = sessions.create(title="T", customer="Acme", facilitator="R")
    seg1 = transcript.add_segment(
        session.id, speaker="facilitator", text="What is the deadline?"  # type: ignore[arg-type]
    )
    seg2 = transcript.add_segment(
        session.id, speaker="customer", text="We need it live by Q3."  # type: ignore[arg-type]
    )
    return repo, artifacts, session, seg1, seg2


def test_full_transcript_strategy_makes_one_call_with_all_segments(db) -> None:  # type: ignore[no-untyped-def]
    repo, artifacts, session, seg1, seg2 = _seed_session(db)
    llm = _RecordingLLM()
    analysis = AnalysisService(repo, artifacts, llm, context_strategy=FullTranscriptStrategy())

    produced = analysis.analyze_session(session.id)

    assert len(llm.calls) == 1
    assert {s.id for s in llm.calls[0].segments} == {seg1.id, seg2.id}

    # Evidence must be attributed to seg1 (the first segment in the unit),
    # proving the analyzed unit's evidence isn't silently forced onto the
    # anchor (last) segment.
    assert len(produced) == 1
    (link,) = artifacts.evidence_for(produced[0].id)
    assert link.transcript_segment_id == seg1.id


def test_per_segment_strategy_makes_one_call_per_segment(db) -> None:  # type: ignore[no-untyped-def]
    repo, artifacts, session, seg1, seg2 = _seed_session(db)
    llm = _RecordingLLM()
    analysis = AnalysisService(repo, artifacts, llm, context_strategy=PerSegmentStrategy())

    produced = analysis.analyze_session(session.id)

    assert len(llm.calls) == 2
    assert [len(u.segments) for u in llm.calls] == [1, 1]
    assert len(produced) == 2


def test_analyze_segment_ignores_configured_strategy(db) -> None:  # type: ignore[no-untyped-def]
    """Explicit single-segment re-analysis always builds a 1-segment unit,
    even when the session-wide strategy is "full"."""

    repo, artifacts, session, seg1, seg2 = _seed_session(db)
    llm = _RecordingLLM()
    analysis = AnalysisService(repo, artifacts, llm, context_strategy=FullTranscriptStrategy())

    analysis.analyze_segment(seg2.id, session.id)

    assert len(llm.calls) == 1
    assert [s.id for s in llm.calls[0].segments] == [seg2.id]
