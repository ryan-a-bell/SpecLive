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
  → LanguageModelProvider  (mock │ openai_compatible)  the actual derivation
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
quote. `validate_corpus.py` enforces that every quote is verbatim and every
`turn_index`/type/tier is valid.

Labeled cases (run `validate_corpus.py` to list):

| case | speakers | gold | notes |
|------|----------|------|-------|
| `warehouse-modernization` | 2 (Q&A) | 11 | from the seeded demo fixture; mock heuristics were written for it |
| `iot-warehouse-ml` | 2 (Q&A) | 13 | predictive-maintenance ML pipeline |
| `hospital-bed-mgmt` | 1 (monologue) | 16 | single-speaker lecture — derivation from narrative, not Q&A |
| `hpc-infrastructure` | 3 | 10 | multiple non-facilitator speakers |
| `speclive-itself` | 2 (Q&A) | 12 | self-referential; ground truth verifiable from this repo's README |

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

## Matchers

Alignment of derived↔gold is pluggable (`--matcher`), kept **independent of
evidence-target agreement** so a right-idea / wrong-citation artifact still
counts as recalled and its citation is graded separately.

- `lexical` (default) — token Jaccard + gold key-phrase hits, folding in each
  derived artifact's own (verbatim) evidence quote. Deterministic, no model.
  Conservative on paraphrase.
- `embedding` — cosine over an `EmbeddingProvider`. With a real embedding
  provider it tolerates paraphrase; with the mock (hash) provider it runs but is
  **not semantically meaningful** (a smoke path — expect inflated recall and low
  type/turn accuracy until a real embedder is configured).

## Run it

```bash
cd apps/api && pip install -e ".[dev]"      # one-time: the harness imports app.*
cd ../../research/harness

python validate_corpus.py                   # check every gold quote is verbatim
python run.py                               # all cases × strategies, mock, lexical
python run.py --case warehouse-modernization
python run.py --providers mock openai_compatible   # LLM auto-skips if no key
python run.py --matcher embedding
python run.py --perturb all                 # stress test: clean vs perturbed
```

Writes `results/latest.{json,md}` (or `results/perturbation.{json,md}` with
`--perturb`). A throwaway SQLite DB is used; your dev database is never touched.

### Real-LLM provider

`openai_compatible` is in the sweep but **skips with a printed reason unless
`LLM_API_KEY` is set** (with `LLM_API_BASE` / `LLM_MODEL`). Point it at OpenAI, a
local Ollama/vLLM server, or Anthropic's OpenAI-compatible endpoint, then re-run
the identical corpus to measure lift over the mock baseline. No code change —
config only.

### Stress tests

`perturb.py` transforms (`stt_noise`, `speaker_swap`, `distractor_padding`) are
applied to a clean transcript and re-scored. `--perturb` reports **recovery
degradation** vs clean (only recovery, since perturbations can move/rewrite turns
and invalidate the gold `turn_index` used by traceability).

## Baseline findings (mock provider, lexical matcher)

See `results/baseline.md`. Highlights:

- **The corpus discriminates.** `warehouse-modernization` scores ~27% recall /
  60% precision / 100% traceability-on-matched; the other four score **0%**. The
  difference is that the mock's keyword rules were written against the warehouse
  scenario — everywhere else its regexes don't fire on the actual phrasing, and
  it even mis-fires (e.g. a "Role-based access" *requirement* derived from
  "…only fires when the WAN is up…").
- **Context strategy is inert for the mock.** `segment` / `window` / `full` score
  identically — the mock reads one customer segment at a time and can't use
  cross-turn context. This is the measuring stick for the real LLM, which
  overrides `analyze_unit` to reason over whole units.
- **`speaker_swap` is the sharpest brittleness** (`--perturb`): flipping
  customer/facilitator labels drops warehouse recall ~18pp, because the mock only
  analyzes customer turns — i.e. the methodology is fragile to diarization
  errors. `stt_noise` / `distractor_padding` barely move the mock here.

## Layout

```
research/
  README.md
  corpus/<case-id>/{transcript.json, system.md, gold.json}
  harness/
    _bootstrap.py       wire real services against a throwaway DB; provider/embedder factories
    ingest.py           transcript.json → session + ordered segments (turn_index → segment)
    run.py              entry: sweep provider × strategy × matcher; --perturb
    match.py            pluggable matchers (lexical, embedding)
    score.py            the four metric families
    report.py           markdown rendering (summary, per-run, perturbation)
    perturb.py          stress-test transforms
    validate_corpus.py  gold-quote / schema validator
  results/              run outputs (latest.*/perturbation.* gitignored; baseline.md committed)
```

## Next steps

1. Wire a real embedding provider so `--matcher embedding` is semantic (the app
   only registers `mock` today).
2. Run the real LLM (`openai_compatible`) over the corpus and compare to baseline.
3. Add more perturbations (negation flips, implicit-only paraphrase variants) and
   report traceability under index-preserving transforms.
4. Grow the corpus toward harder, more paraphrased phrasing where the keyword
   mock is guaranteed to fail and only a real model can recover.
