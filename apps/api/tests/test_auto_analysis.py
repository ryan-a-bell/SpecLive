"""Auto-derivation: finalizing a segment drafts candidate artifacts."""

from __future__ import annotations

from app.config import Settings
from app.services import auto_analysis


def _create_session(client) -> str:  # type: ignore[no-untyped-def]
    return client.post(
        "/api/v1/sessions",
        json={"title": "Auto", "customer": "Acme", "facilitator": "Ryan"},
    ).json()["id"]


def test_finalized_segment_auto_derives_candidates(client) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)

    # No explicit /analyze call — adding the segment is enough.
    resp = client.post(
        f"/api/v1/sessions/{session_id}/transcript",
        json={"speaker": "customer", "text": "We need updates within 30 seconds."},
    )
    assert resp.status_code == 201

    artifacts = client.get(f"/api/v1/sessions/{session_id}/artifacts").json()
    assert artifacts, "the model should have drafted at least one candidate"
    assert all(a["validation_state"] in {"detected", "inferred"} for a in artifacts)

    # The candidate is traceable to the transcript span it came from.
    evidence = client.get(f"/api/v1/artifacts/{artifacts[0]['id']}/evidence").json()
    assert evidence, "a derived candidate should carry its evidence"


def test_auto_analyze_can_be_disabled(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(auto_analysis, "get_settings", lambda: Settings(auto_analyze=False))
    session_id = _create_session(client)

    resp = client.post(
        f"/api/v1/sessions/{session_id}/transcript",
        json={"speaker": "customer", "text": "We need updates within 30 seconds."},
    )
    assert resp.status_code == 201
    assert client.get(f"/api/v1/sessions/{session_id}/artifacts").json() == []
