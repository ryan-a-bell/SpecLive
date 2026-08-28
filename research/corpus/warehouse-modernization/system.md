# Ground-truth system: warehouse picking-visibility modernization

The round-trip anchor for this case. Distilled from the seeded demo scenario
(`fixtures/warehouse_modernization.json`), whose hand-authored artifacts + evidence
are the source of `gold.json`. A faithful methodology should recover these from
the transcript.

## Context

A distribution warehouse runs order picking against an existing Warehouse
Management System (WMS). Supervisors lack a reliable real-time view of where
orders are in the picking process and only learn about delays after a truck is
already waiting at the dock. Floor leads carry rugged tablets. The goal is a
real-time, rule-aware picking-visibility layer on top of the WMS — not a WMS
replacement.

## Objective

- **OBJ-001 — Improve warehouse flow.** Improve flow and prevent avoidable
  truck-loading delays.

## Stakeholder need

- **NEED-001 — Timely operational visibility.** Supervisors need timely
  visibility into order status throughout picking.

## Requirements

- **REQ-002 — 30-second refresh.** Refresh order-status information within 30
  seconds of a source-system change.
- **REQ-010 — Role-based reassignment.** Only shift supervisors may reassign
  picks; floor staff have read-only status access.
- **REQ-012 — Offline operation + sync.** Continue core status functions during
  connectivity loss and reconcile on reconnection.

## Constraints

- **CON-003 — Existing rugged tablets.** Must run on the rugged tablets floor
  leads already carry.
- **CON-004 — Retain current WMS.** Must integrate with the existing WMS without
  replacing it this fiscal year.
- **CON-008 — Q3 go-live.** Must be live before the end of Q3, ahead of peak
  season.

## Risk

- **RISK-007 — Integration latency.** Available WMS interfaces may not support a
  30-second end-to-end refresh.

## Success metric

- **SM-013 — Reduced loading delays.** Reduction in truck wait time caused by
  late picking visibility. *(No transcript evidence span in the fixture, so not
  in the scoreable gold set.)*

## Open questions

- **Q-005 — Which order states matter?** Which states, exceptions, and alerts
  must supervisors see.
- **Q-006 — Degraded-connectivity functions.** Which functions must remain
  available during degraded connectivity, and for how long.

## Assumption

- **ASSUMP-011 — Local caching.** Tablets can cache order data locally during
  short outages. *(No evidence span in the fixture; excluded from scoreable gold.)*
