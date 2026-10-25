"""Render sweep runs as a Markdown report (one summary table + per-run detail)."""

from __future__ import annotations


def _pct(x: float) -> str:
    return f"{x * 100:4.0f}%"


def render(runs: list[dict]) -> str:
    lines: list[str] = ["# Transcript → requirements: eval report", ""]

    # Summary table: one row per run.
    lines += [
        "| case | provider | strategy | recall | wtd-recall | precision | F1 | type-acc | has-ev | correct-turn | grounded |",
        "|------|----------|----------|--------|-----------|-----------|----|----------|--------|--------------|----------|",
    ]
    for r in runs:
        m = r["metrics"]
        rec, typ, tr = m["recovery"], m["typing"], m["traceability"]
        lines.append(
            f"| {r['case']} | {r['provider']} | {r['strategy']} | "
            f"{_pct(rec['recall'])} | {_pct(rec['weighted_recall'])} | "
            f"{_pct(rec['precision'])} | {_pct(rec['f1'])} | "
            f"{_pct(typ['type_accuracy'])} | {_pct(tr['has_evidence'])} | "
            f"{_pct(tr['cites_correct_turn'])} | {_pct(tr['quote_grounded'])} |"
        )

    if runs:
        r0 = runs[0]
        lines += ["", f"_matcher: {r0.get('matcher','?')}, threshold {r0['threshold']}_", ""]

    lines += ["", "## Per-run detail", ""]
    for r in runs:
        m = r["metrics"]
        c = m["counts"]
        rec = m["recovery"]
        cal = m["calibration"]
        lines += [
            (
                f"### {r['case']} · {r['provider']} · {r['strategy']} "
                f"(threshold {r['threshold']})"
            ),
            "",
            (
                f"- counts: {c['matched']}/{c['gold']} gold recovered, "
                f"{c['derived']} derived, {c['spurious']} spurious"
            ),
            (
                f"- recall explicit={_pct(rec['recall_explicit'])} "
                f"paraphrased={_pct(rec['recall_paraphrased'])}"
            ),
            (
                f"- calibration: TP conf={cal['mean_confidence_true_positive']} "
                f"FP conf={cal['mean_confidence_false_positive']}"
            ),
            f"- missed gold: {', '.join(m['missed_gold']) or 'none'}",
            "",
        ]

    return "\n".join(lines)


def _delta(x: float) -> str:
    return f"{x * 100:+4.0f}pp" if x else "   0pp"


def render_perturbation(runs: list[dict]) -> str:
    """Report recovery degradation of each perturbation vs the clean baseline.

    Perturbations may move or rewrite turns, so only the recovery family
    (recall/precision/F1) — which does not depend on turn alignment — is
    compared here; traceability under perturbation is not directly comparable.
    """
    # Index clean recall/precision per (case, provider, strategy).
    clean: dict[tuple, dict] = {}
    for r in runs:
        if r["variant"] == "clean":
            clean[(r["case"], r["provider"], r["strategy"])] = r["metrics"]["recovery"]

    lines = ["# Stress test: recovery degradation under perturbation", ""]
    lines += [
        "| case | provider | strategy | variant | recall | Δrecall | precision | Δprecision | spurious |",
        "|------|----------|----------|---------|--------|---------|-----------|------------|----------|",
    ]
    for r in runs:
        rec = r["metrics"]["recovery"]
        base = clean.get((r["case"], r["provider"], r["strategy"]), rec)
        d_rec = rec["recall"] - base["recall"]
        d_prec = rec["precision"] - base["precision"]
        is_clean = r["variant"] == "clean"
        lines.append(
            f"| {r['case']} | {r['provider']} | {r['strategy']} | {r['variant']} | "
            f"{_pct(rec['recall'])} | {'—' if is_clean else _delta(d_rec)} | "
            f"{_pct(rec['precision'])} | {'—' if is_clean else _delta(d_prec)} | "
            f"{r['metrics']['counts']['spurious']} |"
        )
    lines += [
        "",
        (
            "_Δ is perturbed minus clean, in percentage points. Only recovery "
            "metrics are compared (perturbations can move/rewrite turns, so "
            "traceability is not directly comparable)._"
        ),
    ]
    return "\n".join(lines)
