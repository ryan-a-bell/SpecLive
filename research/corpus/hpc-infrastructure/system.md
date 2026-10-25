# Ground-truth system: Helios Genomics HPC infrastructure

Round-trip anchor for a **three-speaker** discovery call (facilitator + two
customer-side stakeholders with different lenses: budget owner Marcus, systems
lead Elena). Tests derivation across multiple non-facilitator speakers.

## Context

Genomics workloads tripled in a year; researchers wait days in the queue and the
team burns cash on rented cloud GPUs. They must decide on-prem vs cloud vs
hybrid, with a hard compliance boundary on patient-derived data.

## Objective

- **O1 — Throughput at predictable, defensible cost.** Cut queue wait without an
  unpredictable cloud burn rate.

## Requirements

- **R1 — Fair-share + preemption scheduling.** Replace the hand-tuned Slurm setup
  that lets one big job starve everyone.
- **R2 — Scalable parallel filesystem.** Scale past the current NFS I/O ceiling
  (~40 nodes).
- **R3 — Path to low-latency interconnect.** The design must accommodate a
  low-latency fabric (InfiniBand) for committed tightly-coupled protein-folding
  jobs, even if not bought on day one.
- **R4 — Enforced, auditable multi-tenant isolation** on both compute and storage.

## Constraints

- **C1 — Three-year TCO must beat cloud.** On-prem only if predictable three-year
  spend wins; not chasing the cheapest month.
- **C2 — Power & cooling gate.** Any on-prem build is gated by facilities capacity
  (dense GPU racks pull 30–40 kW; the room is provisioned for ~12 kW/rack) — a
  facilities project (liquid cooling), not just procurement.
- **C3 — Auditable compliance.** Patient-derived genomic data must be auditable
  from day one; this is the top-ranked constraint, above raw throughput.

## Decision

- **D1 — Protein-folding initiative is committed** (board-approved), which is what
  promotes R3 from a maybe to a requirement.

## Risk

- **RISK1 — Facilities timeline.** An on-prem build is a facilities project with
  liquid cooling on a months-not-weeks timeline.
