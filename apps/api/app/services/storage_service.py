"""Persist a conversation's content to the configured content store.

Structured discovery data lives in the relational database; this service writes
the *content sidecars* — the raw recording, a rendered transcript, a snapshot of
the derived requirements, and exported discovery packages — into the
:class:`~app.storage.base.ContentStore` under the layout in
:mod:`app.storage.layout`, alongside a ``manifest.json`` that indexes everything
with checksums and provenance (which STT/LLM providers produced it).

It is deliberately best-effort at the call sites (a storage failure must never
break live transcription), but the service itself raises so tests and the
explicit snapshot endpoint see real errors.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..config import Settings
from ..domain.entities import DiscoverySession, TranscriptSegment
from ..repositories import SessionRepository
from ..repositories.mappers import segment_to_domain, session_to_domain
from ..storage import layout
from ..storage.base import ContentStore, StoredObject, sha256_hex
from .errors import NotFoundError
from .export_service import ExportService
from .workspace_service import slugify_customer

_JSON_MEDIA = "application/json"
_MD_MEDIA = "text/markdown; charset=utf-8"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


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
        """Write the full content tree for one conversation and return a summary.

        ``audio`` is the raw recording bytes (e.g. from a file upload); when
        provided and ``STORAGE_PERSIST_AUDIO`` is on, it is stored write-once
        under ``raw/``. Transcript, requirements and exports are (re)generated
        from the current database state on every call.
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

        # 1. Raw recording (write-once; skipped if disabled or absent).
        audio_persisted = False
        if audio is not None and self._settings.storage_persist_audio:
            ext = layout.recording_extension(
                filename=audio_filename, content_type=audio_content_type
            )
            rec_path = layout.recording_path(conv_dir, extension=ext)
            written.append(
                self._store.write_bytes(
                    rec_path,
                    audio,
                    media_type=audio_content_type or "application/octet-stream",
                )
            )
            written.append(
                self._store.write_bytes(
                    layout.recording_meta_path(conv_dir),
                    _json_bytes(
                        {
                            "source_filename": audio_filename,
                            "content_type": audio_content_type,
                            "size_bytes": len(audio),
                            "sha256": sha256_hex(audio),
                            "stored_at": datetime.now(UTC).isoformat(),
                        }
                    ),
                    media_type=_JSON_MEDIA,
                )
            )
            audio_persisted = True

        # 2. Transcript (canonical segments + human-readable render).
        segments = [segment_to_domain(r) for r in self._repo.list_segments(session.id)]
        written.append(
            self._store.write_bytes(
                layout.transcript_segments_path(conv_dir),
                _json_bytes([s.model_dump(mode="json") for s in segments]),
                media_type=_JSON_MEDIA,
            )
        )
        written.append(
            self._store.write_text(
                layout.transcript_markdown_path(conv_dir),
                self._render_transcript_md(session, segments),
                media_type=_MD_MEDIA,
            )
        )

        # 3. Requirements snapshot (full package + evidence traceability).
        package = self._export.build_package(session.id)
        written.append(
            self._store.write_bytes(
                layout.requirements_artifacts_path(conv_dir),
                _json_bytes(package),
                media_type=_JSON_MEDIA,
            )
        )
        written.append(
            self._store.write_bytes(
                layout.requirements_evidence_path(conv_dir),
                _json_bytes(package["traceability"]),
                media_type=_JSON_MEDIA,
            )
        )

        # 4. Exported discovery packages (timestamped history).
        timestamp = layout.export_timestamp()
        for fmt, ext, media in (("json", ".json", _JSON_MEDIA), ("markdown", ".md", _MD_MEDIA)):
            content, _ = self._export.export(session.id, fmt)
            written.append(
                self._store.write_text(
                    layout.export_path(conv_dir, timestamp=timestamp, extension=ext),
                    content,
                    media_type=media,
                )
            )

        # 5. Workspace metadata (non-secret settings snapshot).
        self._store.write_bytes(
            layout.workspace_meta_path(workspace_id),
            _json_bytes(self._workspace_meta(workspace_id, session.customer)),
            media_type=_JSON_MEDIA,
        )

        # 6. Manifest indexing everything with checksums + provenance.
        manifest = self._build_manifest(
            session=session,
            workspace_id=workspace_id,
            conv_dir=conv_dir,
            objects=written,
            segment_count=len(segments),
            audio_persisted=audio_persisted,
        )
        manifest_obj = self._store.write_bytes(
            layout.manifest_path(conv_dir),
            _json_bytes(manifest),
            media_type=_JSON_MEDIA,
        )

        return {
            "session_id": session.id,
            "workspace_id": workspace_id,
            "backend": self._store.backend_id,
            "conversation_dir": conv_dir,
            "audio_persisted": audio_persisted,
            "manifest_location": manifest_obj.location,
            "objects": [self._object_summary(o) for o in [*written, manifest_obj]],
        }

    def describe(self, session_id: str) -> dict[str, Any]:
        """List what is currently stored for a conversation (no bytes)."""

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
            "paths": paths,
            "stored": bool(paths),
        }

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _object_summary(obj: StoredObject) -> dict[str, Any]:
        return {
            "path": obj.path,
            "size_bytes": obj.size_bytes,
            "sha256": obj.sha256,
            "media_type": obj.media_type,
            "location": obj.location,
        }

    def _workspace_meta(self, workspace_id: str, customer: str) -> dict[str, Any]:
        return {
            "id": workspace_id,
            "name": customer,
            "updated_at": datetime.now(UTC).isoformat(),
            "storage": {
                "backend": self._store.backend_id,
                "persist_audio": self._settings.storage_persist_audio,
                "schema_version": layout.SCHEMA_VERSION,
            },
        }

    def _build_manifest(
        self,
        *,
        session: DiscoverySession,
        workspace_id: str,
        conv_dir: str,
        objects: list[StoredObject],
        segment_count: int,
        audio_persisted: bool,
    ) -> dict[str, Any]:
        s = self._settings
        return {
            "schema_version": layout.SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "workspace": {"id": workspace_id, "name": session.customer},
            "conversation": {
                "session_id": session.id,
                "title": session.title,
                "customer": session.customer,
                "facilitator": session.facilitator,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "directory": conv_dir,
            },
            "counts": {"transcript_segments": segment_count},
            "audio_persisted": audio_persisted,
            # Provenance: which providers produced this content. No secrets.
            "provenance": {
                "stt_provider": s.stt_provider,
                "llm_provider": s.llm_provider,
                "llm_model": s.llm_model if s.llm_provider == "openai_compatible" else None,
                "embedding_provider": s.embedding_provider,
                "auto_analyze": s.auto_analyze,
                "analysis_context_mode": s.analysis_context_mode,
            },
            "objects": [self._object_summary(o) for o in objects],
        }

    @staticmethod
    def _render_transcript_md(
        session: DiscoverySession, segments: list[TranscriptSegment]
    ) -> str:
        lines: list[str] = [f"# Transcript — {session.title}", ""]
        lines.append(f"- **Customer:** {session.customer}")
        lines.append(f"- **Facilitator:** {session.facilitator}")
        lines.append(f"- **Session:** `{session.id}`")
        lines.append(f"- **Segments:** {len(segments)}")
        lines.append("")
        if not segments:
            lines.append("_No transcript segments recorded._")
            return "\n".join(lines) + "\n"
        for seg in segments:
            who = seg.speaker_name or seg.speaker.value
            stamp = f"[{seg.start_time:.1f}s] " if seg.start_time is not None else ""
            lines.append(f"**{who}** {stamp}— {seg.text}")
            lines.append("")
        return "\n".join(lines) + "\n"
