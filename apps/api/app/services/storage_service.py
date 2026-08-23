"""Persist a conversation's content to the configured storage backend.

This service is the bridge between the domain (sessions, segments, artifacts,
evidence living in the relational DB) and the :class:`~app.storage.base.ContentStore`.
Given a session it writes the full per-conversation tree described in
:mod:`app.storage.layout` — the raw recording, the rendered transcript, the
derived requirements, the exported discovery packages, and a manifest tying them
together with checksums and model provenance.

It is deliberately idempotent for the regenerable files (transcript,
requirements, manifest) and append-only for exports (each carries a timestamp),
while the raw recording is write-once.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..config import Settings
from ..exporters import get_exporter
from ..repositories import SessionRepository
from ..repositories.mappers import (
    artifact_to_domain,
    evidence_to_domain,
    segment_to_domain,
    session_to_domain,
)
from ..storage import ContentStore, StoredObject, layout
from .errors import NotFoundError
from .export_service import ExportService
from .workspace_service import slugify_customer

_JSON = "application/json"
_MD = "text/markdown; charset=utf-8"


def _dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)


class ConversationStorageService:
    def __init__(
        self,
        repo: SessionRepository,
        export_service: ExportService,
        store: ContentStore,
        settings: Settings,
    ) -> None:
        self._repo = repo
        self._export = export_service
        self._store = store
        self._settings = settings

    # --- public API -------------------------------------------------------
    def snapshot(
        self,
        session_id: str,
        *,
        audio: bytes | None = None,
        audio_filename: str | None = None,
        audio_content_type: str | None = None,
    ) -> dict[str, Any]:
        """Write the full content tree for ``session_id`` and return a summary.

        ``audio`` is the raw recording bytes (from a live capture or an upload);
        it is persisted only when provided *and* ``STORAGE_PERSIST_AUDIO`` is on.
        Everything else is regenerated from the database, so calling this again
        refreshes the transcript/requirements and adds a new export snapshot.
        """

        session_row = self._repo.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session {session_id} not found")
        session = session_to_domain(session_row)

        workspace_id = slugify_customer(session.customer)
        conv_dir = layout.conversation_dir(
            workspace_id,
            session.id,
            title=session.title,
            created_at=session.created_at,
        )

        written: list[StoredObject] = []

        # --- raw recording (write-once) -----------------------------------
        recording_obj: StoredObject | None = None
        audio_skipped_reason: str | None = None
        if audio is not None:
            if self._settings.storage_persist_audio:
                ext = layout.recording_extension(
                    filename=audio_filename, content_type=audio_content_type
                )
                recording_obj = self._store.write_bytes(
                    layout.recording_path(conv_dir, extension=ext),
                    audio,
                    media_type=audio_content_type or "application/octet-stream",
                )
                written.append(recording_obj)
                meta = self._store.write_text(
                    layout.recording_meta_path(conv_dir),
                    _dumps(
                        {
                            "source_filename": audio_filename,
                            "content_type": audio_content_type,
                            "size_bytes": recording_obj.size_bytes,
                            "sha256": recording_obj.sha256,
                            "captured_at": datetime.now(UTC).isoformat(),
                        }
                    ),
                    media_type=_JSON,
                )
                written.append(meta)
            else:
                audio_skipped_reason = "storage_persist_audio=false"

        # --- transcript ---------------------------------------------------
        segments = [segment_to_domain(r) for r in self._repo.list_segments(session_id)]
        seg_payload = [s.model_dump(mode="json") for s in segments]
        written.append(
            self._store.write_text(
                layout.transcript_segments_path(conv_dir), _dumps(seg_payload), media_type=_JSON
            )
        )
        written.append(
            self._store.write_text(
                layout.transcript_markdown_path(conv_dir),
                self._render_transcript_md(session, segments),
                media_type=_MD,
            )
        )

        # --- requirements + evidence --------------------------------------
        artifacts = [artifact_to_domain(r) for r in self._repo.list_artifacts(session_id)]
        evidence = [evidence_to_domain(r) for r in self._repo.list_evidence(session_id)]
        written.append(
            self._store.write_text(
                layout.requirements_artifacts_path(conv_dir),
                _dumps([a.model_dump(mode="json") for a in artifacts]),
                media_type=_JSON,
            )
        )
        written.append(
            self._store.write_text(
                layout.requirements_evidence_path(conv_dir),
                _dumps([e.model_dump(mode="json") for e in evidence]),
                media_type=_JSON,
            )
        )

        # --- exports (timestamped history) --------------------------------
        timestamp = layout.export_timestamp()
        package = self._export.build_package(session_id)
        written.append(
            self._store.write_text(
                layout.export_path(conv_dir, timestamp=timestamp, extension=".json"),
                get_exporter("json").export(package),
                media_type=_JSON,
            )
        )
        written.append(
            self._store.write_text(
                layout.export_path(conv_dir, timestamp=timestamp, extension=".md"),
                get_exporter("markdown").export(package),
                media_type=_MD,
            )
        )

        # --- workspace metadata -------------------------------------------
        self._store.write_text(
            layout.workspace_meta_path(workspace_id),
            _dumps(
                {
                    "workspace_id": workspace_id,
                    "customer": session.customer,
                    "updated_at": datetime.now(UTC).isoformat(),
                    "storage": self._store.describe(),
                }
            ),
            media_type=_JSON,
        )

        # --- manifest (index + provenance + checksums) --------------------
        manifest = {
            "schema_version": layout.SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "workspace_id": workspace_id,
            "conversation": {
                "session_id": session.id,
                "title": session.title,
                "customer": session.customer,
                "status": session.status.value,
            },
            "provenance": {
                "stt_provider": self._settings.stt_provider,
                "llm_provider": self._settings.llm_provider,
                "embedding_provider": self._settings.embedding_provider,
                "llm_model": self._settings.llm_model,
                "auto_analyze": self._settings.auto_analyze,
            },
            "counts": {
                "segments": len(segments),
                "artifacts": len(artifacts),
                "evidence": len(evidence),
            },
            "recording": (
                {
                    "path": recording_obj.path,
                    "size_bytes": recording_obj.size_bytes,
                    "sha256": recording_obj.sha256,
                }
                if recording_obj is not None
                else {"persisted": False, "reason": audio_skipped_reason}
            ),
            "objects": [
                {
                    "path": obj.path,
                    "media_type": obj.media_type,
                    "size_bytes": obj.size_bytes,
                    "sha256": obj.sha256,
                }
                for obj in written
            ],
        }
        manifest_obj = self._store.write_text(
            layout.manifest_path(conv_dir), _dumps(manifest), media_type=_JSON
        )
        written.append(manifest_obj)

        return {
            "session_id": session.id,
            "workspace_id": workspace_id,
            "backend": self._store.backend_id,
            "conversation_dir": conv_dir,
            "audio_persisted": recording_obj is not None,
            "manifest_location": manifest_obj.location,
            "objects": written,
        }

    def describe(self, session_id: str) -> dict[str, Any]:
        """List what is currently stored for a conversation (paths only)."""

        session_row = self._repo.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session {session_id} not found")
        session = session_to_domain(session_row)
        workspace_id = slugify_customer(session.customer)
        conv_dir = layout.conversation_dir(
            workspace_id, session.id, title=session.title, created_at=session.created_at
        )
        paths = self._store.list_prefix(conv_dir)
        return {
            "session_id": session.id,
            "workspace_id": workspace_id,
            "backend": self._store.backend_id,
            "conversation_dir": conv_dir,
            "stored": bool(paths),
            "paths": paths,
        }

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _render_transcript_md(session, segments) -> str:  # type: ignore[no-untyped-def]
        lines: list[str] = [
            f"# Transcript — {session.title}",
            "",
            f"Customer: {session.customer}",
            "",
        ]
        for seg in segments:
            speaker = seg.speaker_name or (
                seg.speaker.value if hasattr(seg.speaker, "value") else str(seg.speaker)
            )
            stamp = f" _(t={seg.start_time:.1f}s)_" if seg.start_time is not None else ""
            lines.append(f"**{speaker}**{stamp}: {seg.text}")
            lines.append("")
        return "\n".join(lines)
