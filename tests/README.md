# Tests

Tests live next to the code they cover; this directory documents the overall
strategy and the cross-cutting end-to-end scenario.

## Where tests live

| Layer | Location | Runner |
|-------|----------|--------|
| Backend unit/integration | `apps/api/tests` | `pytest` |
| Backend end-to-end | `apps/api/tests/e2e` | `pytest tests/e2e` |
| Frontend component/state | `apps/web/**/*.test.tsx`, `apps/web/lib/*.test.ts` | `vitest` |

Run everything from the repo root with `make test`, or `make e2e` for the
end-to-end scenario only.

## Backend coverage

- **Domain model** (`test_domain.py`) — entity defaults, enum completeness.
- **Lifecycle** (`test_lifecycle.py`) — transition legality and the
  human-confirmation guardrail (automation cannot confirm/baseline).
- **Evidence + analysis** (`test_evidence.py`) — offset validation; mock
  derivation yields only inferred artifacts, each with evidence.
- **Sessions/transcript API** (`test_api_sessions.py`).
- **Artifact API** (`test_api_artifacts.py`) — create, evidence, confirm/reject,
  patch+revision, merge with evidence re-pointing.
- **Branches** (`test_branches.py`) — create, nodes, merge, graph projection.
- **Export** (`test_export.py`) — JSON sections, Markdown render, traceability.

## Frontend coverage

- **State management** (`lib/store.test.ts`).
- **Transcript → artifact navigation** (`EvidenceText.test.tsx`).
- **Discovery-tree interaction** (`TreeNode.test.tsx`).
- **Script advancement** (`GuidedScriptPanel.test.tsx`).
- **Branch visualization** (`GitBranchView.test.tsx`).
- **Coverage matrix** (`CoverageMatrix.test.tsx`).

## End-to-end scenario

`apps/api/tests/e2e/test_full_scenario.py` exercises the whole workflow:

1. Start a session (anchored on the seeded script).
2. Submit several transcript segments.
3. Generate candidate artifacts (mock analysis).
4. Evidence links created during analysis.
5. Read the populated discovery tree.
6. Inspect the conversation graph (branches).
7. Confirm a requirement (explicit human action).
8. Export the discovery package (JSON + Markdown) and assert the confirmed
   requirement appears in the confirmed section.
