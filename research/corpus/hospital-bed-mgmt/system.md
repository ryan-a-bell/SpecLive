# Ground-truth system: Ridgeline Health bed-management modernization

Round-trip anchor for a **single-speaker (monologue) transcript** — no
facilitator turns, so it exercises requirement derivation from unstructured
narrative rather than Q&A.

## Context

Ridgeline Health's ER misses its four-hour boarding target more than a third of
the time, causing ambulance diversions (lost revenue + patient-safety risk). Bed
assignment is manual: on discharge the nurse marks the EHR but housekeeping is
not auto-notified; a coordinator works a whiteboard and phone across 412 beds.
Exception rules (isolation, pediatric, post-surgical) live only in the
coordinator's head. The goal is a real-time, rule-aware bed-availability layer on
top of Epic.

## Objective

- **O1 — Halve ER boarding time.** Board target: under two hours (from ~5).

## Stakeholder needs

- **N1 — Rule-aware availability view.** The bed coordinator needs a real-time,
  rule-aware view of bed availability.
- **N2 — Vacancy notification.** Environmental services needs a notification the
  moment a room is vacated.

## Requirements

- **R1 — Automatic housekeeping notification** on discharge (today it is a manual
  call/page).
- **R2 — Encode exception rules** (isolation room type, pediatric, post-surgical
  proximity) in the system, not the coordinator's head.
- **R3 — Epic/HL7 integration** as a consumer of bed-status + ADT events.
- **R4 — HIPAA-scoped, system-enforced visibility** (housekeeping sees room +
  cleaning status, not diagnosis or name).

## Constraints

- **C1 — Do not replace Epic** (Epic stays the system of record).
- **C2 — Device/connectivity limits** (Android handhelds without data plan; Wi-Fi
  does not reach the sub-basement).
- **C3 — Five-month delivery** (capital this fiscal year; live before end of June).
- **C4 — User adoption / staff trust** is itself a requirement (past rollouts
  failed on trust).

## Success metrics

- **M1 — ER boarding time** (from ~5h toward <2h).
- **M2 — Bed turnover time** (90 min → <40).
- **M3 — Ambulance diversion hours** (drop ≥50% within two quarters of go-live).

## Open questions

- **Q1 — EVS channel:** mobile app vs SMS/paging trigger.
- **Q2 — Reservation vs available:** a clean bed held for an incoming transfer.
