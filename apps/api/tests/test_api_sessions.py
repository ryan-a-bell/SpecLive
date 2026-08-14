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
