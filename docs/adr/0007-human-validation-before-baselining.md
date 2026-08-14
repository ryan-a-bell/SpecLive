# 0007 — Human validation before baselining

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

A model-inferred requirement must never be presented as customer-confirmed. This
is both a correctness and a trust requirement: baselining unvalidated inferences
would defeat the tool's purpose.

## Decision

Encode the lifecycle `detected → inferred → clarified → customer_confirmed →
baselined` (plus `rejected` / `superseded` / `merged`) as explicit transition
rules in `app.domain.lifecycle`. The rules distinguish the actor:

- Automated actors (`actor_is_human=False`) may only set `detected` / `inferred`.
- `customer_confirmed` and `baselined` require `actor_is_human=True`.

`AnalysisService` always calls with `actor_is_human=False`; only the explicit
`/confirm` endpoint (a human action) can reach `customer_confirmed`. Every
transition writes an `ArtifactRevision`.

## Consequences

- It is structurally impossible for the mock (or a future LLM) to confirm an
  artifact; the guardrail is enforced in the domain, tested in
  `test_lifecycle.py`, and re-asserted in `test_evidence.py` and the e2e test.
- The UI's confirm action is the single path to confirmation, matching the
  prototype's Confirm button.
- Revisions provide an audit trail of who changed what and why.
