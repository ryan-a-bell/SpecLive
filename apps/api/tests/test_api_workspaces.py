"""Workspace-level context aggregation endpoints."""

from __future__ import annotations

import json

from app.domain.enums import HUMAN_CONFIRMED_STATES

_CONFIRMED_VALUES = {s.value for s in HUMAN_CONFIRMED_STATES}


def test_list_workspaces_groups_seeded_customer(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    workspaces = {w["id"]: w for w in resp.json()}
    assert "acme-logistics" in workspaces
    acme = workspaces["acme-logistics"]
    assert acme["name"] == "Acme Logistics"
    assert acme["session_count"] >= 1
    assert seeded_session_id in {s["id"] for s in acme["sessions"]}


def test_context_has_all_sections_and_source_tags(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/workspaces/acme-logistics/context")
    assert resp.status_code == 200
    pkg = resp.json()
    for key in (
        "workspace",
        "scope",
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
        "session_summaries",
    ):
        assert key in pkg, f"missing section: {key}"

    assert pkg["scope"] == "all"
    assert pkg["workspace"]["id"] == "acme-logistics"
    # Every aggregated item is tagged with the session it came from.
    for item in pkg["traceability"]:
        assert item["source_session_id"]
        assert item["source_session_title"]
    # scope=all keeps the known candidate requirement.
    candidate_titles = {r["title"] for r in pkg["candidate_requirements"]}
    assert "Status refresh within 30 seconds" in candidate_titles


def test_baseline_scope_excludes_candidates(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    pkg = client.get("/api/v1/workspaces/acme-logistics/context?scope=baseline").json()
    assert pkg["scope"] == "baseline"
    # No candidate requirements survive a baseline query.
    assert pkg["candidate_requirements"] == []
    # Everything that remains is human-confirmed.
    for item in pkg["traceability"]:
        assert item["validation_state"] in _CONFIRMED_VALUES
    # The seed confirms constraint CON-004, so baseline is not empty.
    assert pkg["traceability"], "baseline scope should retain the confirmed artifacts"


def test_context_aggregates_multiple_sessions(client) -> None:  # type: ignore[no-untyped-def]
    made = [
        client.post(
            "/api/v1/sessions",
            json={"title": f"Call {i}", "customer": "Globex Corp", "facilitator": "Fac"},
        ).json()["id"]
        for i in range(2)
    ]
    workspaces = {w["id"]: w for w in client.get("/api/v1/workspaces").json()}
    assert "globex-corp" in workspaces
    assert workspaces["globex-corp"]["session_count"] == 2

    pkg = client.get("/api/v1/workspaces/globex-corp/context").json()
    session_ids = {s["id"] for s in pkg["workspace"]["sessions"]}
    assert set(made) == session_ids


def test_markdown_context_renders(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/workspaces/acme-logistics/context?format=markdown")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    text = resp.text
    assert "# Workspace Context — Acme Logistics" in text
    assert "## Traceability appendix" in text


def test_unknown_workspace_is_404(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/v1/workspaces/does-not-exist/context")
    assert resp.status_code == 404


def test_session_export_default_unchanged(client, seeded_session_id) -> None:  # type: ignore[no-untyped-def]
    """The per-session export must keep returning the full package (scope=all)."""

    pkg = json.loads(client.get(f"/api/v1/sessions/{seeded_session_id}/export?format=json").text)
    candidate_titles = {r["title"] for r in pkg["candidate_requirements"]}
    assert "Status refresh within 30 seconds" in candidate_titles
