/**
 * Shared domain types + Zod schemas for the Requirements Discovery Copilot.
 *
 * These mirror the backend Pydantic entities so the web app validates API
 * responses at the boundary and gets end-to-end type safety.
 */
import { z } from "zod";

// --- enums ----------------------------------------------------------------
export const ArtifactType = z.enum([
  "objective",
  "stakeholder_need",
  "requirement",
  "constraint",
  "assumption",
  "risk",
  "decision",
  "open_question",
  "success_metric",
  "integration",
  "stakeholder",
]);
export type ArtifactType = z.infer<typeof ArtifactType>;

export const ValidationState = z.enum([
  "detected",
  "inferred",
  "clarified",
  "customer_confirmed",
  "baselined",
  "rejected",
  "superseded",
  "merged",
]);
export type ValidationState = z.infer<typeof ValidationState>;

export const ArtifactStatus = z.enum([
  "candidate",
  "confirmed",
  "baselined",
  "rejected",
  "superseded",
]);
export type ArtifactStatus = z.infer<typeof ArtifactStatus>;

export const EvidenceRelationship = z.enum([
  "direct",
  "supporting",
  "contradicting",
  "superseding",
  "contextual",
]);
export type EvidenceRelationship = z.infer<typeof EvidenceRelationship>;

export const Speaker = z.enum(["facilitator", "customer", "system", "unknown"]);
export type Speaker = z.infer<typeof Speaker>;

export const CoverageState = z.enum([
  "unanswered",
  "partial",
  "strong",
  "contradictory",
  "needs_validation",
  "confirmed",
]);
export type CoverageState = z.infer<typeof CoverageState>;

// --- entities -------------------------------------------------------------
export const DiscoverySession = z.object({
  id: z.string(),
  title: z.string(),
  customer: z.string(),
  facilitator: z.string(),
  status: z.string(),
  started_at: z.string().nullable().optional(),
  ended_at: z.string().nullable().optional(),
  script_id: z.string().nullable().optional(),
  metadata: z.record(z.unknown()).default({}),
});
export type DiscoverySession = z.infer<typeof DiscoverySession>;

export const TranscriptSegment = z.object({
  id: z.string(),
  session_id: z.string(),
  sequence_number: z.number(),
  speaker: Speaker,
  start_time: z.number().nullable().optional(),
  end_time: z.number().nullable().optional(),
  text: z.string(),
  is_final: z.boolean(),
});
export type TranscriptSegment = z.infer<typeof TranscriptSegment>;

export const DiscoveryArtifact = z.object({
  id: z.string(),
  session_id: z.string(),
  artifact_type: ArtifactType,
  title: z.string(),
  statement: z.string(),
  status: ArtifactStatus,
  confidence: z.number(),
  validation_state: ValidationState,
  derivation_method: z.string(),
  parent_id: z.string().nullable().optional(),
  branch_id: z.string().nullable().optional(),
  rationale: z.string().nullable().optional(),
  superseded_by: z.string().nullable().optional(),
});
export type DiscoveryArtifact = z.infer<typeof DiscoveryArtifact>;

export const EvidenceLink = z.object({
  id: z.string(),
  artifact_id: z.string(),
  transcript_segment_id: z.string(),
  quote_start: z.number(),
  quote_end: z.number(),
  quoted_text: z.string(),
  relationship: EvidenceRelationship,
  confidence: z.number(),
  rationale: z.string().nullable().optional(),
});
export type EvidenceLink = z.infer<typeof EvidenceLink>;

// --- projections ----------------------------------------------------------
export type TreeNode = {
  id: string;
  type: ArtifactType;
  title: string;
  statement: string;
  status: ArtifactStatus;
  confidence: number;
  validation_state: ValidationState;
  evidence_count: number;
  parent_id: string | null;
  children: TreeNode[];
};

