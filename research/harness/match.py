"""Align derived artifacts to gold artifacts.

v1 is a transparent lexical matcher (token Jaccard + gold key-phrase hits). It
is deliberately simple and matching is kept *independent* of evidence quality —
evidence fidelity is scored separately in ``score.py`` — so a right-idea /
wrong-citation artifact still counts as recalled and its citation is graded on
its own. Swap in an embedding or LLM-judge matcher later without touching the
metrics; the interface is just ``match(derived, gold) -> list[Pair]``.
"""

from __future__ import annotations

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
    hit = sum(1 for p in phrases if p.lower() in low)
    return hit / len(phrases)


@dataclass
class Pair:
    gold_id: str
    derived_index: int
    score: float
    type_match: bool


def score_pair(derived, gold: dict) -> tuple[float, bool]:
    """Return (similarity 0-1, type_match) for one derived/gold candidate."""
    dtext = f"{derived.title} {derived.statement}"
    gtext = f"{gold['canonical_statement']} {' '.join(gold.get('key_phrases', []))}"
    jac = _jaccard(_tokens(dtext), _tokens(gtext))
    kp = _keyphrase_hits(gold.get("key_phrases", []), dtext)
    sim = 0.6 * jac + 0.4 * kp
    type_match = derived.artifact_type.value == gold["artifact_type"]
    return sim, type_match


def match(derived: list, gold: list[dict], *, threshold: float = 0.30) -> list[Pair]:
    """Greedy one-to-one alignment: strongest pairs first, each side used once."""
    candidates: list[Pair] = []
    for gi, g in enumerate(gold):
        for di, d in enumerate(derived):
            sim, tmatch = score_pair(d, g)
            if sim >= threshold:
                candidates.append(Pair(g["id"], di, round(sim, 3), tmatch))

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
