"""Pre-canned script catalogue + session script-switching tests."""

from __future__ import annotations

from app.scripts_catalog import seed_catalogue
from app.seed import seed

SIX_HABITS_ID = "SCRIPT-SIX-HABITS"
SPIN_ID = "SCRIPT-SPIN-NEEDS"
WAREHOUSE_ID = "SCRIPT-WAREHOUSE"


def _create_session(client) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        "/api/v1/sessions",
        json={"title": "Test", "customer": "Acme", "facilitator": "Ryan"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_catalogue_seed_is_idempotent_and_lists_starter_script(client) -> None:  # type: ignore[no-untyped-def]
    # Seeding twice must not duplicate stages.
    seed_catalogue()
    seed_catalogue()

    listed = client.get("/api/v1/scripts")
    assert listed.status_code == 200
    ids = {s["id"] for s in listed.json()}
    # The whole starter library is available.
    assert {SIX_HABITS_ID, SPIN_ID} <= ids

    detail = client.get(f"/api/v1/scripts/{SIX_HABITS_ID}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["name"].startswith("Technical Discovery Starter")
    stages = body["stages"]
    assert len(stages) == 12
    # Verbatim first question is preserved.
    assert stages[0]["primary_prompt"].startswith("Could I trouble you")
    # Stages are ordered by sequence.
    assert [s["sequence"] for s in stages] == list(range(1, 13))

    spin = client.get(f"/api/v1/scripts/{SPIN_ID}").json()
    assert spin["name"] == "Needs Discovery (SPIN)"
    assert [s["sequence"] for s in spin["stages"]] == list(range(1, 11))


def test_switching_session_script_restarts_advancement(client) -> None:  # type: ignore[no-untyped-def]
    seed()  # provides the warehouse script alongside the starter catalogue
    session_id = _create_session(client)

    # Attach the starter script and advance a couple of stages.
    patched = client.patch(f"/api/v1/sessions/{session_id}", json={"script_id": SIX_HABITS_ID})
    assert patched.status_code == 200
    assert patched.json()["script_id"] == SIX_HABITS_ID
    client.post(f"/api/v1/sessions/{session_id}/script/advance")
    client.post(f"/api/v1/sessions/{session_id}/script/advance")
    assert client.get(f"/api/v1/sessions/{session_id}/script").json()["current_index"] == 2

    # Switching to a different script restarts advancement at the first stage.
    switched = client.patch(f"/api/v1/sessions/{session_id}", json={"script_id": WAREHOUSE_ID})
    assert switched.status_code == 200
    state = client.get(f"/api/v1/sessions/{session_id}/script").json()
    assert state["script"]["id"] == WAREHOUSE_ID
    assert state["current_index"] == 0
