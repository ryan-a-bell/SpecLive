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

from app.database import Base, SessionLocal, create_all
from app.events import get_event_bus
from app.logging import configure_logging

# The harness drives services directly (no FastAPI startup), so nothing has
# configured logging yet — structlog would otherwise print every domain event
# at INFO and bury the report. Quiet it to warnings+.
configure_logging("ERROR")
from app.config import get_settings
from app.providers.base import EmbeddingProvider, LanguageModelProvider
from app.providers.mock import (
    MockEmbeddingProvider,
    MockLanguageModelProvider,
)
from app.providers.openai_compatible import (
    OpenAICompatibleLanguageModelProvider,
)
from app.repositories import SqlAlchemySessionRepository
from app.services.analysis_service import AnalysisService
from app.services.artifact_service import ArtifactService
from app.services.context_strategy import get_context_strategy
from app.services.session_service import SessionService
from app.services.transcript_service import TranscriptService

_SCHEMA_READY = False

STRATEGIES = ("segment", "window", "full")
PROVIDER_NAMES = ("mock", "openai_compatible")


def provider_available(name: str) -> tuple[bool, str]:
    """Whether a sweep provider can actually run here, and why not if it can't.

    ``mock`` always runs (no keys/network). ``openai_compatible`` needs
    ``LLM_API_KEY`` (with ``LLM_API_BASE`` / ``LLM_MODEL``); absent a key the
    sweep skips it with this reason rather than erroring.
    """
    if name == "mock":
        return True, ""
    if name == "openai_compatible":
        if not get_settings().llm_api_key:
            return False, "LLM_API_KEY not set (set LLM_API_BASE/LLM_API_KEY/LLM_MODEL to enable)"
        return True, ""
    return False, f"unknown provider {name!r}"


def build_llm(name: str) -> LanguageModelProvider:
    if name == "mock":
        return MockLanguageModelProvider()
    if name == "openai_compatible":
        s = get_settings()
        return OpenAICompatibleLanguageModelProvider(
            base_url=s.llm_api_base,
            api_key=s.llm_api_key or "",
            model=s.llm_model,
            timeout=s.llm_timeout_seconds,
        )
    raise ValueError(f"Unknown provider {name!r}")


def build_embedder() -> EmbeddingProvider:
    """Embedding provider for the embedding matcher — mock (hash) by default.
    Swap ``EMBEDDING_PROVIDER`` once a real embedding adapter is registered in
    the app; the matcher is agnostic to which provider it gets."""
    if get_settings().embedding_provider == "mock":
        return MockEmbeddingProvider()
    from app.providers.registry import get_embedding_provider

    return get_embedding_provider()


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
        provider = build_llm(provider_name)
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
