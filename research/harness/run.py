"""Entry point: sweep {provider} × {context strategy} over labeled corpus cases,
drive the real AnalysisService, score against gold, and write a report.

    python research/harness/run.py                     # all cases, all strategies, mock
    python research/harness/run.py --case iot-warehouse-ml
    python research/harness/run.py --strategies segment full --threshold 0.3

Output: results/latest.json (full data) + results/latest.md (readable table).
Run this from the repo root or anywhere; paths are resolved relative to the repo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# _bootstrap sets DATABASE_URL and puts apps/api on sys.path; import it first.
from _bootstrap import STRATEGIES, make_context
import ingest as ingest_mod
import match as match_mod
import report as report_mod
import score as score_mod

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS = _REPO_ROOT / "research" / "corpus"
_RESULTS = _REPO_ROOT / "research" / "results"


def _labeled_cases() -> list[str]:
    return sorted(
        p.name
        for p in _CORPUS.iterdir()
        if p.is_dir() and (p / "gold.json").exists() and (p / "transcript.json").exists()
    )


def run_case(case_id: str, provider: str, strategy: str, threshold: float) -> dict:
    case_dir = _CORPUS / case_id
    transcript = ingest_mod.load_transcript(case_dir / "transcript.json")
    gold = json.loads((case_dir / "gold.json").read_text())["gold_artifacts"]

    ctx = make_context(provider, strategy)
    try:
        segments = ingest_mod.ingest(ctx, transcript)
        ctx.analysis.analyze_session(ctx.session_id)
        derived = ctx.artifacts.list_for_session(ctx.session_id)
        evidence_by_artifact = {a.id: ctx.artifacts.evidence_for(a.id) for a in derived}
    finally:
        ctx.close()

    pairs = match_mod.match(derived, gold, threshold=threshold)
    metrics = score_mod.score(derived, evidence_by_artifact, gold, pairs, segments)
    return {
        "case": case_id,
        "provider": provider,
        "strategy": strategy,
        "threshold": threshold,
        "metrics": metrics,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default="all", help="case id, or 'all' (default)")
    ap.add_argument("--providers", nargs="+", default=["mock"])
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES))
    ap.add_argument("--threshold", type=float, default=0.30)
    args = ap.parse_args()

    cases = _labeled_cases() if args.case == "all" else [args.case]
    if not cases:
        raise SystemExit("No labeled cases found under research/corpus/*/gold.json")

    runs = [
        run_case(case, provider, strategy, args.threshold)
        for case in cases
        for provider in args.providers
        for strategy in args.strategies
    ]

    _RESULTS.mkdir(parents=True, exist_ok=True)
    (_RESULTS / "latest.json").write_text(json.dumps(runs, indent=2))
    md = report_mod.render(runs)
    (_RESULTS / "latest.md").write_text(md)
    print(md)
    print(f"\nWrote {_RESULTS/'latest.json'} and {_RESULTS/'latest.md'}")


if __name__ == "__main__":
    main()
