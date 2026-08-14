"""Export tests against the seeded demo session."""

from __future__ import annotations

import json


def test_json_export_has_all_sections(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    resp = client.get(f"/api/v1/sessions/{seeded_session_id}/export?format=json")
    assert resp.status_code == 200
    package = json.loads(resp.text)
    for key in (
        "executive_summary",
        "objectives",
        "stakeholder_needs",
        "confirmed_requirements",
        "candidate_requirements",
        "constraints",
        "assumptions",
        "risks",
        "decisions",
        "open_questions",
        "success_metrics",
        "traceability",
        "branch_summary",
    ):
        assert key in package, f"missing section: {key}"
    # The seed confirms CON-004 (a constraint) and leaves REQ-002 as a candidate.
    candidate_titles = {r["title"] for r in package["candidate_requirements"]}
    assert "Status refresh within 30 seconds" in candidate_titles


def test_markdown_export_renders(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    resp = client.get(f"/api/v1/sessions/{seeded_session_id}/export?format=markdown")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    text = resp.text
    assert "# Discovery Package" in text
    assert "## Traceability appendix" in text
    assert "Acme Logistics" in text


def test_traceability_links_evidence(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    package = json.loads(
        client.get(f"/api/v1/sessions/{seeded_session_id}/export?format=json").text
    )
    trace = {t["artifact_id"]: t for t in package["traceability"]}
    assert trace["REQ-002"]["evidence"], "REQ-002 must retain evidence"
    quotes = {e["quoted_text"] for e in trace["REQ-002"]["evidence"]}
    assert "within 30 seconds" in quotes
