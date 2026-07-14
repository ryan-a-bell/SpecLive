"""Mock provider implementations.

Deterministic, offline, and keyless. The LLM mock is a keyword heuristic that
recognizes the warehouse/field-operations discovery domain used by the seed
scenario, so the app demonstrates end-to-end derivation without a real model.
"""

from __future__ import annotations

import hashlib
import re

from app.providers.base import (
    ArtifactCandidate,
    TranscriptChunk,
)

# (regex, artifact_type, title, statement_template, confidence, relationship)
_RULES: list[tuple[str, str, str, str, float, str]] = [
    (
        r"real[- ]?time|visibility|see .*status|where .*orders",
        "stakeholder_need",
        "Timely operational visibility",
        "Stakeholders need timely visibility into operational status: {quote}",
        0.82,
        "direct",
    ),
    (
        r"within (\d+)\s*(second|sec|minute|min)|refresh|update .*(fast|quick)|latency",
        "requirement",
        "Status refresh latency target",
        "The solution shall refresh status information within the stated interval: {quote}",
        0.9,
        "direct",
    ),
    (
        r"tablet|rugged|device|hardware|mobile",
        "constraint",
        "Existing field device constraint",
        "The solution shall operate on existing field devices: {quote}",
        0.85,
        "direct",
    ),
    (
        r"cannot replace|keep .*(system|wms)|existing (wms|system)|integrate with",
        "constraint",
        "Retain existing system constraint",
        "The solution shall integrate with the existing system without replacing it: {quote}",
        0.88,
        "direct",
    ),
    (
        r"offline|intermittent|degraded|connectivity|disconnect|no signal",
        "requirement",
        "Degraded-connectivity operation",
        "The solution shall support operation during degraded connectivity: {quote}",
        0.7,
        "direct",
    ),
    (
        r"sync|synchroniz|reconcile|conflict",
        "requirement",
        "Data synchronization behavior",
        "The solution shall synchronize data after reconnection: {quote}",
        0.68,
        "supporting",
    ),
    (
        r"role|permission|access control|who can|authoriz",
        "requirement",
        "Role-based access",
        "The solution shall enforce role-based access: {quote}",
        0.72,
        "direct",
    ),
    (
        r"deadline|by (q[1-4]|end of|the)|go[- ]live|deploy .*(date|by)|launch",
        "constraint",
        "Deployment deadline",
        "The solution shall be deployed by the stated deadline: {quote}",
        0.8,
        "direct",
    ),
    (
        r"measure|success|kpi|metric|how .*know .*success",
        "success_metric",
        "Success measure",
        "Success will be measured as described: {quote}",
        0.66,
        "supporting",
    ),
]

_QUESTION_RE = re.compile(r"\?\s*$")


class MockSpeechToTextProvider:
    async def transcribe(self, audio_ref: str) -> list[TranscriptChunk]:
        # A real STT provider would stream audio; the mock echoes a canned line.
        return [
            TranscriptChunk(
                speaker="Customer",
                text=f"(transcribed audio {audio_ref})",
                start_time=0.0,
                end_time=1.0,
            )
        ]


class MockLanguageModelProvider:
    async def extract_artifacts(
        self, segment_text: str, speaker: str, context: str = ""
    ) -> list[ArtifactCandidate]:
        # Interviewer/facilitator lines are questions, not customer sources.
        if speaker.lower() not in {"customer", "cm"} or _QUESTION_RE.search(segment_text.strip()):
            return []

        candidates: list[ArtifactCandidate] = []
        lowered = segment_text.lower()
        for pattern, atype, title, template, confidence, rel in _RULES:
            match = re.search(pattern, lowered)
            if not match:
                continue
            quote = self._extract_quote(segment_text, match.start(), match.end())
            start = segment_text.lower().find(quote.lower())
            candidates.append(
                ArtifactCandidate(
                    artifact_type=atype,
                    title=title,
                    statement=template.format(quote=quote),
                    confidence=confidence,
                    rationale=f"Heuristic match on pattern '{pattern.split('|')[0]}'.",
                    quote=quote,
                    quote_start=max(start, 0),
                    quote_end=max(start, 0) + len(quote),
                    relationship=rel,
                )
            )
        return candidates

    async def recommend_question(self, gaps: list[str], stage_prompt: str) -> str:
        if gaps:
            return f"To close a gap: {gaps[0]}"
        return stage_prompt

    @staticmethod
    def _extract_quote(text: str, start: int, end: int) -> str:
        """Widen a regex match to the surrounding sentence-ish clause."""
        left = text.rfind(".", 0, start)
        left = 0 if left == -1 else left + 1
        right = text.find(".", end)
        right = len(text) if right == -1 else right
        return text[left:right].strip()


class MockEmbeddingProvider:
    async def embed(self, text: str) -> list[float]:
        # Deterministic pseudo-embedding from a hash; enough for tests/dedup.
        digest = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in digest[:16]]
