# 0008 — Graph visualization library selection

- **Status:** Accepted
- **Date:** 2026-08-13

## Context

The product requires several graph-like visualizations: the discovery tree, the
git-style branch view, the conversation subway, and the coverage matrix. The
brief suggests React Flow "or an equivalent graph library." The supplied
prototype implements all of these with hand-authored CSS grid/flow layouts that
have a specific, deliberate visual language.

## Decision

For this increment, implement the four visualizations as **lightweight custom
React components over CSS grid/flex** that reproduce the prototype's exact visual
language, rather than adopting React Flow now. The layout data (lanes, columns,
stations, cells) comes from the typed `conversation-graph` and `coverage`
projections, so the rendering is data-driven and swappable.

React Flow (or an equivalent) is the intended library for **Increment 2**, when
the branch view becomes interactively editable (drag to re-parent, zoom/pan,
node handles) — capabilities the current static-but-live views don't yet need.

## Consequences

- Pixel-faithful to the prototype with no heavy graph dependency in the MVP; the
  bundle stays small.
- The projections (`GET /conversation-graph`, `/coverage`, `/discovery-tree`) are
  the stable contract; switching to React Flow later is a rendering-layer change,
  not a data change.
- Custom layout code must handle lane/column math (documented in the viz
  components); this is acceptable for the fixed, small graphs of a single call.
- This is the "adjust the structure when technically justified" case the brief
  allows, recorded here as required.
