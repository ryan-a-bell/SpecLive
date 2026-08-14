# Implementation Status Report

**Increment:** 1 (initial production-oriented repository)
**Date:** 2026-08-13
**Verification:** backend `pytest` — 29 passed; frontend `vitest` — 15 passed;
`tsc --noEmit` clean; `next build` succeeds; migrations + seed + export run.

## Delivered against the initial implementation boundary

| Requirement | Status | Where |
|-------------|--------|-------|
| Runnable web application | ✅ | `apps/web` (Next.js, `next build` verified) |
| Runnable API | ✅ | `apps/api` (FastAPI, `/docs` OpenAPI) |
| PostgreSQL schema and migrations | ✅ | `apps/api/alembic` (+ SQLite fallback) |
| Seeded demonstration session | ✅ | `fixtures/warehouse_modernization.json`, `app/seed.py` |
| Static / simulated streaming transcript | ✅ | seed transcript + WS `/stream` + mock STT |
| Artifact and evidence CRUD | ✅ | `ArtifactService`, `/artifacts` routes |
| Discovery tree | ✅ | `TreeService`, `components/tree` |
| Guided script panel | ✅ | `ScriptService`, `GuidedScriptPanel` |
| Git-style branch visualization | ✅ | `GitBranchView` |
| Conversation subway visualization | ✅ | `SubwayView` |
| Coverage matrix | ✅ | `CoverageService`, `CoverageMatrix` |
| Human confirmation workflow | ✅ | lifecycle rules + `/confirm`/`/reject`/`/merge` |
| JSON and Markdown export | ✅ | `exporters/`, `ExportService` |
| Unit tests | ✅ | `apps/api/tests`, `apps/web/**/*.test.tsx` |
| One end-to-end test | ✅ | `apps/api/tests/e2e/test_full_scenario.py` |
| Docker-based local setup | ✅ | `docker-compose.yml`, Dockerfiles, `Makefile` |
| Complete README + architecture docs | ✅ | `README.md`, `docs/` |

## Domain & rules

- All required entities modeled (session, segment, artifact, evidence, script,
  stage, branch, node, revision) with the full enum sets.
- Lifecycle guardrail enforced and tested: **no automated path can confirm or
  baseline** an artifact (ADR-0007, `test_lifecycle.py`, `test_evidence.py`).
- Evidence is first-class with typed relationships and exact offsets (ADR-0006).
- Domain events defined and published; WebSocket streams them; the bus is
  sync-now/queue-ready (ADR-0005).

## Six visualizations (prototype parity)

Live transcript + evidence highlights + badges · discovery tree · provenance
detail · guided script + branches · recommended questions + gaps · git branch
tree · conversation subway · coverage matrix. Mapping in
`docs/product/prototype-mapping.md`.

## Known deviations (documented)

- **Graph library:** MVP uses custom CSS/grid rendering faithful to the
  prototype instead of React Flow; React Flow is planned for Increment 2 when
  editing is needed (ADR-0008).
- **STT/LLM mocked:** deterministic heuristics, no network egress (ADR-0004).
- **Auth/RBAC/redaction/audit:** designed as placeholders in `SECURITY.md`, not
  enforced in this increment.
- **Coverage for live sessions:** derived heuristically; the seeded session uses
  an authored coverage map to match the prototype exactly.

## How to verify locally

```bash
# Backend
cd apps/api && python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" && pytest            # 29 passed
alembic upgrade head && python -m app.seed   # seed demo
python -m app.scripts.export_demo            # writes exports/

# Frontend (from repo root)
npm install
npm run typecheck && npm test                # 15 passed
npm run build                                # production build

# Full stack
make up && make seed                         # http://localhost:3000
```

## Test summary

- Backend: domain, lifecycle (human-confirmation guardrail), evidence validation
  + analysis pipeline, session/transcript API, artifact CRUD + confirm/reject/
  merge + revisions, branch creation/merge/graph, export (JSON/MD/traceability),
  full e2e scenario.
- Frontend: workspace store (state management), evidence-highlight navigation,
  discovery-tree interaction, coverage matrix, git branch visualization, guided
  script advancement.
