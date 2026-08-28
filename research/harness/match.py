"""Align derived artifacts to gold artifacts. Pluggable matchers, one interface:

    matcher.match(derived, gold, evidence_by_artifact, threshold) -> list[Pair]

Matching is kept *independent of evidence-target agreement* — a right-idea /
wrong-citation artifact still counts as recalled, and its citation is graded on
its own in ``score.py`` (``cites_correct_turn`` compares which turn was cited,
which no matcher here looks at). The matchers do fold each derived artifact's
own evidence *quote text* into the compared text: the quote is verbatim
transcript, so it is a fair, non-circular signal of what the artifact is about
(it says nothing about whether the citation points at the right turn).

* ``lexical`` (default) — token Jaccard + gold key-phrase hits. Deterministic,
  no model. Conservative: it under-matches conceptually-correct artifacts whose
  wording diverges from gold (e.g. a templated "existing field devices" vs gold
  "rugged tablets"), which is exactly what the embedding matcher is for.
* ``embedding`` — cosine similarity over an ``EmbeddingProvider``. With a real
  embedding provider it tolerates paraphrase; with the mock (hash) provider it
  runs but is not semantically meaningful (smoke path only).
"""

from __future__ import annotations

import abc
import math
import re
from dataclasses import dataclass

_STOP = {
    "the", "a", "an", "of", "to", "and", "or", "for", "in", "on", "at", "is",
    "are", "be", "shall", "must", "we", "our", "it", "that", "this", "with",
    "as", "by", "so", "can", "will", "which", "solution", "system", "stated",
    "need", "needs", "should", "would", "have", "has",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _keyphrase_hits(phrases: list[str], haystack: str) -> float:
    if not phrases:
        return 0.0
    low = haystack.lower()
    return sum(1 for p in phrases if p.lower() in low) / len(phrases)


@dataclass
class Pair:
    gold_id: str
    derived_index: int
    score: float
    type_match: bool


def _derived_text(derived, ev_quotes: list[str]) -> str:
    return f"{derived.title} {derived.statement} {' '.join(ev_quotes)}"


def _gold_text(gold: dict) -> str:
    return f"{gold['canonical_statement']} {' '.join(gold.get('key_phrases', []))}"


def _greedy(candidates: list[Pair]) -> list[Pair]:
    candidates.sort(key=lambda p: p.score, reverse=True)
    used_gold: set[str] = set()
    used_derived: set[int] = set()
    pairs: list[Pair] = []
    for p in candidates:
        if p.gold_id in used_gold or p.derived_index in used_derived:
            continue
        used_gold.add(p.gold_id)
        used_derived.add(p.derived_index)
        pairs.append(p)
    return pairs


class Matcher(abc.ABC):
    @abc.abstractmethod
    def _similarity(self, derived, ev_quotes: list[str], gold: dict) -> float: ...

    def match(
        self,
        derived: list,
        gold: list[dict],
        evidence_by_artifact: dict[str, list] | None = None,
        *,
        threshold: float = 0.30,
    ) -> list[Pair]:
        ev = evidence_by_artifact or {}
        candidates: list[Pair] = []
        for gi, g in enumerate(gold):
            for di, d in enumerate(derived):
                quotes = [l.quoted_text for l in ev.get(d.id, []) if l.quoted_text]
                sim = self._similarity(d, quotes, g)
                if sim >= threshold:
                    tmatch = d.artifact_type.value == g["artifact_type"]
                    candidates.append(Pair(g["id"], di, round(sim, 3), tmatch))
        return _greedy(candidates)


class LexicalMatcher(Matcher):
    def _similarity(self, derived, ev_quotes: list[str], gold: dict) -> float:
        dtext = _derived_text(derived, ev_quotes)
        jac = _jaccard(_tokens(dtext), _tokens(_gold_text(gold)))
        kp = _keyphrase_hits(gold.get("key_phrases", []), dtext)
        return 0.6 * jac + 0.4 * kp


class EmbeddingMatcher(Matcher):
    """Cosine similarity via an EmbeddingProvider. Embeddings are cached per
    text so each unique string is embedded once."""

    def __init__(self, embedder) -> None:
        self._embedder = embedder
        self._cache: dict[str, list[float]] = {}

    def _embed(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self._embedder.embed([text])[0]
        return self._cache[text]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    def _similarity(self, derived, ev_quotes: list[str], gold: dict) -> float:
        return self._cosine(
            self._embed(_derived_text(derived, ev_quotes)),
            self._embed(_gold_text(gold)),
        )


def get_matcher(name: str, *, embedder=None) -> Matcher:
    if name == "lexical":
        return LexicalMatcher()
    if name == "embedding":
        if embedder is None:
            raise ValueError("embedding matcher requires an EmbeddingProvider")
        return EmbeddingMatcher(embedder)
    raise ValueError(f"Unknown matcher {name!r} (expected 'lexical' or 'embedding')")


# Back-compat helper used by ad-hoc scripts/tests.
def match(derived, gold, evidence_by_artifact=None, *, threshold: float = 0.30):
    return LexicalMatcher().match(derived, gold, evidence_by_artifact, threshold=threshold)


def score_pair(derived, gold: dict, ev_quotes: list[str] | None = None):
    """Convenience for debugging: lexical (similarity, type_match) for one pair."""
    m = LexicalMatcher()
    sim = m._similarity(derived, ev_quotes or [], gold)
    return sim, derived.artifact_type.value == gold["artifact_type"]
