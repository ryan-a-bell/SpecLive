# API Guide

Base URL: `http://localhost:8000` — interactive OpenAPI docs at `/docs`,
schema at `/openapi.json`. All endpoints are under `/api/v1`.

## Conventions

- IDs are strings (UUIDs for new entities; the seed uses semantic ids like
  `REQ-002`).
- Errors return `{ "detail": "..." }` with status:
  `404` not found, `422` validation error, `409` illegal lifecycle transition.
- Enums use snake_case string values (e.g. `stakeholder_need`, `customer_confirmed`).

## Endpoints

### Sessions

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/sessions` | Create a session |
| GET | `/api/v1/sessions` | List sessions |
| GET | `/api/v1/sessions/{id}` | Get a session |
| PATCH | `/api/v1/sessions/{id}` | Update title/status/metadata |

### Workspaces (cross-session context)

A **workspace** groups the discovery conversations that share a customer.
There is no separate workspace entity yet — it is derived from the sessions
list (mirroring the web app's grouping), so a workspace id is the slug of the
customer name (e.g. `Acme Logistics` → `acme-logistics`). These endpoints
aggregate every conversation in a workspace into one context bundle an
external tool — or an LLM architecting in another app — can pull.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/workspaces` | List workspaces and their conversations |
| GET | `/api/v1/workspaces/{id}/context?scope=all\|baseline&format=json\|markdown` | Aggregated requirements + full context |

`scope` is the "depending on query type" knob:

- `scope=baseline` — **only human-confirmed** items (`customer_confirmed` /
  `baselined`). This is the set safe to architect *against*; no automated
  path can reach these states.
- `scope=all` (default) — also includes still-unconfirmed candidates, each
  carrying its `validation_state` and `confidence` so a consumer can weigh
  how much to trust it.

The bundle carries the same sections as the per-session discovery package
(objectives, stakeholder needs, confirmed/candidate requirements, constraints,
assumptions, risks, decisions, open questions, success metrics, branch summary,
and a `traceability` array linking each item to its source transcript
evidence). Every aggregated item is additionally tagged with
`source_session_id` / `source_session_title`. Requirements are aggregated
across sessions, **not** de-duplicated (semantic clustering is future work).

```http
GET /api/v1/workspaces/acme-logistics/context?scope=baseline
```

```json
{ "workspace": { "id": "acme-logistics", "name": "Acme Logistics",
                 "session_count": 2, "sessions": [ … ] },
  "scope": "baseline",
  "executive_summary": "Aggregated discovery context for Acme Logistics …",
  "confirmed_requirements": [ { "id": "REQ-…", "title": "…", "statement": "…",
      "confidence": 0.9, "validation_state": "customer_confirmed",
      "source_session_id": "…", "source_session_title": "…" } ],
  "candidate_requirements": [],
  "constraints": [ … ], "risks": [ … ], "open_questions": [ … ],
  "traceability": [ { "artifact_id": "…", "evidence": [ … ],
      "source_session_id": "…" } ] }
```

### Transcript

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/sessions/{id}/transcript` | Append a segment |
| GET | `/api/v1/sessions/{id}/transcript` | List segments |
| GET | `/api/v1/sessions/{id}/evidence` | All evidence links (for highlighting) |

### Artifacts & evidence

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/sessions/{id}/artifacts` | List artifacts |
| POST | `/api/v1/sessions/{id}/artifacts` | Create an artifact (manual) |
| GET | `/api/v1/artifacts/{id}` | Get an artifact |
| PATCH | `/api/v1/artifacts/{id}` | Edit (records a revision) |
| GET | `/api/v1/artifacts/{id}/evidence` | List evidence |
| POST | `/api/v1/artifacts/{id}/evidence` | Add evidence link |
| GET | `/api/v1/artifacts/{id}/revisions` | List revisions |
| POST | `/api/v1/artifacts/{id}/confirm` | Confirm (human action) |
| POST | `/api/v1/artifacts/{id}/reject` | Reject |
| POST | `/api/v1/artifacts/{id}/merge` | Merge into another artifact |

### Projections, script, analysis, export

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/sessions/{id}/discovery-tree` | Discovery tree |
| GET | `/api/v1/sessions/{id}/conversation-graph` | Branches + nodes |
| GET | `/api/v1/sessions/{id}/coverage` | Coverage matrix |
| GET | `/api/v1/sessions/{id}/recommendations` | Next questions + gaps |
| GET | `/api/v1/scripts` · `/api/v1/scripts/{id}` | Script catalogue |
| GET | `/api/v1/sessions/{id}/script` | Current script state |
| POST | `/api/v1/sessions/{id}/script/advance` | Advance a stage |
| POST | `/api/v1/sessions/{id}/analyze` | Derive candidate artifacts |
| GET | `/api/v1/sessions/{id}/export?format=json\|markdown` | Discovery package |
| WS | `/api/v1/sessions/{id}/stream` | Live event frames |
| WS | `/api/v1/sessions/{id}/audio` | PCM audio in; normalized transcript events out |

## Sample payloads

### Create a session

```http
POST /api/v1/sessions
Content-Type: application/json

