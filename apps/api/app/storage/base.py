"""Content-store port: where recordings/transcripts/requirements/exports live.

A :class:`ContentStore` persists opaque bytes at a relative path (the paths are
computed by :mod:`app.storage.layout`). Two backends implement it:

* :class:`~app.storage.local_store.LocalContentStore` — a local directory tree
  (the default), directly browsable on disk.
* :class:`~app.storage.database_store.DatabaseContentStore` — rows in a blob
  table, for deployments that want a single backing store.

The store deliberately knows nothing about workspaces, conversations, or the
directory scheme — that separation keeps the layout in one place and makes new
backends (e.g. an S3/object-store) a small, self-contained addition behind the
same interface.
"""

from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredObject:
    """Metadata describing a persisted object (not its bytes)."""

    path: str
    size_bytes: int
    sha256: str
    media_type: str
    #: Human-readable location for the object, e.g. an absolute file path for
    #: the local backend or ``db://<path>`` for the database backend. Useful for
    #: surfacing "where is my data" in a settings UI without exposing internals.
    location: str


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ContentStore(abc.ABC):
    """Provider-neutral binary content store keyed by relative path."""

    #: Short identifier, e.g. "local" or "database".
    backend_id: str

    @abc.abstractmethod
    def write_bytes(
        self, path: str, data: bytes, *, media_type: str = "application/octet-stream"
    ) -> StoredObject: ...

    def write_text(
        self, path: str, text: str, *, media_type: str = "text/plain; charset=utf-8"
    ) -> StoredObject:
        return self.write_bytes(path, text.encode("utf-8"), media_type=media_type)

    @abc.abstractmethod
    def read_bytes(self, path: str) -> bytes: ...

    def read_text(self, path: str) -> str:
        return self.read_bytes(path).decode("utf-8")

    @abc.abstractmethod
    def exists(self, path: str) -> bool: ...

    @abc.abstractmethod
    def list_prefix(self, prefix: str = "") -> list[str]:
        """Return every stored path under ``prefix`` (recursive), sorted."""

    @abc.abstractmethod
    def location(self, path: str) -> str:
        """Human-readable location for ``path`` (need not exist yet)."""

    @abc.abstractmethod
    def describe(self) -> dict[str, object]:
        """Non-secret summary of this backend for a settings/status endpoint."""
