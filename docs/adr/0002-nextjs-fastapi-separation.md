# 0002 — Next.js and FastAPI separation

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The application needs rich, interactive visualizations (trees, git-style
branches, subway map, coverage matrix) and real-time streaming, plus a
domain-heavy back end (typed models, lifecycle rules, derivation, export). No
single-language stack serves both concerns well.

## Decision

Separate the front end (Next.js + React + TypeScript) from the back end (FastAPI
+ Pydantic + SQLAlchemy). They communicate over a versioned REST API
(`/api/v1`) plus a WebSocket for streaming. The back end owns all business logic
and persistence; the front end holds only presentation and client cache state.

## Consequences

- Clear contract boundary: the API is typed with Pydantic and consumed through a
  Zod-validated client, giving end-to-end type safety without coupling.
- Each side scales and deploys independently; the back end can serve other
  clients (CLI, integrations) later.
- Requires CORS configuration and a running API for the web app to be useful; a
  mock/offline mode mitigates this for demos.
- Rejected alternative: a single Next.js app with API routes — it would pull the
  Python domain/derivation into TypeScript or a serverless boundary, losing the
  Pydantic/SQLAlchemy strengths and the option of Python ML tooling later.
