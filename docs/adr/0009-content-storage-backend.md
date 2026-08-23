# 0009 — Content storage backend (recordings, transcripts, requirements, exports)

- **Status:** Accepted
- **Date:** 2026-08-23

## Context

Discovery calls produce more than structured records: a raw **recording**, a
**transcript**, the **derived requirements**, and exported **discovery
packages**. Until now the canonical structured data (sessions, segments,
artifacts, evidence) lived in the relational database and the raw audio was
discarded after transcription — nothing persisted the recording, and there was
no configurable, browsable home for the per-conversation content.

We want a **global setting** that decides *where* this content is persisted,
defaulting to a local directory but allowing a single database-backed store,
without leaking the choice into every call site. Binary blobs (audio) and
structured data have different needs: large audio in Postgres bloats backups and
is slow to stream, so the database option is offered for single-store simplicity,
not as the recommended home for big media.

Per-workspace / per-conversation overrides are explicitly **out of scope** for
this increment (tracked as a follow-up issue); the resolver is global-only.

## Decision

Introduce a provider-neutral **`ContentStore`** port (mirroring the existing
`SpeechToTextProvider` / `ArtifactExporter` abstractions) with two backends:

- **`local`** (default) — a directory tree rooted at `STORAGE_LOCAL_ROOT`.
- **`database`** — rows in a `stored_blobs` table keyed by the same relative path.

A single **layout module** (`app/storage/layout.py`) owns the on-disk scheme so
both backends are interchangeable and a future object-store (S3) backend is a
small addition behind the same port. The layout keys each conversation on its
immutable `session_id` (not a sequential number), separates **write-once raw**
content from **regenerable derived** content, and records provenance +
checksums in a per-conversation `manifest.json`:

```
<root>/
├── .speclive-storage.json                     # layout schema-version marker
└── workspaces/<workspace_id>/
    ├── workspace.json
    └── conversations/<yyyymmdd>-<slug>-<session_id>/
        ├── manifest.json                       # index + provenance + checksums
        ├── raw/recording.<ext> + recording.meta.json   # write-once
        ├── transcript/segments.json + transcript.md
        ├── requirements/artifacts.json + evidence.json
        └── exports/discovery-package-<ts>.{json,md}    # timestamped history
```

`STORAGE_BACKEND`, `STORAGE_LOCAL_ROOT`, and `STORAGE_PERSIST_AUDIO` are
env-driven global settings. A `ConversationStorageService.snapshot()` writes the
whole tree (regenerating transcript/requirements/exports from the DB each time),
and uploading a recording via `POST /sessions/{id}/transcribe` triggers a
best-effort snapshot with that audio. `GET /api/v1/settings/storage` reports the
active configuration (no secrets), matching the existing `/settings/analysis`
pattern.

## Consequences

- Recordings are now persisted (when `STORAGE_PERSIST_AUDIO=true`) where they are
  captured, alongside a manifest that traces which STT/LLM providers produced the
  derived content — consistent with the product's evidence-first stance.
- The default (`local`) keeps large audio out of the database and makes the tree
  directly browsable and backup-friendly; `database` exists for deployments that
  want one backing store.
- Structured data remains authoritative in the relational DB; the stored files
  are content sidecars, safe to regenerate.
- Secrets (API keys) are never written into `manifest.json`, `workspace.json`, or
  the settings endpoint.
- Per-workspace/per-conversation overrides and lifecycle/retention-per-kind are
  deferred (follow-up issue); the global resolver leaves room for them to layer
  on without changing callers.
