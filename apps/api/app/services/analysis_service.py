"""Turns transcript segments into candidate artifacts + evidence via the LLM
provider. All artifacts produced here are proposals (detected/inferred) — never
confirmed.

How much surrounding transcript a given call sees is decided by a pluggable
``ContextStrategy`` (see ``context_strategy.py``): per-segment (no context),
sliding time window, or the full session. The strategy only decides how
segments are grouped into an ``AnalysisUnit``; this service is agnostic to
which mode is active, and works the same way against any provider.
"""

from __future__ import annotations

from ..domain import entities as e
from ..domain.enums import DerivationMethod, ValidationState
from ..providers.base import AnalysisUnit, LanguageModelProvider
from ..repositories import SessionRepository
from ..repositories.mappers import segment_to_domain
from .artifact_service import ArtifactService
from .context_strategy import ContextStrategy, PerSegmentStrategy
from .errors import NotFoundError


class AnalysisService:
    def __init__(
        self,
        repo: SessionRepository,
        artifact_service: ArtifactService,
        llm: LanguageModelProvider,
        context_strategy: ContextStrategy | None = None,
    ) -> None:
        self._repo = repo
        self._artifacts = artifact_service
        self._llm = llm
        # Default matches the original, always-available behavior: each
        # segment analyzed alone, no context strategy configured.
        self._context_strategy = context_strategy or PerSegmentStrategy()

    def analyze_segment(self, segment_id: str, session_id: str) -> list[e.DiscoveryArtifact]:
        """Analyze a single segment (by id) and persist candidate artifacts.

        This bypasses the configured context strategy on purpose — it's an
        explicit request to (re)analyze one segment, so it always builds a
        single-segment unit regardless of ``ANALYSIS_CONTEXT_MODE``.
        """

        row = next(
            (s for s in self._repo.list_segments(session_id) if s.id == segment_id), None
        )
        if row is None:
            raise NotFoundError(f"Segment {segment_id} not found in session {session_id}")
        return self._run(session_id, AnalysisUnit(segments=[segment_to_domain(row)]))

    def analyze_session(self, session_id: str) -> list[e.DiscoveryArtifact]:
        """(Re)analyze the whole session using the configured context
        strategy. Idempotency is out of scope for the MVP mock; callers
        typically run this once on demand."""

        if self._repo.get_session(session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")
        segments = [segment_to_domain(row) for row in self._repo.list_segments(session_id)]
        produced: list[e.DiscoveryArtifact] = []
        for unit in self._context_strategy.build_units(segments):
            produced.extend(self._run(session_id, unit))
        return produced

    def _run(self, session_id: str, unit: AnalysisUnit) -> list[e.DiscoveryArtifact]:
        candidates = self._llm.analyze_unit(unit)
        segments_by_id = {segment.id: segment for segment in unit.segments}
        produced: list[e.DiscoveryArtifact] = []
        for cand in candidates:
            artifact = self._artifacts.create(
                session_id,
                artifact_type=cand.artifact_type,
                title=cand.title,
                statement=cand.statement,
                confidence=cand.confidence,
                rationale=cand.rationale,
                validation_state=ValidationState.INFERRED,
                derivation_method=cand.derivation_method or DerivationMethod.KEYWORD_HEURISTIC,
                actor_is_human=False,  # enforces: cannot confirm/baseline automatically
            )
            for ev in cand.evidence:
                # A multi-segment unit's evidence should name which segment it
                # came from; fall back to the unit's anchor for providers that
                # only ever see one segment (matches the pre-unit behavior).
                segment = segments_by_id.get(ev.segment_id or "", unit.anchor)
                self._artifacts.add_evidence(
                    artifact.id,
                    transcript_segment_id=segment.id,
                    quote_start=ev.quote_start,
                    quote_end=ev.quote_end,
                    quoted_text=ev.quoted_text,
                    relationship=ev.relationship,
                    confidence=ev.confidence,
                    rationale=ev.rationale,
                )
            produced.append(self._artifacts.get(artifact.id))
        return produced
