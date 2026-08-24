"""Content-storage layer: layout, both backends, and the snapshot service."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.storage import layout
from app.storage.database_store import DatabaseContentStore
from app.storage.local_store import LocalContentStore


# --- layout ---------------------------------------------------------------
def test_layout_conversation_dir_is_stable_and_sortable() -> None:
    created = datetime(2026, 8, 23, tzinfo=UTC)
    conv = layout.conversation_dir(
        "acme-corp", "sess-123", title="Kickoff Call", created_at=created
    )
    assert conv == "workspaces/acme-corp/conversations/20260823-kickoff-call-sess-123"
    # Content paths hang off the conversation dir under typed subfolders.
    assert layout.recording_path(conv, extension=".mp3").endswith("/raw/recording.mp3")
    assert layout.transcript_segments_path(conv).endswith("/transcript/segments.json")
    assert layout.requirements_artifacts_path(conv).endswith("/requirements/artifacts.json")
    assert layout.manifest_path(conv).endswith("/manifest.json")


def test_recording_extension_prefers_content_type_then_filename() -> None:
    assert layout.recording_extension(filename="x.wav", content_type="audio/mpeg") == ".mp3"
    assert layout.recording_extension(filename="call.M4A", content_type=None) == ".m4a"
    assert layout.recording_extension(filename=None, content_type=None) == ".bin"


# --- local backend --------------------------------------------------------
def test_local_store_roundtrip_and_marker(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalContentStore(tmp_path)
    # Marker is written on init so an older tree can be detected/migrated later.
    marker = json.loads((tmp_path / layout.MARKER_PATH).read_text())
    assert marker["schema_version"] == layout.SCHEMA_VERSION

    obj = store.write_bytes("a/b/c.bin", b"hello", media_type="application/octet-stream")
    assert obj.size_bytes == 5
    assert store.read_bytes("a/b/c.bin") == b"hello"
    assert store.exists("a/b/c.bin")
    assert store.list_prefix("a") == ["a/b/c.bin"]
    assert obj.location.endswith("a/b/c.bin")


def test_local_store_refuses_path_escape(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalContentStore(tmp_path)
    with pytest.raises(ValueError):
        store.write_bytes("../escape.txt", b"nope")


# --- database backend -----------------------------------------------------
def test_database_store_roundtrip(db) -> None:  # type: ignore[no-untyped-def]
    from app.database import SessionLocal

    store = DatabaseContentStore(SessionLocal)
    path = "workspaces/ws/conversations/conv/raw/recording.mp3"
    store.write_bytes(path, b"\x00\x01audio", media_type="audio/mpeg")
    assert store.exists(path)
    assert store.read_bytes(path) == b"\x00\x01audio"
    assert path in store.list_prefix("workspaces/ws")
    # Upsert: writing the same path replaces the bytes, not duplicates the row.
    store.write_bytes(path, b"newer", media_type="audio/mpeg")
    assert store.read_bytes(path) == b"newer"
    assert store.location(path) == f"db://stored_blobs/{path}"


# --- snapshot service -----------------------------------------------------
def _make_service(db, store):  # type: ignore[no-untyped-def]
    from app.config import get_settings
    from app.repositories import SqlAlchemySessionRepository
    from app.services.export_service import ExportService
    from app.services.storage_service import ConversationStorageService

    repo = SqlAlchemySessionRepository(db)
    return (
        ConversationStorageService(repo, ExportService(repo), store, get_settings()),
        repo,
    )


def _create_session(db):  # type: ignore[no-untyped-def]
    from app.db import DiscoverySessionORM

    row = DiscoverySessionORM(
        id="stor-sess-1",
        title="Discovery Call",
        customer="Acme Corp",
        facilitator="Ryan",
        status="draft",
    )
    db.add(row)
    db.commit()
    return row


def test_snapshot_writes_full_tree_with_manifest(tmp_path, db, clean_db) -> None:  # type: ignore[no-untyped-def]
    _create_session(db)
    store = LocalContentStore(tmp_path)
    service, _ = _make_service(db, store)

    result = service.snapshot(
        "stor-sess-1",
        audio=b"ID3-fake-audio",
        audio_filename="call.mp3",
        audio_content_type="audio/mpeg",
    )

    assert result["workspace_id"] == "acme-corp"
    assert result["audio_persisted"] is True

    conv = result["conversation_dir"]
    for expected in (
        layout.recording_path(conv, extension=".mp3"),
        layout.recording_meta_path(conv),
        layout.transcript_segments_path(conv),
        layout.transcript_markdown_path(conv),
        layout.requirements_artifacts_path(conv),
        layout.requirements_evidence_path(conv),
        layout.manifest_path(conv),
        layout.workspace_meta_path("acme-corp"),
    ):
        assert store.exists(expected), expected

    # Raw recording is stored verbatim.
    assert store.read_bytes(layout.recording_path(conv, extension=".mp3")) == b"ID3-fake-audio"

    # Manifest records provenance + checksums, no secrets.
    manifest = json.loads(store.read_text(layout.manifest_path(conv)))
    assert manifest["schema_version"] == layout.SCHEMA_VERSION
    assert manifest["conversation"]["session_id"] == "stor-sess-1"
    assert "stt_provider" in manifest["provenance"]
    assert "api_key" not in json.dumps(manifest)
    assert all(o["sha256"] for o in manifest["objects"])


def test_snapshot_can_skip_audio(tmp_path, db, clean_db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app import config as config_module

    monkeypatch.setenv("STORAGE_PERSIST_AUDIO", "false")
    config_module.get_settings.cache_clear()
    try:
        _create_session(db)
        store = LocalContentStore(tmp_path)
        service, _ = _make_service(db, store)
        result = service.snapshot(
            "stor-sess-1", audio=b"audio", audio_filename="c.mp3", audio_content_type="audio/mpeg"
        )
        assert result["audio_persisted"] is False
        conv = result["conversation_dir"]
        assert not store.exists(layout.recording_path(conv, extension=".mp3"))
        # Transcript + requirements are still written.
        assert store.exists(layout.transcript_segments_path(conv))
    finally:
        config_module.get_settings.cache_clear()
