# Backlog

Grouped by increment. The MVP items are delivered in this repository; later
groups are planned.

## MVP (this increment — delivered)

- [x] Monorepo scaffold (apps + packages + docs + fixtures)
- [x] Domain model: entities, enums, events, lifecycle rules
- [x] PostgreSQL schema + Alembic migration + SQLite fallback
- [x] Provider interfaces + mock STT/LLM/embedding implementations
- [x] Services: session, transcript, analysis, artifact, tree, branch, script,
      coverage, recommendation, export
- [x] Versioned REST API + OpenAPI + WebSocket stream
- [x] Provider-neutral audio WebSocket + local/OpenAI/Wispr STT adapters
- [x] Seeded warehouse-modernization demo session
- [x] Web app: six visualizations, human confirmation workflow
- [x] JSON + Markdown export with traceability appendix
- [x] Backend + frontend tests + one end-to-end scenario
- [x] Docker Compose, Makefile, `.env.example`, README + architecture + ADRs

## Increment 2

- [ ] LLM-backed derivation behind `LanguageModelProvider` (with prompt/versioning)
- [ ] Authentication + role-based access control enforcement
- [ ] Interactive branch editing with React Flow (drag re-parent, zoom/pan)
- [ ] CSV and DOCX exporters
- [ ] Artifact edit UI (inline PATCH) + merge/supersede UI flows
- [ ] Coverage derivation improvements for live (non-seeded) sessions

## Increment 3

- [ ] Multi-facilitator real-time collaboration (shared cursor/selection)
- [ ] Embeddings-based artifact clustering + duplicate detection
- [ ] Transcript redaction pipeline + retention purge job
- [ ] Append-only audit log for confirm/reject/edit/export
- [ ] Session templates + reusable script library management UI

## Future integrations

- [ ] ReqIF export/round-trip
- [ ] Jira issue creation from confirmed requirements
- [ ] IBM DOORS / DOORS Next integration
- [ ] SysML model fragment export
- [ ] Enterprise SSO (SAML/OIDC) and per-tenant data isolation
