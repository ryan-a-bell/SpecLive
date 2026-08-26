"""Wire the *real* SpecLive services against a throwaway SQLite DB.

The harness deliberately drives production code — ``AnalysisService`` with a
real ``LanguageModelProvider`` and a real ``ContextStrategy`` — rather than
reimplementing derivation, so what we measure is the actual methodology.

Importing this module sets ``DATABASE_URL`` to an in-memory SQLite database
*before* any ``app.*`` module is imported (the app binds its engine at import
time from settings), exactly like ``apps/api/tests/conftest.py`` does.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# Bind to a private throwaway SQLite file and the in-process event bus before any
# app module is imported (the app binds its engine at import time). A temp file
# (rather than :memory:) avoids per-connection-DB surprises across pool types.
_TMPDIR = tempfile.mkdtemp(prefix="speclive-research-")
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{_TMPDIR}/harness.db")
os.environ.setdefault("STORAGE_LOCAL_ROOT", f"{_TMPDIR}/data")
os.environ.setdefault("EVENT_BUS", "memory")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("STT_PROVIDER", "mock")

from app.database import Base, SessionLocal, create_all  # noqa: E402
from app.events import get_event_bus  # noqa: E402
from app.logging import configure_logging  # noqa: E402

# The harness drives services directly (no FastAPI startup), so nothing has
# configured logging yet — structlog would otherwise print every domain event
# at INFO and bury the report. Quiet it to warnings+.
configure_logging("ERROR")
from app.providers.mock import MockLanguageModelProvider  # noqa: E402
from app.providers.base import LanguageModelProvider  # noqa: E402
from app.services.analysis_service import AnalysisService  # noqa: E402
from app.services.artifact_service import ArtifactService  # noqa: E402
from app.services.context_strategy import get_context_strategy  # noqa: E402
from app.services.session_service import SessionService  # noqa: E402
from app.services.transcript_service import TranscriptService  # noqa: E402
from app.repositories import SqlAlchemySessionRepository  # noqa: E402

_SCHEMA_READY = False

# Provider registry for the sweep. Mock is the deterministic, key-free baseline.
# A real LLM (openai_compatible) can be added here later behind an env guard.
PROVIDERS: dict[str, type[LanguageModelProvider]] = {
    "mock": MockLanguageModelProvider,
}

STRATEGIES = ("segment", "window", "full")


class Context:
    """A wired, wiped set of services sharing one DB session."""

    def __init__(self, provider_name: str, strategy_name: str) -> None:
        self.provider_name = provider_name
        self.strategy_name = strategy_name
        self.db = SessionLocal()
        self._wipe()
        self.repo = SqlAlchemySessionRepository(self.db)
        bus = get_event_bus()
        self.sessions = SessionService(self.repo, bus)
        self.transcript = TranscriptService(self.repo, bus)
        self.artifacts = ArtifactService(self.repo, bus)
        provider = PROVIDERS[provider_name]()
        self.analysis = AnalysisService(
            self.repo,
            self.artifacts,
            provider,
            context_strategy=get_context_strategy(strategy_name),
        )

    def _wipe(self) -> None:
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

    def close(self) -> None:
        self.db.close()


def make_context(provider_name: str, strategy_name: str) -> Context:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        create_all()
        _SCHEMA_READY = True
    return Context(provider_name, strategy_name)
