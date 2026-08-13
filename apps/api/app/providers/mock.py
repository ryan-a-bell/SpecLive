"""Mock provider implementations.

These make the whole system runnable with no API keys. The mock language model
uses transparent, deterministic keyword/regex heuristics — it is emphatically
NOT a real model, and its confidence values are illustrative. Crucially, it only
ever proposes artifacts in `detected`/`inferred`; it never confirms anything.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import AsyncIterator

from ..domain.enums import ArtifactType, DerivationMethod, EvidenceRelationship
from .base import (
    ArtifactCandidate,
    EmbeddingProvider,
    EvidenceCandidate,
    LanguageModelProvider,
    SpeechToTextProvider,
    TranscriptChunk,
)

# (regex, artifact_type, title, statement_template, base_confidence, relationship)
_RULES: list[tuple[re.Pattern[str], ArtifactType, str, str, float, EvidenceRelationship]] = [
    (
        re.compile(r"within\s+(\d+)\s*(second|minute|hour)s?", re.I),
        ArtifactType.REQUIREMENT,
        "Quantified freshness target",
        "The solution shall refresh information within {match} of a source-system change.",
        0.9,
        EvidenceRelationship.DIRECT,
    ),
    (
        re.compile(r"(real[- ]?time|real time|live) (view|visibility|status|update)", re.I),
        ArtifactType.STAKEHOLDER_NEED,
        "Timely operational visibility",
        "Stakeholders need timely, real-time visibility into operational status.",
        0.8,
        EvidenceRelationship.SUPPORTING,
    ),
    (
        re.compile(r"(cannot|can't|can not|unable to) (replace|change|migrate)", re.I),
        ArtifactType.CONSTRAINT,
        "System retention constraint",
        "The solution shall integrate with the existing system without replacing it.",
        0.85,
        EvidenceRelationship.DIRECT,
    ),
    (
        re.compile(r"(rugged )?tablet|handheld|mobile device|scanner", re.I),
        ArtifactType.CONSTRAINT,
        "Existing field hardware",
        "The solution shall operate on the existing field devices already issued to staff.",
        0.8,
        EvidenceRelationship.DIRECT,
    ),
    (
        re.compile(r"(offline|intermittent|degraded|no connectivity|lose connection)", re.I),
        ArtifactType.OPEN_QUESTION,
        "Degraded-connectivity behavior",
        "Which functions must remain available during degraded connectivity, and for how long?",
        0.6,
        EvidenceRelationship.CONTEXTUAL,
    ),
    (
        re.compile(r"(deadline|by (q[1-4]|end of|next)|go[- ]?live|deploy(ment)? by)", re.I),
        ArtifactType.CONSTRAINT,
        "Deployment timeline constraint",
        "The solution shall be delivered within the stated deployment deadline.",
        0.75,
        EvidenceRelationship.DIRECT,
    ),
    (
        re.compile(r"(role|permission|access control|who can|only .* can)", re.I),
        ArtifactType.REQUIREMENT,
        "Role-based access",
        "The solution shall restrict actions based on the user's role.",
        0.7,
        EvidenceRelationship.SUPPORTING,
    ),
    (
        re.compile(r"(integrat|api|feed|export|WMS|ERP|sync)", re.I),
        ArtifactType.INTEGRATION,
        "Source-system integration",
        "The solution shall integrate with the identified source system(s).",
        0.65,
        EvidenceRelationship.SUPPORTING,
    ),
    (
        re.compile(r"(measure|success|kpi|metric|percent|accuracy|throughput)", re.I),
        ArtifactType.SUCCESS_METRIC,
        "Success measure",
        "Success shall be measured by the stated operational metric.",
        0.6,
        EvidenceRelationship.SUPPORTING,
    ),
]


class MockLanguageModelProvider(LanguageModelProvider):
    """Deterministic keyword/regex derivation."""

    def analyze_segment(self, text: str, *, speaker: str) -> list[ArtifactCandidate]:
        # Only customer statements yield candidate needs/requirements; facilitator
        # turns are questions and don't create artifacts (matches the prototype).
        if speaker == "facilitator":
            return []

        candidates: list[ArtifactCandidate] = []
        for pattern, atype, title, statement_tpl, conf, rel in _RULES:
            match = pattern.search(text)
            if not match:
                continue
            quote_start, quote_end = match.span()
            quoted = text[quote_start:quote_end]
            statement = statement_tpl.format(match=match.group(0))
            candidates.append(
                ArtifactCandidate(
                    artifact_type=atype,
                    title=title,
                    statement=statement,
                    confidence=self._jitter(conf, quoted),
                    rationale=(
                        f"Heuristic rule matched '{quoted}'. Requires human review before "
                        "confirmation."
                    ),
                    derivation_method=DerivationMethod.KEYWORD_HEURISTIC,
                    evidence=[
                        EvidenceCandidate(
                            quote_start=quote_start,
                            quote_end=quote_end,
                            quoted_text=quoted,
                            relationship=rel,
                            confidence=conf,
                            rationale=f"Span matched the '{title}' rule.",
                        )
                    ],
                )
            )
        return candidates

    def recommend_questions(self, context: str, *, gaps: list[str]) -> list[str]:
        base = [
            "Which specific states and exceptions must the user see to act in time?",
            "What make, model, and OS are the field devices?",
            "What APIs, exports, or event feeds does the source system expose?",
            "Which functions must continue during intermittent connectivity, and for how long?",
        ]
        # Deterministically prioritize by gap keywords present.
        return base[: max(1, min(len(base), len(gaps) + 1))]

    @staticmethod
    def _jitter(base: float, seed_text: str) -> float:
        """Deterministic small perturbation so demo confidences aren't identical."""

        h = int(hashlib.sha256(seed_text.encode()).hexdigest(), 16) % 8
        return round(min(0.98, base + (h - 4) / 100.0), 2)


class MockSpeechToTextProvider(SpeechToTextProvider):
    """Replays a canned transcript as a stream. Real STT replaces only this."""

    def __init__(self, chunks: list[TranscriptChunk] | None = None) -> None:
        self._chunks = chunks or []

    async def stream(self, session_id: str) -> AsyncIterator[TranscriptChunk]:
        for chunk in self._chunks:
            yield chunk


class MockEmbeddingProvider(EmbeddingProvider):
    """Cheap, deterministic hash-based embeddings for clustering demos."""

    DIM = 16

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vectors.append([digest[i % len(digest)] / 255.0 for i in range(self.DIM)])
        return vectors
