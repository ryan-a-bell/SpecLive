# 0004 — Provider abstraction for STT and LLM services

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The system must not couple to a single speech-to-text or language-model vendor,
and it must run without any API keys for development, demos, and CI. Customer
transcript data is sensitive, so the egress surface must be explicit.

## Decision

Define narrow provider interfaces — `SpeechToTextProvider`,
`LanguageModelProvider`, `EmbeddingProvider`, `ArtifactExporter`,
`SessionRepository`, `EventBus` — in the back end. Services depend only on these
interfaces. Concrete providers are resolved by a registry keyed on
configuration (`STT_PROVIDER`, `LLM_PROVIDER`, …). The MVP ships mock
implementations that perform **no network egress**: `MockLanguageModelProvider`
derives artifacts with transparent keyword/regex heuristics.

## Consequences

- The whole stack runs key-free and offline; CI is deterministic.
- A real vendor is added by implementing one interface and registering it — no
  service or domain change.
- The provider layer is the single, auditable egress point for customer data,
  supporting the trust-boundary controls in `SECURITY.md`.
- Mock heuristics are not a real model; confidence values are illustrative and
  must not be presented as model outputs (documented in the README limitations).
