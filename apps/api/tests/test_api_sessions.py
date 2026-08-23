"""Session + transcript API tests."""

from __future__ import annotations


def _create_session(client) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        "/api/v1/sessions",
        json={"title": "Test", "customer": "Acme", "facilitator": "Ryan"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_create_and_get_session(client) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    resp = client.get(f"/api/v1/sessions/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer"] == "Acme"
    assert body["status"] == "active"


def test_creating_session_pauses_the_previous_active_session(client) -> None:  # type: ignore[no-untyped-def]
    first_id = _create_session(client)
    second_id = _create_session(client)

    assert client.get(f"/api/v1/sessions/{first_id}").json()["status"] == "paused"
    assert client.get(f"/api/v1/sessions/{second_id}").json()["status"] == "active"
    active = [
        session
        for session in client.get("/api/v1/sessions").json()
        if session["status"] == "active"
    ]
    assert [session["id"] for session in active] == [second_id]


def test_reactivating_session_pauses_the_current_active_session(client) -> None:  # type: ignore[no-untyped-def]
    first_id = _create_session(client)
    second_id = _create_session(client)

    response = client.patch(f"/api/v1/sessions/{first_id}", json={"status": "active"})

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert client.get(f"/api/v1/sessions/{second_id}").json()["status"] == "paused"


def test_missing_session_returns_404(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/sessions/does-not-exist").status_code == 404


def test_patch_session_status(client) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    resp = client.patch(f"/api/v1/sessions/{session_id}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["ended_at"] is not None


def test_transcript_append_and_list(client) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)
    for i, (speaker, text) in enumerate(
        [
            ("facilitator", "What matters most?"),
            ("customer", "Real-time visibility within 30 seconds."),
        ]
    ):
        resp = client.post(
            f"/api/v1/sessions/{session_id}/transcript",
            json={"speaker": speaker, "text": text},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["sequence_number"] == i + 1

    listed = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
    assert len(listed) == 2
    assert listed[0]["speaker"] == "facilitator"


def test_health(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/health").json()["status"] == "ok"
