"""Shared pytest fixtures.

A file-based SQLite database in a temp dir is configured *before* the app is
imported, so the cached settings/engine bind to it.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# Configure an isolated database before importing any app module.
_TMPDIR = tempfile.mkdtemp(prefix="rdc-test-")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMPDIR}/test.db"
os.environ["EVENT_BUS"] = "memory"
os.environ["LOG_LEVEL"] = "WARNING"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, create_all  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    create_all()


@pytest.fixture()
def db() -> Iterator[object]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def clean_db() -> None:
    """Wipe all tables for isolation between tests that assert on counts."""

    with SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_session_id() -> str:
    """Seed the demo session and return its id."""

    return seed(if_empty=False)