export const TreeNodeSchema: z.ZodType<TreeNode> = z.lazy(() =>
  z.object({
    id: z.string(),
    type: ArtifactType,
    title: z.string(),
    statement: z.string(),
    status: ArtifactStatus,
    confidence: z.number(),
    validation_state: ValidationState,
    evidence_count: z.number(),
    parent_id: z.string().nullable(),
    children: z.array(TreeNodeSchema),
  }),
);

export const DiscoveryTree = z.object({
  session_id: z.string(),
  roots: z.array(TreeNodeSchema),
});
export type DiscoveryTree = z.infer<typeof DiscoveryTree>;

export const ConversationNode = z.object({
  id: z.string(),
  branch_id: z.string(),
  node_type: z.string(),
  label: z.string(),
  transcript_segment_id: z.string().nullable().optional(),
  artifact_id: z.string().nullable().optional(),
  parent_node_id: z.string().nullable().optional(),
  sequence: z.number(),
});
export type ConversationNode = z.infer<typeof ConversationNode>;

export const ConversationBranch = z.object({
  id: z.string(),
  session_id: z.string(),
  parent_branch_id: z.string().nullable().optional(),
  source_stage_id: z.string().nullable().optional(),
  name: z.string(),
  topic: z.string(),
  status: z.string(),
  created_from_segment_id: z.string().nullable().optional(),
  merge_target_stage_id: z.string().nullable().optional(),
  nodes: z.array(ConversationNode).default([]),
});
export type ConversationBranch = z.infer<typeof ConversationBranch>;

export const ConversationGraph = z.object({
  session_id: z.string(),
  branches: z.array(ConversationBranch),
});
export type ConversationGraph = z.infer<typeof ConversationGraph>;

export const CoverageCell = z.object({
  stage_id: z.string(),
  state: CoverageState,
  title: z.string().nullable().optional(),
  meta: z.string().nullable().optional(),
});
export type CoverageCell = z.infer<typeof CoverageCell>;

export const CoverageRow = z.object({
  branch_id: z.string(),
  branch: z.string(),
  topic: z.string(),
  cells: z.array(CoverageCell),
});

export const Coverage = z.object({
  session_id: z.string(),
  stages: z.array(z.object({ id: z.string(), title: z.string(), sequence: z.number() })),
  rows: z.array(CoverageRow),
  summary: z.object({
    counts: z.record(z.number()),
    total_cells: z.number(),
    coverage_percent: z.number(),
  }),
});
export type Coverage = z.infer<typeof Coverage>;

export const ScriptStage = z.object({
  id: z.string(),
  script_id: z.string(),
  sequence: z.number(),
  title: z.string(),
  objective: z.string(),
  primary_prompt: z.string(),
  alternative_prompts: z.array(z.string()),
  completion_criteria: z.array(z.string()),
});
export type ScriptStage = z.infer<typeof ScriptStage>;

export const ScriptDefinition = z.object({
  id: z.string(),
  name: z.string(),
  version: z.string(),
  description: z.string(),
  stages: z.array(ScriptStage),
});
export type ScriptDefinition = z.infer<typeof ScriptDefinition>;

export const ScriptState = z.object({
  script: ScriptDefinition,
  current_index: z.number(),
  current_stage: ScriptStage.nullable(),
  completed_stage_ids: z.array(z.string()),
  total_stages: z.number(),
});
export type ScriptState = z.infer<typeof ScriptState>;

export const RecommendedQuestion = z.object({
  rank: z.number(),
  question: z.string(),
  why: z.string(),
});
export const Recommendations = z.object({
  session_id: z.string(),
  questions: z.array(RecommendedQuestion),
  gaps: z.array(z.object({ title: z.string(), body: z.string() })),
});
export type Recommendations = z.infer<typeof Recommendations>;

// --- streaming events -----------------------------------------------------
export const DomainEventFrame = z.object({
  id: z.string(),
  type: z.string(),
  session_id: z.string(),
  payload: z.record(z.unknown()),
  occurred_at: z.string(),
});
export type DomainEventFrame = z.infer<typeof DomainEventFrame>;
