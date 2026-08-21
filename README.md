# Requirements Discovery Copilot

A facilitator's copilot for **live customer discovery conversations**. As a
conversation streams in, the application derives candidate **objectives,
stakeholder needs, requirements, constraints, assumptions, risks, decisions,
and open questions** — and keeps every derived item **traceable back to the
exact transcript evidence** it came from.

The facilitator follows a configurable **discovery script**, lets customer
answers spawn **conversation branches**, validates inferred items through an
explicit human-confirmation workflow, and at the end exports a structured
**discovery package** (JSON + Markdown).

> This repository is the **first production-oriented increment**. Speech-to-text
> supports mock, local faster-whisper, OpenAI Realtime, and Wispr Flow adapters.
> LLM calls remain mocked, so the default setup still runs with **no API keys**.

---

## Product purpose

Discovery calls produce requirements that are frequently untraceable,
prematurely "confirmed", or lost between the conversation and the spec. This
tool treats **evidence-first traceability** and **human validation before
baselining** as non-negotiable:

- Every candidate artifact records its **source evidence**, **interpretation
  rationale**, **confidence**, **derivation method**, and **validation state**.
- A model-inferred requirement is **never** marked customer-confirmed without an
  explicit user action or explicit confirmation evidence.
- The scripted conversation stays the anchor while answer-driven branches keep
  their own evidence and derived artifacts.

## Architecture summary

Monorepo with a clear front-end / back-end split:

```
apps/web   Next.js + React + TypeScript + Tailwind + shadcn-style UI + TanStack Query
apps/api   FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL
packages/  domain (shared TS types), client (typed API client), ui, config
```

- The API owns the domain, persistence, an internal **event bus**, and provider
  abstractions (`SpeechToTextProvider`, `LanguageModelProvider`,
  `EmbeddingProvider`, `ArtifactExporter`, `SessionRepository`, `EventBus`).
- The web app renders the six core visualizations and never embeds business
  logic — it reads typed server state and issues intent-level mutations.
- Streaming (transcript segments, candidate artifacts, evidence, tree/branch
  changes, recommendations) flows over WebSockets. Browser microphone audio goes
  only to the SpecLive API; provider selection and credentials stay server-side.
- Recorded audio can also be **uploaded as a file** (`POST /sessions/{id}/transcribe`).
  The server decodes it to canonical PCM once and runs it through the *same*
  provider-neutral ingest pipeline as the live mic, so an upload yields the same
  persisted segments, evidence, and derived artifacts.

See [`docs/architecture/README.md`](docs/architecture/README.md) for context,
container, component, event-flow, derivation-sequence, and data-model diagrams
(Mermaid), and [`docs/adr`](docs/adr) for the architecture decisions.

## Prototype reference

The interaction and visual-design reference is the static prototype at
[`docs/product/prototype/customer_requirements_copilot_v41.html`](docs/product/prototype/customer_requirements_copilot_v41.html)
(open it directly in a browser). The mapping from each prototype panel to its
production component and service is in
[`docs/product/prototype-mapping.md`](docs/product/prototype-mapping.md).

## Local setup

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
make up            # postgres + api + web (+ optional redis)
make seed          # load the warehouse-modernization demo session
open http://localhost:3000
```

- Web: http://localhost:3000
- API: http://localhost:8000 (OpenAPI docs at `/docs`)

### Option B — run services directly

```bash
# API
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://copilot:copilot@localhost:5432/copilot
alembic upgrade head
python -m app.seed          # seed demo data
uvicorn app.main:app --reload

# Web
cd apps/web
npm install
npm run dev
```

If no PostgreSQL is available, the API falls back to a local SQLite database
(`DATABASE_URL=sqlite+pysqlite:///./copilot.db`) so tests and the demo still run.

## Environment variables

See [`.env.example`](.env.example) for the full list. Key ones:

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | SQLAlchemy URL | `postgresql+psycopg://copilot:copilot@db:5432/copilot` |
| `REDIS_URL` | Optional event-bus/cache backend | _(unset → in-memory)_ |
| `STT_PROVIDER` | Speech-to-text provider id | `mock` |
| `STT_SPEAKER_DETECTION` | Advertise server-side voice labeling support | `false` |
| `OPENAI_API_KEY` | Required for `STT_PROVIDER=openai` | _(unset)_ |
| `WISPR_FLOW_API_KEY` | Required for `STT_PROVIDER=wispr` | _(unset)_ |
| `WISPR_FLOW_ACCESS_TOKEN` | Wispr streaming-session token | _(unset)_ |
| `FASTER_WHISPER_MODEL` | Local faster-whisper model | `small.en` |
| `LLM_PROVIDER` | Language-model provider id | `mock` |
| `EMBEDDING_PROVIDER` | Embedding provider id | `mock` |
| `EVENT_BUS` | `memory` or `redis` | `memory` |
| `CORS_ORIGINS` | Allowed web origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_BASE_URL` | Web → API base URL | `http://localhost:8000` |
| `LOG_LEVEL` | Structured log level | `INFO` |