{ "title": "Warehouse Modernization Discovery",
  "customer": "Acme Logistics",
  "facilitator": "Ryan",
  "script_id": "SCRIPT-WAREHOUSE" }
```

```json
{ "id": "8f3c…", "title": "Warehouse Modernization Discovery",
  "customer": "Acme Logistics", "facilitator": "Ryan",
  "status": "active", "script_id": "SCRIPT-WAREHOUSE", "metadata": {} }
```

### Append a transcript segment

```http
POST /api/v1/sessions/{id}/transcript
{ "speaker": "customer",
  "text": "Ideally within 30 seconds. Anything over a couple of minutes is too stale." }
```

```json
{ "id": "…", "session_id": "…", "sequence_number": 4, "speaker": "customer",
  "text": "Ideally within 30 seconds…", "is_final": true }
```

### Analyze (mock derivation)

```http
POST /api/v1/sessions/{id}/analyze
```

```json
[
  { "id": "…", "artifact_type": "requirement",
    "title": "Quantified freshness target",
    "statement": "The solution shall refresh information within 30 seconds of a source-system change.",
    "status": "candidate", "confidence": 0.91,
    "validation_state": "inferred", "derivation_method": "keyword_heuristic" }
]
```

### Confirm an artifact (human action)

```http
POST /api/v1/artifacts/REQ-002/confirm
```

```json
{ "id": "REQ-002", "validation_state": "customer_confirmed", "status": "confirmed" }
```

Attempting to confirm from an automated path is impossible; a disallowed
transition returns `409`.

### Add an evidence link

```http
POST /api/v1/artifacts/REQ-002/evidence
{ "transcript_segment_id": "SEG-104",
  "quote_start": 8, "quote_end": 25, "quoted_text": "within 30 seconds",
  "relationship": "direct", "confidence": 0.95 }
```

### Streaming frame (WebSocket)

```json
{ "id": "…", "type": "artifact.candidate.created",
  "session_id": "…", "payload": { "id": "…", "artifact_type": "constraint", "…": "…" },
  "occurred_at": "2026-08-13T18:37:00Z" }
```

### Live transcription (WebSocket)

The browser can first query the provider-neutral capability endpoint:

```http
GET /api/v1/transcription/status
```

```json
{ "available": true, "supports_partials": true, "supports_speaker_detection": true,
  "audio": { "encoding": "pcm_s16le", "sample_rate": 16000, "channels": 1 },
  "max_frame_seconds": 5 }
```

This intentionally omits the configured provider and all provider credentials.

After `transcription.ready`, select speaker behavior before sending audio:

```json
{ "type": "configure", "speaker_mode": "auto" }
```

or stamp a known person manually:

```json
{ "type": "configure", "speaker_mode": "manual",
  "speaker": "facilitator", "speaker_id": "manual:ryan",
  "speaker_name": "Ryan" }
```

Connect to `/api/v1/sessions/{id}/audio`. The server first sends the canonical
audio contract:

```json
{ "type": "transcription.ready", "session_id": "...",
  "audio": { "encoding": "pcm_s16le", "sample_rate": 16000, "channels": 1 } }
```

Send binary mono PCM16 frames (no JSON/base64 wrapper). Keep frame durations
consistent and no longer than five seconds. SpecLive returns provider-neutral
events:

```json
{ "type": "transcript.partial", "session_id": "...", "segment_id": "...",
  "text": "The customer needs", "is_final": false,
  "speaker": "unknown", "speaker_id": "voice-1", "speaker_name": "Voice 1",
  "speaker_source": "detected", "speaker_confidence": 0.94,
  "start_time": null, "end_time": null }
```

Finish with `{ "type": "stop" }`. The final event uses the same shape with
`type: "transcript.final"` and `is_final: true`; final text is persisted by the
API. Provider names, protocols, credentials, and audio requirements never cross
this browser-facing boundary.

Correct one segment—or every segment grouped under the same `speaker_id`—with:

```http
PATCH /api/v1/sessions/{id}/transcript/{segment_id}/speaker
{ "speaker": "customer", "speaker_name": "Maya", "apply_to_voice": true }
```
