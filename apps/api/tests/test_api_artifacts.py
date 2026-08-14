"""Artifact API: create, evidence, confirm/reject/merge, revisions."""

from __future__ import annotations

import pytest


@pytest.fixture()
def session_with_segment(client):  # type: ignore[no-untyped-def]
    session_id = client.post(
        "/api/v1/sessions",
        json={"title": "T", "customer": "Acme", "facilitator": "Ryan"},
    ).json()["id"]
    seg = client.post(
        f"/api/v1/sessions/{session_id}/transcript",
        json={"speaker": "customer", "text": "We need updates within 30 seconds."},
    ).json()
    return session_id, seg["id"]


def _create_artifact(client, session_id: str) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        f"/api/v1/sessions/{session_id}/artifacts",
        json={
            "artifact_type": "requirement",
            "title": "Refresh 30s",
            "statement": "The system shall refresh within 30 seconds.",
            "confidence": 0.9,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_create_artifact_is_candidate(session_with_segment, client) -> None:  # type: ignore[no-untyped-def]
    session_id, _ = session_with_segment
    artifact_id = _create_artifact(client, session_id)
    body = client.get(f"/api/v1/artifacts/{artifact_id}").json()
    assert body["status"] == "candidate"
    assert body["validation_state"] == "detected"


def test_add_evidence_and_list(session_with_segment, client) -> None:  # type: ignore[no-untyped-def]
    session_id, seg_id = session_with_segment
    artifact_id = _create_artifact(client, session_id)
    resp = client.post(
        f"/api/v1/artifacts/{artifact_id}/evidence",
        json={
            "transcript_segment_id": seg_id,
            "quote_start": 17,
            "quote_end": 34,
            "quoted_text": "within 30 seconds",
            "relationship": "direct",
            "confidence": 0.95,
        },
    )
    assert resp.status_code == 201, resp.text
    links = client.get(f"/api/v1/artifacts/{artifact_id}/evidence").json()
    assert len(links) == 1
    assert links[0]["relationship"] == "direct"


def test_confirm_creates_revision_and_confirmed_status(session_with_segment, client) -> None:  # type: ignore[no-untyped-def]
    session_id, _ = session_with_segment
    artifact_id = _create_artifact(client, session_id)
    resp = client.post(f"/api/v1/artifacts/{artifact_id}/confirm")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "confirmed"
    assert resp.json()["validation_state"] == "customer_confirmed"
    revisions = client.get(f"/api/v1/artifacts/{artifact_id}/revisions").json()
    assert len(revisions) == 1
    assert revisions[0]["revision_number"] == 1


def test_reject_artifact(session_with_segment, client) -> None:  # type: ignore[no-untyped-def]
    session_id, _ = session_with_segment
    artifact_id = _create_artifact(client, session_id)
    resp = client.post(f"/api/v1/artifacts/{artifact_id}/reject", json={"reason": "duplicate"})
    assert resp.json()["status"] == "rejected"


def test_patch_records_revision(session_with_segment, client) -> None:  # type: ignore[no-untyped-def]
    session_id, _ = session_with_segment
    artifact_id = _create_artifact(client, session_id)
    resp = client.patch(
        f"/api/v1/artifacts/{artifact_id}",
        json={"title": "Refresh <= 30s", "change_reason": "clarity"},
    )
    assert resp.json()["title"] == "Refresh <= 30s"
    assert len(client.get(f"/api/v1/artifacts/{artifact_id}/revisions").json()) == 1


def test_merge_repoints_evidence(session_with_segment, client) -> None:  # type: ignore[no-untyped-def]
    session_id, seg_id = session_with_segment
    survivor = _create_artifact(client, session_id)
    duplicate = _create_artifact(client, session_id)
    client.post(
        f"/api/v1/artifacts/{duplicate}/evidence",
        json={
            "transcript_segment_id": seg_id,
            "quote_start": 0,
            "quote_end": 2,
            "quoted_text": "We",
        },
    )
    resp = client.post(f"/api/v1/artifacts/{duplicate}/merge", json={"into_artifact_id": survivor})
    assert resp.json()["validation_state"] == "merged"
    assert resp.json()["superseded_by"] == survivor
    # Evidence moved to the survivor.
    assert len(client.get(f"/api/v1/artifacts/{survivor}/evidence").json()) == 1
    assert len(client.get(f"/api/v1/artifacts/{duplicate}/evidence").json()) == 0
