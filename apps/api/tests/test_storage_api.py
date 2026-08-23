"""Storage endpoints + GET /settings/storage (and its no-secret guarantee)."""

from __future__ import annotations

import json


def _create_session(client) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        "/api/v1/sessions",
        json={"title": "Storage Call", "customer": "Zeta Inc", "facilitator": "Ryan"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_storage_settings_reports_backend(client) -> None:  # type: ignore[no-untyped-def]
    body = client.get("/api/v1/settings/storage").json()
    assert body["backend"] == "local"
    assert body["persist_audio"] is True
    assert body["schema_version"]
    assert body["local_root"]  # populated for the local backend


def test_storage_settings_never_leaks_secrets(client) -> None:  # type: ignore[no-untyped-def]
    raw = json.dumps(client.get("/api/v1/settings/storage").json())
    for needle in ("api_key", "password", "secret"):
        assert needle not in raw


def test_snapshot_then_describe(client, clean_db) -> None:  # type: ignore[no-untyped-def]
    session_id = _create_session(client)

    # Nothing stored yet.
    empty = client.get(f"/api/v1/sessions/{session_id}/storage").json()
    assert empty["stored"] is False
    assert empty["paths"] == []
    assert empty["workspace_id"] == "zeta-inc"

    # Snapshot with an uploaded recording.
    files = {"file": ("call.mp3", b"ID3-audio-bytes", "audio/mpeg")}
    snap = client.post(f"/api/v1/sessions/{session_id}/storage/snapshot", files=files)
    assert snap.status_code == 200
    result = snap.json()
    assert result["audio_persisted"] is True
    assert result["backend"] == "local"
    names = {o["path"].rsplit("/", 1)[-1] for o in result["objects"]}
    assert {"recording.mp3", "segments.json", "artifacts.json", "manifest.json"} <= names

    # Describe now lists the persisted tree.
    described = client.get(f"/api/v1/sessions/{session_id}/storage").json()
    assert described["stored"] is True
    assert any(p.endswith("/raw/recording.mp3") for p in described["paths"])


def test_snapshot_unknown_session_404(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/sessions/does-not-exist/storage/snapshot")
    assert resp.status_code == 404
