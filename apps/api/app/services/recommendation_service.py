"""Recommended next questions + active gaps, derived from discovery-tree gaps."""

from __future__ import annotations

from typing import Any

from ..domain.enums import ArtifactType, ValidationState
from ..providers.base import LanguageModelProvider
from ..repositories import SessionRepository
from ..repositories.mappers import artifact_to_domain


class RecommendationService:
    def __init__(self, repo: SessionRepository, llm: LanguageModelProvider) -> None:
        self._repo = repo
        self._llm = llm

    def recommend(self, session_id: str) -> dict[str, Any]:
        artifacts = [artifact_to_domain(r) for r in self._repo.list_artifacts(session_id)]
        evidence = self._repo.list_evidence(session_id)
        ev_artifact_ids = {link.artifact_id for link in evidence}

        gaps: list[dict[str, str]] = []
        # Open questions are explicit gaps.
        for a in artifacts:
            if a.artifact_type == ArtifactType.OPEN_QUESTION and a.validation_state not in (
                ValidationState.REJECTED,
                ValidationState.MERGED,
            ):
                gaps.append({"title": a.title, "body": a.statement})
        # Low-confidence or evidence-less requirements/constraints are soft gaps.
        for a in artifacts:
            if a.artifact_type in (ArtifactType.REQUIREMENT, ArtifactType.CONSTRAINT):
                if a.id not in ev_artifact_ids:
                    gaps.append(
                        {
                            "title": f"{a.title} lacks supporting evidence",
                            "body": "No transcript evidence is linked yet.",
                        }
                    )
                elif a.confidence < 0.75:
                    gaps.append(
                        {
                            "title": f"{a.title} is low-confidence",
                            "body": f"Confidence {a.confidence:.0%}; needs a clarifying question.",
                        }
                    )

        gap_titles = [g["title"] for g in gaps]
        questions = self._llm.recommend_questions("", gaps=gap_titles)
        ranked = [
            {"rank": i + 1, "question": q, "why": self._why(i, gaps)}
            for i, q in enumerate(questions)
        ]
        return {"session_id": session_id, "questions": ranked, "gaps": gaps[:6]}

    @staticmethod
    def _why(index: int, gaps: list[dict[str, str]]) -> str:
        if index < len(gaps):
            return f"Addresses gap: {gaps[index]['title']}"
        return "Strengthens overall discovery coverage."