**No secrets are committed.** All configuration is environment-driven.

## Development commands

| Command | Description |
|---------|-------------|
| `make up` / `make down` | Start / stop the Docker Compose stack |
| `make seed` | Seed the demonstration session |
| `make api` | Run the API locally with reload |
| `make web` | Run the web app locally |
| `make lint` | Ruff + mypy (api) and ESLint + tsc (web) |
| `make format` | Ruff format + Prettier |
| `make test` | All backend + frontend tests |
| `make e2e` | The full end-to-end discovery scenario |
| `make export` | Export the seeded session's discovery package |

## Testing commands

```bash
make test              # everything
cd apps/api && pytest  # backend unit/integration/e2e
cd apps/web && npm test # frontend component/state tests
```

Backend coverage: domain models, API routes, evidence-link validation,
artifact state transitions, branch creation/merge, export, and one full
end-to-end scenario. Frontend coverage: components, selection state,
transcript→artifact navigation, tree interaction, script advancement, and
branch visualization.

### Uploading a recorded file

Besides the live microphone WebSocket, a finished recording can be transcribed
by uploading it:

```bash
curl -F "file=@discovery-call.mp3" \
  http://localhost:8000/api/v1/sessions/<session-id>/transcribe
```

The server decodes the file to 16 kHz mono PCM and streams it through the
configured `STT_PROVIDER` (mock/local/openai/wispr) exactly like live audio, so
the response and the session end up with the same segments and derived
artifacts. WAV uploads decode with no extra dependencies; compressed formats
(MP3, M4A, OGG, …) require `ffmpeg` on the API host (bundled in the Docker
image). Optional `speaker_mode=manual` with `speaker` and `speaker_name` form
fields stamp every segment with a fixed speaker; the default `auto` mode uses
provider-detected voices. In the web app, the transcript panel's **Upload
recording** button does the same thing.

### Synthetic audio playback

To exercise the live streaming path without a microphone,
[`scripts/audio_playback_test.py`](scripts/README.md) synthesizes a
multi-speaker discussion (Piper by default) and streams it into a live session:

```bash
python scripts/audio_playback_test.py --script scripts/sample_discussion.json
```

Run the API with `STT_PROVIDER=local` (faster-whisper) to transcribe the
synthesized speech for real; with the default `mock` provider it validates the
streaming plumbing end to end. See [`scripts/README.md`](scripts/README.md).

## Repository map

```
requirements-discovery-copilot/
├── apps/
│   ├── web/                 Next.js front end (six visualizations)
│   └── api/                 FastAPI back end (domain, services, providers)
├── packages/
│   ├── domain/              Shared TypeScript domain types + Zod schemas
│   ├── client/              Typed API client used by the web app
│   ├── ui/                  Shared UI primitives / tokens
│   └── config/              Shared tsconfig / eslint / tailwind presets
├── docs/
│   ├── architecture/        C4 + event + sequence + data-model diagrams
│   ├── adr/                 Architecture decision records (0001–0008)
│   ├── api/                 API guide + sample payloads
│   ├── domain/              Domain glossary
│   └── product/             MVP scope, personas, journeys, prototype ref
├── fixtures/                Seed scenario (warehouse modernization)
├── scripts/                 Dev/seed/export helpers
├── tests/                   Cross-cutting e2e docs
├── docker-compose.yml
├── Makefile
├── README.md · CONTRIBUTING.md · SECURITY.md · LICENSE · .env.example
```

## Current limitations

- **LLM analysis is mocked.** `MockLanguageModelProvider` derives artifacts with
  deterministic keyword/heuristic rules, not a real model. Confidence values are
  illustrative. Local STT uses fixed-duration pseudo-streaming chunks.
- **Auth is stubbed.** A single facilitator identity is assumed; role-based
  access control is designed (see `SECURITY.md`) but not enforced.
- **Speaker diarization:** the data model, auto/manual mode, stable voice grouping,
  confidence, and correction workflow are implemented. Production-quality voice
  clustering still depends on the configured server-side diarization engine.
- **Exports:** JSON and Markdown only. CSV/DOCX/ReqIF/Jira/DOORS/SysML are
  designed for via the `ArtifactExporter` interface but not implemented.
- **No compliance claims.** Security features are architectural placeholders
  unless explicitly implemented and verified.

## Roadmap

Grouped backlog lives in [`docs/product/backlog.md`](docs/product/backlog.md):

- **MVP (this increment):** runnable web + API, schema/migrations, seeded demo,
  simulated streaming, artifact/evidence CRUD, tree, script panel, git/subway
  visualizations, coverage matrix, human confirmation, JSON/MD export, tests.
- **Increment 2:** LLM-backed derivation, auth +
  RBAC, richer graph editing, CSV/DOCX export.
- **Increment 3:** multi-facilitator collaboration, embeddings-based clustering,
  redaction pipeline, audit logging.
- **Future integrations:** ReqIF, Jira, DOORS, SysML exporters; enterprise SSO.

## License

[MIT](LICENSE).
