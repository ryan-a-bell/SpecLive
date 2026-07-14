# Build Progress — Requirements Discovery Copilot

Snapshot of the initial repository build. Update as we go.

## Architectural decisions (confirmed with product owner)

| Decision | Choice | ADR |
|---|---|---|
| Stack | Full stack as specified: Next.js web + FastAPI + PostgreSQL + Docker Compose | ADR-0002, 0003 |
| Graph viz | Custom SVG/CSS lane renderers (not React Flow) for git/subway/matrix | ADR-0008 |
| Repo layout | Slim monorepo: `apps/web` + `apps/api`, domain types as folders inside web (no separate `packages/`) | ADR-0001 |
| Streaming | WebSocket (bidirectional from day one, ready for live audio upload) | ADR-0005 |

## Done ✅

### Backend (`apps/api`) — imports cleanly, 14 routes registered
- [x] Project config: `pyproject.toml` (ruff, mypy, pytest), `app/config.py`, `app/logging.py` (structlog)
- [x] Enums + lifecycle state machine tables: `app/enums.py`
      (artifact status transitions, confirmable/closable states, evidence relationships, coverage states)
- [x] SQLAlchemy models: `app/models.py` — all 11 entities
      (DiscoverySession, TranscriptSegment, DiscoveryArtifact, EvidenceLink, ArtifactRevision,
      ScriptDefinition, ScriptStage, ConversationBranch, ConversationNode)
- [x] Pydantic schemas / API contracts: `app/schemas.py`
- [x] Internal event bus (sync now, queue-ready): `app/events.py`
- [x] Provider interfaces + mock impls: `app/providers/` (STT, LLM, Embedding, Exporter — keyless)
- [x] ID generation: `app/ids.py` (human-readable REQ-002 / NEED-001 / SEG-101 codes)
- [x] Domain errors: `app/errors.py`
- [x] Services layer (`app/services/`):
      session, transcript, analysis (derivation pipeline), artifact (lifecycle state machine),
      evidence, revision, tree, script, branch, coverage, export (JSON + Markdown + registry)
- [x] Routers (`app/routers/`): sessions, transcript, artifacts, views, scripts, analysis
- [x] FastAPI app + WebSocket streaming endpoint + OpenAPI tags: `app/main.py`, `app/streaming.py`

## Not started yet ⬜ — pick up here

1. **Alembic migrations + seed fixtures** (task #3)
   - `apps/api/alembic/` env + initial migration
   - `fixtures/` warehouse/field-ops seed scenario (transcript, script stages, artifacts,
     evidence links, branches, coverage) + `scripts/seed.py` loader
2. **Backend tests** (task #4)
   - domain, API, evidence validation, artifact state transitions, branch create/merge, export, one e2e
3. **Frontend Next.js app** (task #5) — `apps/web/`
   - all six panels + git/subway/matrix viz, Zustand selection store, typed API client, TanStack Query,
     WebSocket hook, component tests
4. **Docs, Docker, Makefile, root files** (task #6)
   - README, 8 ADRs, architecture mermaid diagrams, docker-compose.yml, Makefile, `.env.example`,
     CONTRIBUTING, SECURITY, LICENSE, backlog (MVP/Inc2/Inc3/Future), implementation-status report
   - `docs/product/prototype-mapping.md` is already written ✅

## How to resume the backend locally
```bash
cd apps/api && . .venv/bin/activate
python -c "from app.main import app"   # sanity check (currently passes)
```
The venv exists with deps installed. Postgres is NOT yet wired (no migrations); the app
currently points at `postgresql+psycopg://rdc:rdc@localhost:5432/rdc` via `RDC_DATABASE_URL`.
Tests will run against SQLite once written (db.py already handles the sqlite connect args).

## Known open items to decide later
- Coverage matrix uses a computed baseline + seed override in session metadata — confirm that's acceptable vs. a dedicated coverage table.
- WebSocket clients are receive-only this increment; live audio upload path is stubbed in the mock STT provider.
