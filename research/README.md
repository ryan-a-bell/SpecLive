# research/ — transcript → requirements evaluation harness

A local research tool for **optimizing and stress-testing SpecLive's
transcript-to-requirements methodology**. It drives the *real* derivation
pipeline (`AnalysisService` + a `LanguageModelProvider` + a `ContextStrategy`)
over labeled sample transcripts and scores what comes out against a hand-authored
ground truth.

This is a local research tool, not part of the app or CI.

## The pipeline under test

```
transcript segments
  → ContextStrategy        (segment │ window │ full)   how much context each call sees
  → LanguageModelProvider  (mock │ …)                  the actual derivation
  → ArtifactCandidate[]    (+ evidence spans)
  → AnalysisService        persists as INFERRED artifacts + evidence links
```

"Methodology" = **which context strategy × which provider** best turns a
transcript into a traceable requirement set. The harness sweeps both knobs so a
result is a comparison, not a single number.

## Corpus (ground truth)

Each case under `corpus/<case-id>/` is a **known/existing system** described in a
discovery transcript, so the system is the round-trip anchor: a faithful
methodology should reconstruct its requirements.

| file | role |
|------|------|
| `transcript.json` | the discovery call (same `turns` format as `scripts/conversations/*`) |
| `system.md` | ground-truth spec of the real system the transcript describes |
| `gold.json` | `system.md` distilled into scoreable expected artifacts |

`gold.json` rows carry: `artifact_type`, `canonical_statement`, `key_phrases`,
`tier` (`must`/`should`/`nice`, weights recall), `implicitness`
(`explicit`/`paraphrased`/`implicit`, slices results), `negation`, and
`evidence` keyed by `turn_index` into `transcript.turns` with a **verbatim**
quote. Authoring is hand-first — the gold *is* the measuring stick.

Labeled cases:
- `iot-warehouse-ml` — IoT predictive-maintenance ML pipeline (13 gold artifacts).

## Metrics

Four independent families — a recovered requirement can be right or wrong on each
axis separately:

- **recovery** — recall / weighted-recall / precision / F1; recall sliced by
  `implicitness`. "How well is the system described?"
- **typing** — do matched items land in the right `ArtifactType` bucket.
- **traceability** — for matched items: `has_evidence`, `cites_correct_turn`
  (evidence points at the gold-expected segment), `quote_grounded` (the cited
  text is a verbatim substring of its segment — the property the LLM prompt
  demands). This is SpecLive's evidence-first philosophy, measured.
- **calibration** — is mean confidence higher for true positives than for
  spurious ones.

Matching (`match.py`) is a transparent lexical matcher (token Jaccard + gold
key-phrase hits) kept **independent** of evidence quality, so a right-idea /
wrong-citation artifact still counts as recalled and its citation is graded
separately. Swap in an embedding / LLM-judge matcher later without touching the
metrics.

## Run it

```bash
cd apps/api && pip install -e ".[dev]"      # one-time: the harness imports app.*
cd ../../research/harness
python run.py                               # all cases × all strategies, mock
python run.py --case iot-warehouse-ml --strategies segment full
python run.py --threshold 0.35
```

Writes `research/results/latest.{json,md}`. The harness binds a throwaway SQLite
DB and never touches your dev database.

## Baseline finding (mock provider)

See `results/baseline.md`. The keyword mock recovers **0/13** on
`iot-warehouse-ml` and all three context strategies score identically — expected,
and the point of the baseline:

- The mock reads one customer segment at a time via regex, so it cannot use a
  facilitator's paraphrase or reason across turns; context strategy makes no
  difference to it (`analyze_unit` falls back to per-segment).
- It **mis-fires**: e.g. it derives a "Role-based access" *requirement* from
  "…only fires when the WAN is up…" — a concrete precision failure.

This is the measuring stick for the real-LLM path: re-run the identical corpus
through `openai_compatible` (Anthropic's OpenAI-compatible endpoint) to measure
the lift.

## Layout

```
research/
  README.md
  corpus/<case-id>/{transcript.json, system.md, gold.json}
  harness/
    _bootstrap.py   wire real services against a throwaway DB
    ingest.py       transcript.json → session + ordered segments (turn_index → segment)
    run.py          entry: sweep provider × strategy, score, report
    match.py        derived ↔ gold alignment
    score.py        the four metric families
    report.py       markdown rendering
    perturb.py      stress-test transforms (stt noise, speaker swap, distractors)
  results/          run outputs (latest.* gitignored; baseline.md committed)
```

## Next steps

1. Label the other three existing conversations + the warehouse fixture.
2. Author a new known-system case where the spec is verifiable (e.g. SpecLive
   itself).
3. Wire `perturb.py` into `run.py` behind a `--perturb` flag; report degradation.
4. Add the real LLM provider to the sweep and compare against this baseline.
5. Add an embedding/LLM-judge matcher for the real-LLM run (phrasings diverge).
