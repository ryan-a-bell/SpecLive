"""Validate the corpus: every gold evidence quote must be a verbatim substring of
its referenced transcript turn, turn_index in range, and artifact_type/tier valid.

    python research/harness/validate_corpus.py

Exits non-zero on any problem so it can gate corpus edits.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.domain.enums import ArtifactType

_CORPUS = Path(__file__).resolve().parents[1] / "corpus"
_TYPES = {t.value for t in ArtifactType}
_TIERS = {"must", "should", "nice"}


def validate() -> list[str]:
    problems: list[str] = []
    for case_dir in sorted(p for p in _CORPUS.iterdir() if p.is_dir()):
        gp, tp = case_dir / "gold.json", case_dir / "transcript.json"
        if not gp.exists() or not tp.exists():
            continue
        turns = json.loads(tp.read_text())["turns"]
        gold = json.loads(gp.read_text())["gold_artifacts"]
        ids = set()
        for g in gold:
            gid = g.get("id", "?")
            where = f"{case_dir.name}/{gid}"
            if gid in ids:
                problems.append(f"{where}: duplicate id")
            ids.add(gid)
            if g["artifact_type"] not in _TYPES:
                problems.append(f"{where}: bad artifact_type {g['artifact_type']!r}")
            if g.get("tier") not in _TIERS:
                problems.append(f"{where}: bad tier {g.get('tier')!r}")
            ti = g["evidence"]["turn_index"]
            if not (0 <= ti < len(turns)):
                problems.append(f"{where}: turn_index {ti} out of range (0..{len(turns)-1})")
                continue
            quote = g["evidence"]["quote"]
            if quote not in turns[ti]["text"]:
                problems.append(f"{where}: quote not verbatim in turn {ti}: {quote!r}")
    return problems


def main() -> None:
    problems = validate()
    n_cases = sum(
        1 for p in _CORPUS.iterdir() if p.is_dir() and (p / "gold.json").exists()
    )
    if problems:
        print(f"CORPUS INVALID ({len(problems)} problem(s) across {n_cases} case(s)):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"corpus OK: {n_cases} labeled case(s), all gold quotes verbatim")


if __name__ == "__main__":
    main()
