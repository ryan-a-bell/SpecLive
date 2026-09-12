"""Turn a completed derivation run into tabular views for analysis.

This is the *backend* to the SpecLive inference UI: given the artifacts the
real ``AnalysisService`` derived from a transcript (plus their evidence links
and the ordered segments), it produces flat ``pandas`` DataFrames you can slice,
score, and visualize — the same "what was inferred, from which words, with what
confidence, and how do the inferences relate" view the web app renders, but as
data.

Three views, all built from the same run:

- :func:`build_ledger`          one row per *derived artifact* (the inference).
- :func:`build_segment_coverage`one row per *transcript segment* (what's
                                inferred vs. not).
- :func:`detect_dependencies`   cross-artifact edges: reinforcement vs. conflict.

Nothing here re-derives anything — it only reshapes what the pipeline produced,
so the numbers stay faithful to the real methodology. Column definitions live in
the module-level constants so the notebook and any future exporter agree on the
schema.

Only ``pandas`` and the stdlib are imported at module load, so this is safe to
import from the harness without pulling in heavier viz deps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations

import pandas as pd

# --- schema (single source of truth for the column contract) --------------

#: EvidenceRelationship values, bucketed into the user-facing "dependency" idea.
#: reinforcement = "you said this and it backs up the same idea";
#: conflict      = "you said this but it cuts against / replaces the other".
REINFORCING_RELATIONSHIPS = {"direct", "supporting", "contextual"}
CONFLICTING_RELATIONSHIPS = {"contradicting", "superseding"}

LEDGER_COLUMNS = [
    # run identity
    "case", "provider", "strategy",
    # what it is
    "artifact_id", "artifact_type", "title", "statement",
    # how sure / how derived / where in its lifecycle
    "confidence", "derivation_method", "validation_state", "status",
    # where in the transcript it came from  ("time" + "which portion of text")
    "evidence_count", "segment_seq", "start_time", "end_time",
    "speaker", "speaker_name", "evidence_quote", "evidence_relationship",
    "segment_text",
    # cross-artifact links  (filled by attach_dependencies)
    "depends_on", "dependency_kind",
    # optional evaluation against gold  (filled by attach_gold)
    "matched_gold_id", "gold_type", "correct_type", "quote_grounded",
]

SEGMENT_COLUMNS = [
    "segment_seq", "start_time", "end_time", "speaker", "speaker_name", "text",
    # what the LLM actually saw for this segment (depends on the context strategy)
    "context",
    # what came back, per segment (parallel lists, one entry per artifact)
    "inferred", "requirements", "inferred_types", "confidences",
    "artifact_count", "artifact_ids", "max_confidence",
]

DEPENDENCY_COLUMNS = [
    "source_id", "target_id", "kind", "score", "basis",
    "source_type", "target_type", "source_title", "target_title",
]


# --- tokenization (kept identical in spirit to the lexical matcher) --------

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --- ledger: one row per derived artifact ----------------------------------

def build_ledger(
    *,
    case: str,
    provider: str,
    strategy: str,
    derived: list,
    evidence_by_artifact: dict[str, list],
    segments: list,
) -> pd.DataFrame:
    """One row per inferred artifact, traced back to the transcript span it
    was derived from.

    ``segments`` is the turn-ordered segment list from ``ingest.ingest`` (so
    ``segments[i]`` is turn ``i``); it is used to resolve each artifact's
    strongest evidence link to a time, speaker, and the full segment text.
    """
    by_id = {s.id: (i, s) for i, s in enumerate(segments)}
    rows: list[dict] = []
    for a in derived:
        links = evidence_by_artifact.get(a.id, [])
        primary = max(links, key=lambda l: l.confidence, default=None)
        seg_seq = start = end = speaker = speaker_name = None
        quote = seg_text = relationship = None
        if primary is not None:
            relationship = primary.relationship.value
            quote = primary.quoted_text
            hit = by_id.get(primary.transcript_segment_id)
            if hit is not None:
                seg_seq, seg = hit
                start, end = seg.start_time, seg.end_time
                speaker = seg.speaker.value
                speaker_name = seg.speaker_name
                seg_text = seg.text
        rows.append(
            {
                "case": case,
                "provider": provider,
                "strategy": strategy,
                "artifact_id": a.id,
                "artifact_type": a.artifact_type.value,
                "title": a.title,
                "statement": a.statement,
                "confidence": round(float(a.confidence), 3),
                "derivation_method": a.derivation_method.value,
                "validation_state": a.validation_state.value,
                "status": a.status.value,
                "evidence_count": len(links),
                "segment_seq": seg_seq,
                "start_time": start,
                "end_time": end,
                "speaker": speaker,
                "speaker_name": speaker_name,
                "evidence_quote": quote,
                "evidence_relationship": relationship,
                "segment_text": seg_text,
                "depends_on": [],
                "dependency_kind": None,
                "matched_gold_id": None,
                "gold_type": None,
                "correct_type": None,
                "quote_grounded": None,
            }
        )
    df = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    return df.sort_values(["segment_seq", "confidence"], ascending=[True, False],
                          na_position="last").reset_index(drop=True)


# --- segment coverage: one row per transcript turn -------------------------

def build_context_map(segments: list, context_strategy) -> dict[int, str]:
    """For each segment index, the exact text the LLM saw for it — i.e. the
    joined text of the :class:`AnalysisUnit` the given ``ContextStrategy`` puts
    that segment into.

    With ``segment`` the context is just that turn; with ``window`` it's the
    window; with ``full`` it's the whole transcript. This is the "chunk /
    context that was passed to the LLM" column.
    """
    seg_index = {s.id: i for i, s in enumerate(segments)}
    ctx: dict[int, str] = {}
    for unit in context_strategy.build_units(segments):
        unit_text = "\n".join(
            f"{(s.speaker_name or s.speaker.value)}: {s.text}" for s in unit.segments
        )
        for s in unit.segments:
            ctx[seg_index[s.id]] = unit_text
    return ctx


def build_segment_coverage(
    *,
    derived: list,
    evidence_by_artifact: dict[str, list],
    segments: list,
    context_strategy=None,
) -> pd.DataFrame:
    """One row per transcript segment: what the LLM saw (``context``) and what
    it inferred from that segment (parallel ``requirements`` / ``inferred_types``
    / ``confidences`` lists) — the "what's inferred, what's not" view.

    Pass ``context_strategy`` (from ``get_context_strategy``) to fill the
    ``context`` column with the actual unit text; omit it and ``context`` is the
    segment's own text.
    """
    seg_index = {s.id: i for i, s in enumerate(segments)}
    hits: dict[int, list] = {i: [] for i in range(len(segments))}
    for a in derived:
        cited = {seg_index[l.transcript_segment_id]
                 for l in evidence_by_artifact.get(a.id, [])
                 if l.transcript_segment_id in seg_index}
        for i in cited:
            hits[i].append(a)

    context = (build_context_map(segments, context_strategy)
               if context_strategy is not None else None)

    rows = []
    for i, seg in enumerate(segments):
        arts = sorted(hits[i], key=lambda a: float(a.confidence), reverse=True)
        rows.append(
            {
                "segment_seq": i,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "speaker": seg.speaker.value,
                "speaker_name": seg.speaker_name,
                "text": seg.text,
                "context": context[i] if context is not None else seg.text,
                "inferred": bool(arts),
                "requirements": [a.statement for a in arts],
                "inferred_types": [a.artifact_type.value for a in arts],
                "confidences": [round(float(a.confidence), 3) for a in arts],
                "artifact_count": len(arts),
                "artifact_ids": [a.id for a in arts],
                "max_confidence": round(max((float(a.confidence) for a in arts),
                                            default=0.0), 3),
            }
        )
    return pd.DataFrame(rows, columns=SEGMENT_COLUMNS)


# --- cross-artifact dependencies: reinforcement vs. conflict ----------------

@dataclass
class _ArtView:
    id: str
    type: str
    title: str
    statement: str
    superseded_by: str | None
    segments: set[str]
    conflict_relationship: bool  # any contradicting/superseding evidence link


def detect_dependencies(
    *,
    derived: list,
    evidence_by_artifact: dict[str, list],
    sim_reinforce: float = 0.45,
    sim_relate: float = 0.25,
) -> pd.DataFrame:
    """Infer artifact→artifact links and label each reinforcement / conflict /
    related.

    v1 heuristic — deliberately transparent, no model call:

    * **conflict**  — one artifact supersedes the other (``superseded_by``), OR
      either carries a contradicting/superseding evidence link AND the two are
      about the same thing (lexical overlap ≥ ``sim_relate``).
    * **reinforcement** — same ``artifact_type`` and statement overlap ≥
      ``sim_reinforce`` (the same idea, said more than once / corroborated).
    * **related** — overlap ≥ ``sim_relate`` or a shared evidence segment, but
      below the reinforcement bar (adjacent topic / shared context).

    Detecting true semantic conflict (e.g. negation flips) is itself an
    inference task; this gives an honest first cut that SpecLive's backend can
    later replace with a model pass. Edges are undirected pairs, emitted once.
    """
    views: list[_ArtView] = []
    for a in derived:
        links = evidence_by_artifact.get(a.id, [])
        views.append(
            _ArtView(
                id=a.id,
                type=a.artifact_type.value,
                title=a.title,
                statement=a.statement,
                superseded_by=getattr(a, "superseded_by", None),
                segments={l.transcript_segment_id for l in links},
                conflict_relationship=any(
                    l.relationship.value in CONFLICTING_RELATIONSHIPS for l in links
                ),
            )
        )
    toks = {v.id: _tokens(f"{v.title} {v.statement}") for v in views}

    rows = []
    for x, y in combinations(views, 2):
        sim = _jaccard(toks[x.id], toks[y.id])
        shares_segment = bool(x.segments & y.segments)
        supersedes = x.superseded_by == y.id or y.superseded_by == x.id
        kind = basis = None
        if supersedes:
            kind, basis = "conflict", "supersession"
        elif (x.conflict_relationship or y.conflict_relationship) and sim >= sim_relate:
            kind, basis = "conflict", "contradicting_evidence"
        elif x.type == y.type and sim >= sim_reinforce:
            kind, basis = "reinforcement", f"same_type+similarity={sim:.2f}"
        elif sim >= sim_relate or shares_segment:
            kind = "related"
            basis = ("shared_segment" if shares_segment and sim < sim_relate
                     else f"similarity={sim:.2f}")
        if kind is None:
            continue
        rows.append(
            {
                "source_id": x.id, "target_id": y.id, "kind": kind,
                "score": round(sim, 3), "basis": basis,
                "source_type": x.type, "target_type": y.type,
                "source_title": x.title, "target_title": y.title,
            }
        )
    return pd.DataFrame(rows, columns=DEPENDENCY_COLUMNS)


def attach_dependencies(ledger: pd.DataFrame, deps: pd.DataFrame) -> pd.DataFrame:
    """Fold the dependency edges back into the ledger's ``depends_on`` /
    ``dependency_kind`` columns (conflict wins over reinforcement over related
    when an artifact has several)."""
    _rank = {"conflict": 3, "reinforcement": 2, "related": 1}
    neighbors: dict[str, list[str]] = {aid: [] for aid in ledger["artifact_id"]}
    best: dict[str, str] = {}
    for _, e in deps.iterrows():
        for a, b in ((e.source_id, e.target_id), (e.target_id, e.source_id)):
            neighbors.setdefault(a, []).append(b)
            if _rank.get(e.kind, 0) > _rank.get(best.get(a, ""), 0):
                best[a] = e.kind
    out = ledger.copy()
    out["depends_on"] = out["artifact_id"].map(lambda i: neighbors.get(i, []))
    out["dependency_kind"] = out["artifact_id"].map(lambda i: best.get(i))
    return out


# --- optional: fold in gold matches (evaluation columns) -------------------

def attach_gold(
    ledger: pd.DataFrame,
    *,
    derived: list,
    gold: list[dict],
    pairs: list,
    evidence_by_artifact: dict[str, list],
) -> pd.DataFrame:
    """Fill ``matched_gold_id`` / ``gold_type`` / ``correct_type`` /
    ``quote_grounded`` from a matcher's ``Pair`` list, when a gold file exists.

    ``quote_grounded`` mirrors the harness's traceability metric: is the cited
    quote a verbatim substring of the gold-expected segment's phrasing.
    """
    gold_by_id = {g["id"]: g for g in gold}
    by_derived_index = {p.derived_index: p for p in pairs}
    id_by_index = {i: a.id for i, a in enumerate(derived)}

    matched_gold: dict[str, str] = {}
    correct_type: dict[str, bool] = {}
    for di, p in by_derived_index.items():
        aid = id_by_index[di]
        matched_gold[aid] = p.gold_id
        correct_type[aid] = p.type_match

    out = ledger.copy()
    out["matched_gold_id"] = out["artifact_id"].map(matched_gold)
    out["gold_type"] = out["matched_gold_id"].map(
        lambda gid: gold_by_id.get(gid, {}).get("artifact_type") if gid else None
    )
    out["correct_type"] = out["artifact_id"].map(correct_type)
    return out
