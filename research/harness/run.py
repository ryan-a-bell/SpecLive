"""Entry point: sweep {provider} × {context strategy} over labeled corpus cases,
drive the real AnalysisService, score against gold, and write a report.

    python research/harness/run.py                       # all cases × strategies, mock, lexical
    python research/harness/run.py --case iot-warehouse-ml
    python research/harness/run.py --providers mock openai_compatible
    python research/harness/run.py --matcher embedding
    python research/harness/run.py --perturb all          # stress test: clean vs perturbed

Output: results/latest.json (full data) + results/latest.md (readable tables).
Providers that can't run here (e.g. openai_compatible with no LLM_API_KEY) are
skipped with a printed reason rather than erroring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import ingest as ingest_mod
import match as match_mod
import perturb as perturb_mod
import report as report_mod
import score as score_mod

# _bootstrap sets DATABASE_URL and puts apps/api on sys.path; import it first.
from _bootstrap import (
    STRATEGIES,
    build_embedder,
    make_context,
    provider_available,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS = _REPO_ROOT / "research" / "corpus"
_RESULTS = _REPO_ROOT / "research" / "results"


def _labeled_cases() -> list[str]:
    return sorted(
        p.name
        for p in _CORPUS.iterdir()
        if p.is_dir() and (p / "gold.json").exists() and (p / "transcript.json").exists()
    )


def run_variant(
    case_id: str,
    provider: str,
    strategy: str,
    matcher,
    threshold: float,
    transform: str | None,
) -> dict:
    case_dir = _CORPUS / case_id
    transcript = ingest_mod.load_transcript(case_dir / "transcript.json")
    if transform:
        transcript = perturb_mod.TRANSFORMS[transform](transcript)
    gold = json.loads((case_dir / "gold.json").read_text())["gold_artifacts"]

    ctx = make_context(provider, strategy)
    try:
        segments = ingest_mod.ingest(ctx, transcript)
        ctx.analysis.analyze_session(ctx.session_id)
        derived = ctx.artifacts.list_for_session(ctx.session_id)
        evidence_by_artifact = {a.id: ctx.artifacts.evidence_for(a.id) for a in derived}
    finally:
        ctx.close()

    pairs = matcher.match(derived, gold, evidence_by_artifact, threshold=threshold)
    metrics = score_mod.score(derived, evidence_by_artifact, gold, pairs, segments)
    return {
        "case": case_id,
        "provider": provider,
        "strategy": strategy,
        "matcher": type(matcher).__name__,
        "threshold": threshold,
        "variant": transform or "clean",
        "metrics": metrics,
    }


def _resolve_providers(requested: list[str]) -> list[str]:
    usable: list[str] = []
    for name in requested:
        ok, why = provider_available(name)
        if ok:
            usable.append(name)
        else:
            print(f"[skip] provider {name!r}: {why}")
    return usable


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default="all", help="case id, or 'all' (default)")
    ap.add_argument("--providers", nargs="+", default=["mock"])
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES))
    ap.add_argument("--matcher", choices=["lexical", "embedding"], default="lexical")
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument(
        "--perturb",
        nargs="*",
        help="stress test: run clean vs perturbed. Names from perturb.TRANSFORMS, "
        "or 'all'. Reports recovery degradation.",
    )
    args = ap.parse_args()

    cases = _labeled_cases() if args.case == "all" else [args.case]
    if not cases:
        raise SystemExit("No labeled cases found under research/corpus/*/gold.json")

    providers = _resolve_providers(args.providers)
    if not providers:
        raise SystemExit("No usable providers.")

    embedder = build_embedder() if args.matcher == "embedding" else None
    matcher = match_mod.get_matcher(args.matcher, embedder=embedder)

    if args.perturb is not None:
        transforms = (
            list(perturb_mod.TRANSFORMS)
            if not args.perturb or args.perturb == ["all"]
            else args.perturb
        )
        variants: list[str | None] = [None, *transforms]
        runs = [
            run_variant(case, provider, strategy, matcher, args.threshold, tf)
            for case in cases
            for provider in providers
            for strategy in args.strategies
            for tf in variants
        ]
        md = report_mod.render_perturbation(runs)
        out_name = "perturbation"
    else:
        runs = [
            run_variant(case, provider, strategy, matcher, args.threshold, None)
            for case in cases
            for provider in providers
            for strategy in args.strategies
        ]
        md = report_mod.render(runs)
        out_name = "latest"

    _RESULTS.mkdir(parents=True, exist_ok=True)
    (_RESULTS / f"{out_name}.json").write_text(json.dumps(runs, indent=2))
    (_RESULTS / f"{out_name}.md").write_text(md)
    print(md)
    print(f"\nWrote {_RESULTS / f'{out_name}.json'} and {_RESULTS / f'{out_name}.md'}")


if __name__ == "__main__":
    main()
