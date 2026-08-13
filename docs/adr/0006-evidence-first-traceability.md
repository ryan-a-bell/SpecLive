# 0006 — Evidence-first requirement traceability

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The core product value is that every derived item is traceable to what the
customer actually said. Requirements that cannot be traced are the failure mode
we exist to prevent.

## Decision

Make `EvidenceLink` a first-class entity, not a UI decoration. Each link records
the transcript segment, exact character offsets (`quote_start`/`quote_end`), the
quoted text, a typed `relationship` (`direct` / `supporting` / `contradicting` /
`superseding` / `contextual`), a confidence, and a rationale. Every
artifact-producing path attaches evidence (or explicitly marks the artifact
`detected`/`inferred` with none). The export's traceability appendix is generated
from these links.

## Consequences

- The transcript view can highlight the exact supporting span and color it by
  relationship; clicking it selects the artifact.
- Contradicting/superseding relationships are modeled, enabling conflict
  surfacing in the coverage matrix.
- Derivation must compute offsets; the seed loader computes them from quoted text
  to stay robust to edits.
- Slightly more write work per artifact, accepted as the point of the product.
