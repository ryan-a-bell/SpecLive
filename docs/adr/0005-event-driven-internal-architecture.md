# 0005 — Event-driven internal architecture

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The UI must update in real time as segments arrive, artifacts are derived,
evidence is linked, and coverage changes. We want to stream these today but keep
the option of a queue/worker architecture later, without rewriting services.

## Decision

Introduce an internal `EventBus` abstraction and typed `DomainEvent`s
(`transcript.segment.received`, `artifact.candidate.created`,
`artifact.confirmed`, `evidence.link.created`, `branch.created`,
`coverage.updated`, …). Services publish events synchronously; an in-memory bus
delivers them to synchronous handlers and to per-session async queues consumed
by the WebSocket layer. `DomainEvent.to_wire()` defines the transport frame.

## Decision detail: sync now, queue-ready

`publish()` is synchronous because the in-memory implementation does no real I/O.
The interface is unchanged for a future Redis/queue implementation that enqueues
synchronously and delivers asynchronously.

## Consequences

- The MVP runs entirely in-process — simple to test and deploy.
- The same event frames feed the WebSocket and could feed a durable queue later.
- Publishing must never break a request: handler exceptions are caught and
  logged, not propagated.
- Ordering and delivery guarantees are best-effort in-memory; a durable bus would
  add these when introduced.
