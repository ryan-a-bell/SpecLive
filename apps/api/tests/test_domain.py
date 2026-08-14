"""Domain entity and enum tests."""

from __future__ import annotations

from app.domain import entities as e
from app.domain.enums import ArtifactType, EvidenceRelationship, ValidationState


def test_artifact_defaults_to_candidate_and_detected() -> None:
    artifact = e.DiscoveryArtifact(
        session_id="s1",
        artifact_type=ArtifactType.REQUIREMENT,
        title="Refresh",
        statement="The system shall refresh within 30 seconds.",
    )
    assert artifact.validation_state is ValidationState.DETECTED
    assert artifact.confidence == 0.0
    assert artifact.id  # auto-assigned uuid


def test_evidence_link_carries_relationship_and_offsets() -> None:
    link = e.EvidenceLink(
        artifact_id="a1",
        transcript_segment_id="seg1",
        quote_start=3,
        quote_end=10,
        quoted_text="within",
        relationship=EvidenceRelationship.DIRECT,
    )
    assert link.relationship is EvidenceRelationship.DIRECT
    assert link.quote_end > link.quote_start


def test_all_artifact_types_present() -> None:
    expected = {
        "objective",
        "stakeholder_need",
        "requirement",
        "constraint",
        "assumption",
        "risk",
        "decision",
        "open_question",
        "success_metric",
        "integration",
        "stakeholder",
    }
    assert {t.value for t in ArtifactType} == expected
