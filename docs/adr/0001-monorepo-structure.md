# 0001 — Monorepo structure

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The product spans a TypeScript front end and a Python back end that must share a
domain vocabulary (artifact types, validation states, evidence relationships).
We want atomic changes across both, a single place for docs/ADRs/fixtures, and
the option to extract shared code (types, API client) into packages.

## Decision

Use a single repository organized as:

```
apps/       web (Next.js), api (FastAPI)
packages/   domain (shared TS types + Zod), client (typed API client), ui, config
docs/       architecture, adr, api, domain, product
fixtures/   seed scenario shared by seed + tests
```

JS packages are wired with npm workspaces (`@rdc/domain`, `@rdc/client`,
`@rdc/ui`, `@rdc/config`). The Python back end is a self-contained package under
`apps/api` with its own `pyproject.toml`; it does not participate in npm
workspaces but shares the repo, fixtures, and docs.

## Consequences

- Cross-cutting changes (a new artifact type in TS and Python) happen in one PR.
- The shared `fixtures/warehouse_modernization.json` seeds the DB and is asserted
  against in tests, keeping the demo and tests in lockstep.
- Two toolchains (npm + pip) coexist; the `Makefile` provides a unified entry.
- The Python domain and the TS domain are duplicated by necessity (different
  languages) but kept structurally identical and enum-compatible; a future ADR
  may generate one from the other via the OpenAPI schema.
