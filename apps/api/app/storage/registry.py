"""Content-store registry — resolves the configured storage backend.

Global-only for this increment (one deployment-wide backend selected by
``STORAGE_BACKEND``). Per-workspace / per-conversation overrides are tracked
separately (see the storage-settings follow-up issue) and would layer on top of
this resolver without changing its callers.
"""

from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import ContentStore
from .database_store import DatabaseContentStore
from .local_store import LocalContentStore


@lru_cache
def get_content_store() -> ContentStore:
    settings = get_settings()
    backend = (settings.storage_backend or "local").strip().lower()

    if backend == "local":
        return LocalContentStore(settings.storage_local_root)
    if backend == "database":
        # Imported lazily so the storage package doesn't pull in the DB engine
        # for callers that only use the local backend.
        from ..database import SessionLocal

        return DatabaseContentStore(SessionLocal)

    raise ValueError(
        f"Unsupported STORAGE_BACKEND: {settings.storage_backend!r} "
        "(expected 'local' or 'database')"
    )
