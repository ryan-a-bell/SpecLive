/**
 * Shared UI tokens and helpers.
 *
 * The MVP keeps this deliberately small: the design tokens that both the web
 * app and any future shared components consume. Presentational primitives
 * (Panel, Badge, etc.) live in `apps/web/components/ui` until a second consumer
 * justifies promoting them here.
 */

export const artifactColor: Record<string, string> = {
  objective: "#b693ff",
  stakeholder_need: "#67a8ff",
  requirement: "#64d69b",
  constraint: "#ffab68",
  risk: "#ff7f8f",
  assumption: "#9eb0c7",
  open_question: "#ffd36f",
  decision: "#67a8ff",
  success_metric: "#64d69b",
  integration: "#ffab68",
  stakeholder: "#b693ff",
};

export const evidenceColor: Record<string, string> = {
  direct: "#67a8ff",
  supporting: "#64d69b",
  contradicting: "#ff7f8f",
  superseding: "#b693ff",
  contextual: "#ffab68",
};

export const coverageClass: Record<string, string> = {
  strong: "coverage-high",
  confirmed: "coverage-high",
  partial: "coverage-med",
  needs_validation: "coverage-med",
  contradictory: "coverage-low",
  unanswered: "",
};
