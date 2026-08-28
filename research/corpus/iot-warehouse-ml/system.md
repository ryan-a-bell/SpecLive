# Ground-truth system: Northwind Fulfillment — IoT predictive-maintenance ML pipeline

This is the **known system** the discovery transcript describes. It is the
round-trip anchor: the transcript was recorded while the customer described this
system, so a faithful transcript→requirements methodology should recover the
requirements below. `gold.json` is this narrative distilled into scoreable rows.

## Context

Northwind Fulfillment runs three warehouse buildings instrumented with ~4,000
IoT sensors (temperature, humidity, conveyor vibration, RFID reads at pick
faces). Telemetry streams into an MQTT broker and lands in an unpruned
time-series database. They want a machine-learning pipeline that turns this
telemetry into actionable predictive-maintenance alerts.

## Objectives

- **O1 — Reduce unplanned downtime.** Predict conveyor-motor failure early
  enough to service off-shift instead of losing a line mid-day. This is the
  primary business outcome.

## Requirements

- **R1 — Advance-warning window.** The pipeline shall predict an impending
  conveyor-motor failure with **12–24 hours** of lead time.
- **R2 — Edge inference.** Model scoring shall run **at the edge**, local to the
  conveyors, and continue to fire alerts during WAN/connectivity loss (buildings
  lose connectivity several times a week).
- **R3 — Cloud training.** Model *training* may run in the cloud; only inference
  must be local.
- **R4 — Drift detection.** The pipeline shall detect model-accuracy drift over
  time (there is no monitoring today; degradation is currently invisible).
- **R5 — Automated retraining loop.** The pipeline shall retrain without a
  data-scientist in the loop each week (no in-house ML team to babysit it).
- **R6 — Recall-biased alerting.** Alerting shall favor **recall over
  precision** — over-alert early, tighten the threshold once trusted — because a
  missed failure costs a five-figure day while a false alarm costs ~an hour of a
  technician's time.

## Constraints

- **C1 — Robustness to bad data.** Features must tolerate missing windows,
  offline sensors, drifting clocks between buildings, and unmapped sensors
  (~1/3 were never mapped to a specific motor).
- **C2 — EU data residency.** Data for EU sites must stay in-region.
- **C3 — Worker-identity privacy.** RFID picker IDs (which tie telemetry back to
  an individual worker's badge) must not leave the site / must not be sent to the
  cloud.

## Success metric

- **M1 — Cost model / alert economics.** Success is framed by the asymmetric
  cost: a missed failure ≈ five-figure day lost; a false alarm ≈ one technician
  hour. This both justifies R6 and is the yardstick for tuning thresholds.

## Open questions / gaps (present in the system today)

- **Q1 — No monitoring exists** to know when the model has drifted; the current
  state is "find out from a failure we didn't catch." (Directly motivates R4.)

## Assumptions to validate

- **A1 — Self-serve pipeline.** The pipeline is assumed to be largely
  self-serve (automated retraining + alerting), because there is no ML team to
  operate it. Flagged in-call as an assumption to confirm. (Relates to R5.)
