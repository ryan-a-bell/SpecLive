"""Evidence-link validation and the analysis pipeline (mock provider)."""

from __future__ import annotations

import pytest

from app.events import get_event_bus
from app.providers.mock import MockLanguageModelProvider
from app.repositories import SqlAlchemySessionRepository
from app.services.analysis_service import AnalysisService
from app.services.artifact_service import ArtifactService
from app.services.errors import ValidationError
from app.services.session_service import SessionService
from app.services.transcript_service import TranscriptService


def test_invalid_quote_offsets_rejected(db) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySessionRepository(db)
    bus = get_event_bus()
    sessions = SessionService(repo, bus)
    artifacts = ArtifactService(repo, bus)
    session = sessions.create(title="T", customer="Acme", facilitator="R")
    from app.domain.enums import ArtifactType

    artifact = artifacts.create(
        session.id,
        artifact_type=ArtifactType.REQUIREMENT,
        title="X",
        statement="Y",
    )
    with pytest.raises(ValidationError):
        artifacts.add_evidence(
            artifact.id,
            transcript_segment_id="seg",
            quote_start=10,
            quote_end=3,  # end < start
            quoted_text="bad",
        )


def test_analysis_produces_inferred_not_confirmed(db) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemySessionRepository(db)
    bus = get_event_bus()
    sessions = SessionService(repo, bus)
    transcript = TranscriptService(repo, bus)
    artifacts = ArtifactService(repo, bus)
    analysis = AnalysisService(repo, artifacts, MockLanguageModelProvider())

    session = sessions.create(title="T", customer="Acme", facilitator="R")
    transcript.add_segment(
        session.id,
        speaker="customer",  # type: ignore[arg-type]
        text=(
            "We need a real-time view and updates within 30 seconds, "
            "and we cannot replace the WMS."
        ),
    )
    produced = analysis.analyze_session(session.id)

    assert produced, "mock analysis should derive at least one candidate"
    # Nothing produced by analysis may be confirmed/baselined.
    for artifact in produced:
        assert artifact.validation_state.value in {"detected", "inferred"}
    # Each derived artifact carries at least one evidence link.
    for artifact in produced:
        assert artifacts.evidence_for(artifact.id)
