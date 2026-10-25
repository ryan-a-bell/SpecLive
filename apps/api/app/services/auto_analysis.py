"""Auto-derivation: draft candidate artifacts the moment a segment is finalized.

The language model authors the candidate requirements; the facilitator only
confirms, edits, or rejects them. Wiring that derivation to the
``transcript.segment.finalized`` domain event means it fires for *every* ingest
path — live mic, file upload, manual entry — without the client having to issue a
separate ``POST /analyze``. Derived artifacts remain proposals (detected /
inferred); the human-validation guardrail is untouched.

The handler is synchronous (it runs inline on the in-process bus, matching the
rest of the MVP's synchronous services) and defensive: it opens its own database
session and never raises out of ``publish`` — a derivation failure is logged and
must not break transcript ingestion. A queue-backed bus could later run the same
handler off the request path with no change to callers.
"""

from __future__ import annotations

from collections.abc import Callable

from ..config import get_settings
from ..database import SessionLocal
from ..domain.events import DomainEvent, EventType
from ..events import EventBus
from ..logging import get_logger
from ..providers import get_llm_provider
from ..repositories import SqlAlchemySessionRepository
from .analysis_service import AnalysisService
from .artifact_service import ArtifactService

logger = get_logger(__name__)

# Buses already carrying the handler, so repeated app/startup wiring in the same
# process (e.g. one TestClient per test) never stacks duplicate subscriptions.
_registered: set[int] = set()


def register_auto_analysis(bus: EventBus) -> Callable[[], None]:
    """Subscribe the auto-derivation handler to ``bus`` (idempotent per bus)."""

    if id(bus) in _registered:
        return lambda: None

    def _on_event(event: DomainEvent) -> None:
        if event.type is not EventType.TRANSCRIPT_SEGMENT_FINALIZED:
            return
        if not get_settings().auto_analyze:
            return
        segment_id = event.payload.get("id")
        if not segment_id:
            return
        try:
            with SessionLocal() as db:
                repo = SqlAlchemySessionRepository(db)
                artifacts = ArtifactService(repo, bus)
                analysis = AnalysisService(repo, artifacts, get_llm_provider())
                produced = analysis.analyze_segment(str(segment_id), event.session_id)
            logger.info(
                "auto_analysis.derived",
                session_id=event.session_id,
                segment_id=segment_id,
                artifacts=len(produced),
            )
        except Exception:  # noqa: BLE001 - never let derivation break ingestion
            logger.exception(
                "auto_analysis.failed", session_id=event.session_id, segment_id=segment_id
            )

    unsubscribe = bus.subscribe_sync(_on_event)
    _registered.add(id(bus))

    def _unregister() -> None:
        unsubscribe()
        _registered.discard(id(bus))

    return _unregister
