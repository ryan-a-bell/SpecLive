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

    lines += ["", "## Per-run detail", ""]
    for r in runs:
        m = r["metrics"]
        c = m["counts"]
        rec = m["recovery"]
        cal = m["calibration"]
        lines += [
            f"### {r['case']} · {r['provider']} · {r['strategy']} "
            f"(threshold {r['threshold']})",
            "",
            f"- counts: {c['matched']}/{c['gold']} gold recovered, "
            f"{c['derived']} derived, {c['spurious']} spurious",
            f"- recall explicit={_pct(rec['recall_explicit'])} "
            f"paraphrased={_pct(rec['recall_paraphrased'])}",
            f"- calibration: TP conf={cal['mean_confidence_true_positive']} "
            f"FP conf={cal['mean_confidence_false_positive']}",
            f"- missed gold: {', '.join(m['missed_gold']) or 'none'}",
            "",
        ]

    return "\n".join(lines)
