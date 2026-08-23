"""On-disk layout for persisted conversation content (storage scheme "B").

This module owns *only* the naming scheme — the relative paths under a storage
root at which a conversation's recording, transcript, requirements and exports
live. It has no I/O and no knowledge of which backend (local directory or
database) actually persists the bytes; a :class:`~app.storage.base.ContentStore`
takes a relative path from here and stores it wherever it likes.

Layout (per the design agreed in the storage-settings discussion)::

    <root>/
    ├── .speclive-storage.json                     # format-version marker
    └── workspaces/
        └── <workspace_id>/                        # slug derived from customer
            ├── workspace.json                     # workspace metadata + settings snapshot
            └── conversations/
                └── <yyyymmdd>-<title-slug>-<session_id>/
                    ├── manifest.json              # index + provenance + checksums
                    ├── raw/                       # WRITE-ONCE, never regenerated
                    │   ├── recording<ext>
                    │   └── recording.meta.json
                    ├── transcript/
                    │   ├── segments.json
                    │   └── transcript.md
                    ├── requirements/
                    │   ├── artifacts.json
                    │   └── evidence.json
                    └── exports/                   # regenerable, kept as history
                        ├── discovery-package-<ts>.json
                        └── discovery-package-<ts>.md

Keying the conversation directory on the immutable ``session_id`` (rather than a
sequential "conversation#") keeps the on-disk tree 1:1 with the database and
stable across re-imports; the date + title-slug prefix only makes it sortable
and human-readable.
"""

from __future__ import annotations

import re
from datetime import datetime

# Bump when the directory scheme changes in a way that needs migration. Written
# into the root marker file so a backend can detect and migrate an older tree.
SCHEMA_VERSION = "1"

MARKER_PATH = ".speclive-storage.json"
WORKSPACES_DIR = "workspaces"
CONVERSATIONS_DIR = "conversations"
WORKSPACE_META_FILE = "workspace.json"

MANIFEST_FILE = "manifest.json"
RAW_DIR = "raw"
RECORDING_STEM = "recording"
RECORDING_META_FILE = "recording.meta.json"
TRANSCRIPT_DIR = "transcript"
TRANSCRIPT_SEGMENTS_FILE = "segments.json"
TRANSCRIPT_MARKDOWN_FILE = "transcript.md"
REQUIREMENTS_DIR = "requirements"
REQUIREMENTS_ARTIFACTS_FILE = "artifacts.json"
REQUIREMENTS_EVIDENCE_FILE = "evidence.json"
EXPORTS_DIR = "exports"


def slugify(value: str, *, fallback: str = "item") -> str:
    """Lower-case, hyphenate and trim a value for use in a path segment."""

    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower().strip())
    slug = re.sub(r"^-+|-+$", "", slug)
    return slug or fallback


def _join(*parts: str) -> str:
    """Join path segments with forward slashes (storage paths are POSIX-style,
    independent of the host OS; the local backend maps them to real paths)."""

    return "/".join(p.strip("/") for p in parts if p)


def workspace_dir(workspace_id: str) -> str:
    return _join(WORKSPACES_DIR, slugify(workspace_id, fallback="workspace"))


def workspace_meta_path(workspace_id: str) -> str:
    return _join(workspace_dir(workspace_id), WORKSPACE_META_FILE)


def conversation_dirname(
    session_id: str, *, title: str | None = None, created_at: datetime | None = None
) -> str:
    """``<yyyymmdd>-<title-slug>-<session_id>`` — sortable, human, stable."""

    date_part = (created_at or datetime.now()).strftime("%Y%m%d")
    title_part = slugify(title or "", fallback="conversation")
    return f"{date_part}-{title_part}-{session_id}"


def conversation_dir(
    workspace_id: str,
    session_id: str,
    *,
    title: str | None = None,
    created_at: datetime | None = None,
) -> str:
    return _join(
        workspace_dir(workspace_id),
        CONVERSATIONS_DIR,
        conversation_dirname(session_id, title=title, created_at=created_at),
    )


# --- per-conversation content paths ---------------------------------------
# Each takes the conversation directory (from :func:`conversation_dir`) and
# returns the full relative path to a specific artifact within it.


def manifest_path(conv_dir: str) -> str:
    return _join(conv_dir, MANIFEST_FILE)


def recording_path(conv_dir: str, *, extension: str = ".bin") -> str:
    ext = extension if extension.startswith(".") else f".{extension}"
    return _join(conv_dir, RAW_DIR, f"{RECORDING_STEM}{ext}")


def recording_meta_path(conv_dir: str) -> str:
    return _join(conv_dir, RAW_DIR, RECORDING_META_FILE)


def transcript_segments_path(conv_dir: str) -> str:
    return _join(conv_dir, TRANSCRIPT_DIR, TRANSCRIPT_SEGMENTS_FILE)


def transcript_markdown_path(conv_dir: str) -> str:
    return _join(conv_dir, TRANSCRIPT_DIR, TRANSCRIPT_MARKDOWN_FILE)


def requirements_artifacts_path(conv_dir: str) -> str:
    return _join(conv_dir, REQUIREMENTS_DIR, REQUIREMENTS_ARTIFACTS_FILE)


def requirements_evidence_path(conv_dir: str) -> str:
    return _join(conv_dir, REQUIREMENTS_DIR, REQUIREMENTS_EVIDENCE_FILE)


def export_path(conv_dir: str, *, timestamp: str, extension: str) -> str:
    ext = extension if extension.startswith(".") else f".{extension}"
    return _join(conv_dir, EXPORTS_DIR, f"discovery-package-{timestamp}{ext}")


def export_timestamp(when: datetime | None = None) -> str:
    """Compact UTC-ish timestamp for export filenames, e.g. ``20260823T171045Z``."""

    return (when or datetime.now()).strftime("%Y%m%dT%H%M%SZ")


# Map common upload content types / filename extensions to a canonical recording
# extension so the stored raw file keeps a meaningful suffix.
_CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
}


def recording_extension(*, filename: str | None, content_type: str | None) -> str:
    """Best-effort canonical extension for a persisted recording."""

    if content_type:
        mapped = _CONTENT_TYPE_EXTENSIONS.get(content_type.split(";")[0].strip().lower())
        if mapped:
            return mapped
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if re.fullmatch(r"\.[a-z0-9]{1,5}", ext):
            return ext
    return ".bin"
