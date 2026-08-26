"""Turn (derived artifacts + evidence + gold + matches) into metrics.

Four independent families — a recovered requirement can be right or wrong on
each axis separately:

* recovery      recall / precision of the requirement set (tier-weighted)
* typing        do matched items land in the right ArtifactType bucket
* traceability  do matched items carry evidence that (a) exists, (b) quotes the
                segment verbatim (grounding), (c) cites the gold-expected turn
* calibration   are matched (true-positive) confidences higher than spurious ones
"""

from __future__ import annotations

from match import Pair

_TIER_WEIGHT = {"must": 3.0, "should": 2.0, "nice": 1.0}


def _safe_div(n: float, d: float) -> float:
    return round(n / d, 3) if d else 0.0


def score(
    derived: list,
    evidence_by_artifact: dict[str, list],
    gold: list[dict],
    pairs: list[Pair],
    segments: list,
) -> dict:
    seg_id_to_turn = {seg.id: i for i, seg in enumerate(segments)}
    seg_text = {seg.id: seg.text for seg in segments}
    gold_by_id = {g["id"]: g for g in gold}

    matched_gold_ids = {p.gold_id for p in pairs}
    matched_derived_idx = {p.derived_index for p in pairs}

    # --- recovery ---
    recall = _safe_div(len(matched_gold_ids), len(gold))
    precision = _safe_div(len(matched_derived_idx), len(derived))
    spurious = len(derived) - len(matched_derived_idx)
    f1 = _safe_div(2 * precision * recall, precision + recall) if (precision + recall) else 0.0

    gold_w = sum(_TIER_WEIGHT[g["tier"]] for g in gold)
    hit_w = sum(_TIER_WEIGHT[gold_by_id[gid]["tier"]] for gid in matched_gold_ids)
    weighted_recall = _safe_div(hit_w, gold_w)

    # recall sliced by difficulty label
    def _slice_recall(key: str, value) -> float:
        subset = [g["id"] for g in gold if g.get(key) == value]
        if not subset:
            return 0.0
        return _safe_div(sum(1 for gid in subset if gid in matched_gold_ids), len(subset))

    # --- typing ---
    type_acc = _safe_div(sum(1 for p in pairs if p.type_match), len(pairs))

    # --- traceability (over matched derived artifacts only) ---
    n_matched = len(pairs)
    has_ev = 0
    seg_correct = 0
    total_links = 0
    grounded_links = 0
    for p in pairs:
        art = derived[p.derived_index]
        links = evidence_by_artifact.get(art.id, [])
        if links:
            has_ev += 1
        gold_turn = gold_by_id[p.gold_id]["evidence"]["turn_index"]
        cited_turns = {seg_id_to_turn.get(l.transcript_segment_id) for l in links}
        if gold_turn in cited_turns:
            seg_correct += 1
        for l in links:
            total_links += 1
            text = seg_text.get(l.transcript_segment_id, "")
            if l.quoted_text and l.quoted_text in text:
                grounded_links += 1

    traceability = {
        "has_evidence": _safe_div(has_ev, n_matched),
        "cites_correct_turn": _safe_div(seg_correct, n_matched),
        "quote_grounded": _safe_div(grounded_links, total_links),
    }

    # --- calibration ---
    tp_conf = [derived[i].confidence for i in matched_derived_idx]
    fp_conf = [d.confidence for i, d in enumerate(derived) if i not in matched_derived_idx]
    calibration = {
        "mean_confidence_true_positive": _safe_div(sum(tp_conf), len(tp_conf)),
        "mean_confidence_false_positive": _safe_div(sum(fp_conf), len(fp_conf)),
    }

    return {
        "counts": {
            "gold": len(gold),
            "derived": len(derived),
            "matched": n_matched,
            "spurious": spurious,
        },
        "recovery": {
            "recall": recall,
            "weighted_recall": weighted_recall,
            "precision": precision,
            "f1": f1,
            "recall_explicit": _slice_recall("implicitness", "explicit"),
            "recall_paraphrased": _slice_recall("implicitness", "paraphrased"),
        },
        "typing": {"type_accuracy": type_acc},
        "traceability": traceability,
        "calibration": calibration,
        "missed_gold": sorted(g["id"] for g in gold if g["id"] not in matched_gold_ids),
    }
