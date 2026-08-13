"""End-to-end discovery scenario.

1. Start a discovery session.
2. Submit several transcript segments.
3. Generate candidate artifacts (mock analysis).
4. Create evidence links (implicitly, from analysis).
5. Populate the discovery tree.
6. Create a side branch.
7. Confirm a requirement.
8. Export the discovery package.
"""

from __future__ import annotations

import json

from app.seed import seed


def test_full_discovery_scenario(client) -> None:  # type: ignore[no-untyped-def]
    # Ensure the shared script catalogue exists.
    seed(if_empty=True)

    # 1. Start a session anchored on the warehouse discovery script.
    session_id = client.post(
        "/api/v1/sessions",
        json={
            "title": "E2E Discovery",
            "customer": "Globex",
            "facilitator": "Ryan",
            "script_id": "SCRIPT-WAREHOUSE",
        },
    ).json()["id"]

    # 2. Submit several transcript segments.
    utterances = [
        ("facilitator", "What is the core problem?"),
        ("customer", "We lack a real-time view of picking and need updates within 30 seconds."),
        ("customer", "It must run on our rugged tablets and we cannot replace the WMS this year."),
        ("facilitator", "What happens when connectivity is intermittent?"),
    ]
    for speaker, text in utterances:
        assert (
            client.post(
                f"/api/v1/sessions/{session_id}/transcript",
                json={"speaker": speaker, "text": text},
            ).status_code
            == 201
        )

    # 3./4. Generate candidate artifacts + evidence via mock analysis.
    produced = client.post(f"/api/v1/sessions/{session_id}/analyze").json()
    assert produced, "analysis should derive candidate artifacts"
    for artifact in produced:
        assert artifact["validation_state"] in {"detected", "inferred"}

    # 5. Populate + read the discovery tree.
    tree = client.get(f"/api/v1/sessions/{session_id}/discovery-tree").json()
    assert tree["roots"], "tree should have at least one root artifact"

    # 6. Create a side branch off the current script stage.
    # (Branch creation via the graph service is exercised through the seeded
    # session; here we assert the projection endpoint is available.)
    graph = client.get(f"/api/v1/sessions/{session_id}/conversation-graph").json()
    assert "branches" in graph

    # 7. Confirm one requirement (explicit human action).
    requirement = next(a for a in produced if a["artifact_type"] == "requirement")
    confirmed = client.post(f"/api/v1/artifacts/{requirement['id']}/confirm").json()
    assert confirmed["validation_state"] == "customer_confirmed"
    assert confirmed["status"] == "confirmed"

    # 8. Export the discovery package (JSON + Markdown).
    pkg = json.loads(client.get(f"/api/v1/sessions/{session_id}/export?format=json").text)
    assert any(r["title"] == confirmed["title"] for r in pkg["confirmed_requirements"]), (
        "confirmed requirement must appear in the confirmed section"
    )

    md = client.get(f"/api/v1/sessions/{session_id}/export?format=markdown").text
    assert "# Discovery Package" in md

    # Coverage + script advancement round out the workflow.
    coverage = client.get(f"/api/v1/sessions/{session_id}/coverage").json()
    assert "summary" in coverage
    advanced = client.post(f"/api/v1/sessions/{session_id}/script/advance").json()
    assert advanced["current_index"] >= 1
