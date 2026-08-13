# 0003 — PostgreSQL persistence

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The domain is relational: sessions own segments/artifacts/branches; artifacts
link to evidence and revisions; branches own nodes. We need referential
integrity, transactional writes (an artifact + its evidence + a revision), and
JSON fields for flexible metadata and coverage maps.

## Decision

Use PostgreSQL as the primary datastore via SQLAlchemy 2.0 (typed ORM) with
Alembic migrations. Enum values are stored as strings for portability; flexible
fields (`metadata`, coverage map, revision snapshots) use JSON columns. A
SQLite fallback (`sqlite+pysqlite`) is supported for tests and keyless local
runs, using the same models and `create_all()`.

## Consequences

- Strong integrity and transactions for evidence-first traceability.
- Alembic gives reproducible schema evolution; `0001_initial` creates the full
  schema and is applied in Docker before the app starts.
- JSON columns keep the schema stable while metadata evolves, at the cost of
  weaker query-time typing for those fields.
- The SQLite fallback trades some fidelity (types, concurrency) for a
  zero-dependency test/demo path; migrations target Postgres semantics with
  `render_as_batch=True` for SQLite compatibility.
