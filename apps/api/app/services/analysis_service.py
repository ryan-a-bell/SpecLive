"""Turns transcript segments into candidate artifacts + evidence via the LLM
provider. All artifacts produced here are proposals (detected/inferred) — never
confirmed.
"""

from __future__ import annotations

from ..domain import entities as e
from ..domain.enums import DerivationMethod, ValidationState
from ..providers.base import LanguageModelProvider
from ..repositories import SessionRepository
from .artifact_service import ArtifactService
from .errors import NotFoundError


class AnalysisService:
    def __init__(
        self,
        repo: SessionRepository,
        artifact_service: ArtifactService,
        llm: LanguageModelProvider,
    ) -> None:
        self._repo = repo
        self._artifacts = artifact_service
        self._llm = llm

    def analyze_segment(self, segment_id: str, session_id: str) -> list[e.DiscoveryArtifact]:
        """Analyze a single segment (by id) and persist candidate artifacts."""

        segment = next(
            (s for s in self._repo.list_segments(session_id) if s.id == segment_id), None
        )
        if segment is None:
            raise NotFoundError(f"Segment {segment_id} not found in session {session_id}")
        return self._analyze(session_id, segment)

    def analyze_session(self, session_id: str) -> list[e.DiscoveryArtifact]:
        """(Re)analyze every segment in the session. Idempotency is out of scope
        for the MVP mock; callers typically run this once on demand."""

        if self._repo.get_session(session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")
        produced: list[e.DiscoveryArtifact] = []
        for segment in self._repo.list_segments(session_id):
            produced.extend(self._analyze(session_id, segment))
        return produced

    def _analyze(self, session_id: str, segment) -> list[e.DiscoveryArtifact]:  # type: ignore[no-untyped-def]
        candidates = self._llm.analyze_segment(segment.text, speaker=segment.speaker)
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
