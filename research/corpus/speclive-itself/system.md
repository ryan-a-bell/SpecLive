# Ground-truth system: SpecLive (the Requirements Discovery Copilot itself)

A self-referential case: the transcript is a discovery call in which the product
team describes SpecLive's own requirements. The ground truth is verifiable
directly from this repository's `README.md` and `IMPLEMENTATION_STATUS.md`, which
makes it a strong round-trip anchor — you can check each recovered requirement
against the actual system.

## Objective

- **O1 — Real-time, evidence-traced derivation.** As a discovery call streams in,
  derive candidate objectives/needs/constraints/risks and keep every one
  traceable to the exact transcript evidence that produced it.

## Requirements

- **R1 — Full provenance per artifact.** Each candidate records source evidence,
  interpretation rationale, confidence, derivation method, and validation state.
- **R2 — Human confirmation before baseline.** A model-inferred requirement is
  never marked customer-confirmed without an explicit human action.
- **R3 — File upload through the same pipeline.** A recorded file can be uploaded
  and yields the same segments/artifacts as the live mic.
- **R4 — Live streaming ingest.** The live path streams mic audio → transcript →
  artifacts over a streaming connection.
- **R5 — Script + answer-driven branches.** The facilitator follows a configurable
  discovery script; customer answers spawn branches that keep their own evidence
  and artifacts; the script stays the anchor.
- **R7 — Discovery-package export.** Export a structured package as JSON and
  Markdown.

## Stakeholder needs

- **N1 — Configurable discovery script** the facilitator drives the call from.
- **N2 — Visible provenance for trust.** The facilitator must be able to see *why*
  each requirement was proposed, or they won't trust/adopt it.

## Constraints

- **C1 — Provider-neutral STT** (mock / local / hosted vendor).
- **C2 — Server-side credentials.** Provider credentials never reach the browser.
- **C3 — Runs with no API keys by default** (mock LLM/STT), so it runs key-free.
