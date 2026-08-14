# MVP Scope

## Problem

During live customer discovery calls, facilitators struggle to capture needs and
requirements while staying present in the conversation. The resulting notes are
often untraceable, prematurely "confirmed," or disconnected from what was
actually said.

## MVP goal

Give a facilitator a copilot that, during a single discovery session, derives
candidate discovery artifacts from the transcript, keeps each traceable to its
evidence, follows a configurable script with answer-driven branches, and
produces a structured, traceable discovery package — with all inferences
requiring explicit human confirmation.

## In scope (this increment)

- Create/open a discovery session anchored on a discovery script.
- Static or simulated streaming transcript ingestion.
- Mock-backed derivation of objectives, needs, requirements, constraints,
  assumptions, risks, decisions, open questions, success metrics, integrations.
- First-class evidence links with typed relationships and exact quote offsets.
- Live discovery tree, guided script panel, recommended questions + gaps.
- Git-style branch view, conversation subway, coverage matrix.
- Human confirmation workflow (confirm / reject / edit / merge) with revisions.
- JSON + Markdown discovery-package export.
- PostgreSQL schema + migrations, seeded demo, Docker Compose, tests, docs.

## Out of scope (later increments)

- Real speech-to-text ingestion and LLM-backed derivation.
- Authentication, role-based access enforcement, audit log, redaction pipeline.
- Interactive graph editing (drag/zoom) — see ADR-0008.
- CSV/DOCX/ReqIF/Jira/DOORS/SysML exporters.
- Multi-facilitator real-time collaboration.

## Success criteria

- The seeded demo session reproduces the prototype's information architecture.
- A statement added in the composer produces a traceable candidate artifact.
- No automated path can mark an artifact customer-confirmed.
- The exported package contains every required section with a traceability
  appendix linking artifacts to evidence.
