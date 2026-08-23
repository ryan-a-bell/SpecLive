"""Persisted-content storage: recordings, transcripts, requirements, exports.

Selectable backend (local directory by default, database optional) behind a
single :class:`ContentStore` port, with a fixed on-disk layout (see
:mod:`app.storage.layout`).
"""

from .base import ContentStore, StoredObject
from .database_store import DatabaseContentStore
from .local_store import LocalContentStore
from .registry import get_content_store

__all__ = [
    "ContentStore",
    "StoredObject",
    "LocalContentStore",
    "DatabaseContentStore",
    "get_content_store",
]
