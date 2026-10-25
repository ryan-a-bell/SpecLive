"""Discovery-script catalogue management."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _script_payload(name: str = "Field Operations Discovery") -> dict:
    return {
        "name": name,
        "version": "1.0.0",
        "description": "A reusable script for field-work discovery.",
        "stages": [
            {
                "title": "Current workflow",
                "objective": "Understand the work as it happens today.",
                "primary_prompt": "Walk me through the current workflow.",
                "alternative_prompts": ["Where does it slow down?"],
                "completion_criteria": ["Actors and handoffs are named"],
            }
        ],
    }


def test_script_catalogue_create_update_and_archive(client: TestClient) -> None:
    created_response = client.post("/api/v1/scripts", json=_script_payload())
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["name"] == "Field Operations Discovery"
    assert created["archived"] is False
    assert created["stages"][0]["sequence"] == 0

    stage_id = created["stages"][0]["id"]
    updated_body = _script_payload("Field Operations Discovery v2")
    updated_body["version"] = "2.0.0"
    updated_body["stages"][0]["id"] = stage_id
    updated_body["stages"].append(
        {
            "title": "Validate",
            "objective": "Confirm the proposed workflow.",
            "primary_prompt": "What would make this recommendation incomplete?",
            "alternative_prompts": [],
            "completion_criteria": [],
        }
    )

    updated_response = client.put(f"/api/v1/scripts/{created['id']}", json=updated_body)
    assert updated_response.status_code == 200
    updated = updated_response.json()
    assert updated["name"] == "Field Operations Discovery v2"
    assert updated["stages"][0]["id"] == stage_id
    assert [stage["sequence"] for stage in updated["stages"]] == [0, 1]

    archived_response = client.post(f"/api/v1/scripts/{created['id']}/archive")
    assert archived_response.status_code == 200
    assert archived_response.json()["archived"] is True

    active_ids = {script["id"] for script in client.get("/api/v1/scripts").json()}
    assert created["id"] not in active_ids
    all_scripts = client.get("/api/v1/scripts?include_archived=true").json()
    assert any(script["id"] == created["id"] and script["archived"] for script in all_scripts)


def test_script_attached_to_session_cannot_be_archived(client: TestClient) -> None:
    script = client.post("/api/v1/scripts", json=_script_payload("In-use script")).json()
    session_response = client.post(
        "/api/v1/sessions",
        json={
            "title": "Discovery",
            "customer": "Acme",
            "facilitator": "Robin",
            "script_id": script["id"],
        },
    )
    assert session_response.status_code == 201

    archived_response = client.post(f"/api/v1/scripts/{script['id']}/archive")
    assert archived_response.status_code == 422
    assert "attached to a conversation" in archived_response.json()["detail"]
