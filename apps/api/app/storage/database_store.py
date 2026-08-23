"""Database content store — optional single-backing-store backend.

Persists each object as a row in the ``stored_blobs`` table, keyed by the same
relative path the local backend would use on disk. This is offered for
deployments that want everything (structured data *and* binary content) in one
database. Large audio recordings in a relational DB bloat backups and are slow
to stream, so **local remains the default**; this backend exists for
single-store simplicity and future object-store parity, not as the recommended
place for big media.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import StoredBlobORM
from .base import ContentStore, StoredObject, sha256_hex


class DatabaseContentStore(ContentStore):
    backend_id = "database"

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    # --- ContentStore -----------------------------------------------------
    def write_bytes(
        self, path: str, data: bytes, *, media_type: str = "application/octet-stream"
    ) -> StoredObject:
        digest = sha256_hex(data)
        with self._session_factory() as db:
            row = db.get(StoredBlobORM, path)
            if row is None:
                row = StoredBlobORM(path=path)
                db.add(row)
            row.data = data
            row.media_type = media_type
            row.size_bytes = len(data)
            row.sha256 = digest
            db.commit()
        return StoredObject(
            path=path,
            size_bytes=len(data),
            sha256=digest,
            media_type=media_type,
            location=self.location(path),
        )

    def read_bytes(self, path: str) -> bytes:
        with self._session_factory() as db:
            row = db.get(StoredBlobORM, path)
            if row is None:
                raise FileNotFoundError(path)
            return bytes(row.data)

    def exists(self, path: str) -> bool:
        with self._session_factory() as db:
            return db.get(StoredBlobORM, path) is not None

    def list_prefix(self, prefix: str = "") -> list[str]:
        with self._session_factory() as db:
            stmt = select(StoredBlobORM.path)
            if prefix:
                stmt = stmt.where(StoredBlobORM.path.like(f"{prefix}%"))
            return sorted(db.execute(stmt).scalars().all())

    def location(self, path: str) -> str:
        return f"db://stored_blobs/{path}"

    def describe(self) -> dict[str, object]:
        return {"backend": self.backend_id, "table": StoredBlobORM.__tablename__}
