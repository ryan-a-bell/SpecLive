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
