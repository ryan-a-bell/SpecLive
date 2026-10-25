"""Local-directory content store — the default storage backend.

Persists each object as a real file under a configurable root directory, so the
tree in :mod:`app.storage.layout` is exactly what appears on disk and can be
browsed, backed up, or synced with ordinary file tools. On first use it writes a
``.speclive-storage.json`` marker recording the layout schema version.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from . import layout
from .base import ContentStore, StoredObject, sha256_hex


class LocalContentStore(ContentStore):
    backend_id = "local"

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).expanduser().resolve()
        self._ensure_marker()

    @property
    def root(self) -> Path:
        return self._root

    # --- internals --------------------------------------------------------
    def _abs(self, path: str) -> Path:
        # Resolve and confine within root so a crafted path cannot escape it.
        candidate = (self._root / path).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(f"Refusing to write outside storage root: {path!r}")
        return candidate

    def _ensure_marker(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        marker = self._root / layout.MARKER_PATH
        if not marker.exists():
            marker.write_text(
                json.dumps(
                    {
                        "schema_version": layout.SCHEMA_VERSION,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    # --- ContentStore -----------------------------------------------------
    def write_bytes(
        self, path: str, data: bytes, *, media_type: str = "application/octet-stream"
    ) -> StoredObject:
        target = self._abs(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredObject(
            path=path,
            size_bytes=len(data),
            sha256=sha256_hex(data),
            media_type=media_type,
            location=str(target),
        )

    def read_bytes(self, path: str) -> bytes:
        return self._abs(path).read_bytes()

    def exists(self, path: str) -> bool:
        return self._abs(path).is_file()

    def list_prefix(self, prefix: str = "") -> list[str]:
        base = self._abs(prefix) if prefix else self._root
        if not base.exists():
            return []
        roots = [base] if base.is_dir() else []
        if base.is_file():
            return [base.relative_to(self._root).as_posix()]
        paths: list[str] = []
        for root in roots:
            for item in root.rglob("*"):
                if item.is_file():
                    paths.append(item.relative_to(self._root).as_posix())
        return sorted(paths)

    def location(self, path: str) -> str:
        return str(self._abs(path))

    def describe(self) -> dict[str, object]:
        return {
            "backend": self.backend_id,
            "root": str(self._root),
            "schema_version": layout.SCHEMA_VERSION,
        }
