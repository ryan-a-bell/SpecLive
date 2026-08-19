"use client";

import { useMemo } from "react";
import { useConversationGraph, useScriptState } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";

type Graph = NonNullable<ReturnType<typeof useConversationGraph>["data"]>;
type ConversationBranch = Graph["branches"][number];
type ConversationNode = NonNullable<ConversationBranch["nodes"]>[number];

/**
 * Q&A flow — the questions the facilitator (SE) asks and the answers the
 * customer gives, read top-to-bottom in conversation order. The main script is
 * pinned to the left; answer-driven follow-ups branch to the right, indenting
 * one level per depth. Mirrors the "effective Q&A flow during technical
 * discovery" diagram, driven by the live conversation graph.
 *
 *   • Question asked by the facilitator  →  gray dot + "Q{n}"
 *   • Answer from the customer           →  circled "A"
 *   • Derived artifact (requirement …)   →  small colored chip
 *
 * Clicking a row selects its artifact / transcript segment so the companion
 * transcript highlights the supporting evidence.
 */

const ROW_H = 46; // vertical space per row (conversation order)
const DEPTH_X = 30; // indent per branch-nesting level
const TOP = 16;
const LEFT = 14;
const CHIP_H = 28;
const GLYPH_DX = 9; // glyph centre offset from the row's left edge

type StepKind = "qa" | "answer" | "artifact";

interface Step {
  id: string;
  kind: StepKind;
  qNum?: number;
  question?: ConversationNode;
  answer?: ConversationNode;
  node: ConversationNode; // primary node (question for "qa", else the node itself)
  depth: number;
  row: number;
  /** id of the step this one flows from within its thread, if any */
  flowFrom?: string;
  /** id of the parent step a branch drops down from, if any */
  branchFrom?: string;
}

const ARTIFACT_COLOR: Record<string, string> = {
  requirement: "var(--green)",
  finding: "var(--blue)",
  risk: "var(--red)",
  decision: "var(--purple)",
  merge: "var(--muted)",
};

const isQuestion = (n: ConversationNode) =>
  n.node_type === "question" || n.node_type === "script_stage";

/** Collapse a branch's ordered nodes into Q→A steps (and standalone chips). */
function stepsForBranch(
  branch: ConversationBranch,
): Pick<Step, "id" | "kind" | "question" | "answer" | "node">[] {
  const nodes = [...(branch.nodes ?? [])].sort((a, b) => a.sequence - b.sequence);
  const out: Pick<Step, "id" | "kind" | "question" | "answer" | "node">[] = [];
  for (let i = 0; i < nodes.length; i += 1) {
    const node = nodes[i];
    if (!node) continue;
    if (isQuestion(node)) {
      const next = nodes[i + 1];
      const answer = next && next.node_type === "answer" ? next : undefined;
      if (answer) i += 1; // consume the paired answer
      out.push({ id: node.id, kind: "qa", question: node, answer, node });
    } else if (node.node_type === "answer") {
      out.push({ id: node.id, kind: "answer", node });
    } else {
      out.push({ id: node.id, kind: "artifact", node });
    }
  }
  return out;
}

function truncate(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function QAFlowView({ sessionId }: { sessionId: string }) {
  const graph = useConversationGraph(sessionId);
  const script = useScriptState(sessionId);
  const selectArtifact = useWorkspaceStore((s) => s.selectArtifact);
  const selectSegment = useWorkspaceStore((s) => s.selectSegment);
  const selectedArtifactId = useWorkspaceStore((s) => s.selectedArtifactId);
  const selectedSegmentId = useWorkspaceStore((s) => s.selectedSegmentId);

  const stages = script.data?.script.stages;

  const { steps, rows } = useMemo(() => {
    const branches = graph.data?.branches ?? [];
    if (branches.length === 0) return { steps: [] as Step[], rows: 0 };

    const main =
      branches.find((b) => b.topic === "main_script") ??
      branches.find((b) => (b.parent_branch_id ?? null) === null) ??
      branches[0];
    if (!main) return { steps: [] as Step[], rows: 0 };

    // A branch names the *script stage* it was spawned from (e.g. "STAGE-3"),
    // not a conversation-node id — resolve that to the stage's position and
    // attach the branch beneath the matching step on the main spine.
    const stageIndexById = new Map((stages ?? []).map((s, i) => [s.id, i]));
    const childrenOfStageIndex = new Map<number, ConversationBranch[]>();
    const childrenOfBranch = new Map<string, ConversationBranch[]>();
    for (const b of branches) {
      if (b.id === main.id) continue;
      if (b.parent_branch_id) {
        const list = childrenOfBranch.get(b.parent_branch_id) ?? [];
        list.push(b);
        childrenOfBranch.set(b.parent_branch_id, list);
      } else if (b.source_stage_id && stageIndexById.has(b.source_stage_id)) {
        const idx = stageIndexById.get(b.source_stage_id)!;
        const list = childrenOfStageIndex.get(idx) ?? [];
        list.push(b);
        childrenOfStageIndex.set(idx, list);
      }
    }

    const laid: Step[] = [];
    let row = 0;
    let qCounter = 0;

    const emitBranch = (
      branch: ConversationBranch,
      depth: number,
      branchFrom: string | undefined,
      isMain: boolean,
    ) => {
      const chain = stepsForBranch(branch);
      let prevId: string | undefined;
      chain.forEach((raw, i) => {
        const step: Step = {
          ...raw,
          depth,
          row,
          flowFrom: prevId,
          branchFrom: i === 0 ? branchFrom : undefined,
        };
        if (step.kind === "qa") {
          qCounter += 1;
          step.qNum = qCounter;
        }
        laid.push(step);
        row += 1;
        prevId = step.id;

        // Answer-driven follow-ups drop from the step that triggered them:
        // stage-sourced branches from the matching main step, nested branches
        // from the end of their parent branch.
        if (isMain) {
          for (const child of childrenOfStageIndex.get(i) ?? [])
            emitBranch(child, depth + 1, step.id, false);
        }
        if (i === chain.length - 1) {
          for (const child of childrenOfBranch.get(branch.id) ?? [])
            emitBranch(child, depth + 1, step.id, false);
        }
      });
    };

    emitBranch(main, 0, undefined, true);
    return { steps: laid, rows: row };
  }, [graph.data, stages]);

  const byId = useMemo(() => new Map(steps.map((s) => [s.id, s])), [steps]);

  if (steps.length === 0) {
    return (
      <p className="text-[12px] text-[var(--muted)]">
        No conversation yet — questions and answers appear here as the discovery call unfolds.
      </p>
    );
  }

  const spineX = (s: Step) => LEFT + s.depth * DEPTH_X + GLYPH_DX;
  const rowCy = (s: Step) => TOP + s.row * ROW_H + CHIP_H / 2;
  const maxDepth = steps.reduce((m, s) => Math.max(m, s.depth), 0);
  const contentLeft = LEFT + maxDepth * DEPTH_X;
  const width = contentLeft + 300;
  const height = TOP + rows * ROW_H + 12;

  const isSelected = (s: Step) =>
    (s.node.artifact_id != null && s.node.artifact_id === selectedArtifactId) ||
    (s.node.transcript_segment_id != null && s.node.transcript_segment_id === selectedSegmentId);

  return (
    <div className="qa-flow">
      <ul className="qa-legend">
        <li>
          <span className="dot se" /> Question asked by SE
        </li>
        <li>
          <span className="ring">A</span> Answer from customer
        </li>
        <li>
          <span className="dot art" /> Derived artifact
        </li>
      </ul>

      <svg
        className="qa-svg"
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Question-and-answer flow for the discovery conversation, in order"
      >
        {/* Connectors first, so chips sit on top. */}
        {steps.map((s) => {
          const out = [];
          if (s.flowFrom && byId.has(s.flowFrom)) {
            const from = byId.get(s.flowFrom)!;
            out.push(
              <path
                key={`flow-${s.id}`}
                className="qa-link flow"
                d={`M${spineX(s)} ${rowCy(from)} V${rowCy(s)}`}
              />,
            );
          }
          if (s.branchFrom && byId.has(s.branchFrom)) {
            const parent = byId.get(s.branchFrom)!;
            out.push(
              <path
                key={`branch-${s.id}`}
                className="qa-link branch"
                d={`M${spineX(parent)} ${rowCy(parent)} V${rowCy(s)} H${spineX(s)}`}
              />,
            );
          }
          return out;
        })}

        {/* Rows */}
        {steps.map((s) => {
          const x = LEFT + s.depth * DEPTH_X;
          const cy = TOP + s.row * ROW_H + CHIP_H / 2;
          const clickable = Boolean(s.node.artifact_id || s.node.transcript_segment_id);
          const selected = isSelected(s);
          const onActivate = () => {
            if (s.node.artifact_id) selectArtifact(s.node.artifact_id);
            if (s.node.transcript_segment_id) selectSegment(s.node.transcript_segment_id);
          };

          let labelX = x + 20;
          let label = "";
          let chipClass = "qa-chip";
          if (s.kind === "qa") {
            labelX = x + 42;
            label = truncate(s.question?.label ?? "", 26);
            chipClass = "qa-chip q";
          } else if (s.kind === "answer") {
            labelX = x + 26;
            label = truncate(s.node.label, 30);
            chipClass = "qa-chip a";
          } else {
            labelX = x + 20;
            label = truncate(s.node.label, 26);
            chipClass = "qa-chip art";
          }
          const chipW = Math.min(258, 20 + label.length * 6.9);

          return (
            <g
              key={s.id}
              className={`qa-step ${clickable ? "clickable" : ""} ${selected ? "selected" : ""}`}
              onClick={clickable ? onActivate : undefined}
              role={clickable ? "button" : undefined}
              tabIndex={clickable ? 0 : undefined}
              onKeyDown={
                clickable
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onActivate();
                      }
                    }
                  : undefined
              }
            >
              {/* Full-row hit target */}
              <rect
                className="qa-hit"
                x={x}
                y={cy - ROW_H / 2}
                width={chipW + (labelX - x) + 8}
                height={ROW_H}
                rx={8}
              />

              {s.kind === "qa" && (
                <>
                  <circle className="qa-glyph se" cx={x + GLYPH_DX} cy={cy} r={4.5} />
                  <text className="qa-num" x={x + 20} y={cy + 4}>
                    Q{s.qNum}
                  </text>
                  <rect
                    className={chipClass}
                    x={labelX}
                    y={cy - CHIP_H / 2}
                    rx={7}
                    width={chipW}
                    height={CHIP_H}
                  />
                  <text className="qa-label" x={labelX + 10} y={cy + 4}>
                    {label}
                  </text>
                  {s.answer && (
                    <>
                      <circle className="qa-ansdot" cx={labelX + chipW + 12} cy={cy} r={7} />
                      <text className="qa-ansdot-label" x={labelX + chipW + 12} y={cy + 3}>
                        A
                      </text>
                      <title>{`Q: ${s.question?.label}\nA: ${s.answer.label}`}</title>
                    </>
                  )}
                  {!s.answer && <title>{s.question?.label}</title>}
                </>
              )}

              {s.kind === "answer" && (
                <>
                  <circle className="qa-ring" cx={x + GLYPH_DX + 2} cy={cy} r={9} />
                  <text className="qa-ring-label" x={x + GLYPH_DX + 2} y={cy + 4}>
                    A
                  </text>
                  <rect
                    className={chipClass}
                    x={labelX}
                    y={cy - CHIP_H / 2}
                    rx={7}
                    width={chipW}
                    height={CHIP_H}
                  />
                  <text className="qa-label" x={labelX + 10} y={cy + 4}>
                    {label}
                  </text>
                  <title>{s.node.label}</title>
                </>
              )}

              {s.kind === "artifact" && (
                <>
                  <circle
                    className="qa-glyph art"
                    cx={x + GLYPH_DX}
                    cy={cy}
                    r={4.5}
                    style={{ fill: ARTIFACT_COLOR[s.node.node_type] ?? "var(--muted)" }}
                  />
                  <rect
                    className={chipClass}
                    x={labelX}
                    y={cy - CHIP_H / 2}
                    rx={7}
                    width={chipW}
                    height={CHIP_H}
                    style={{ stroke: ARTIFACT_COLOR[s.node.node_type] ?? "var(--border)" }}
                  />
                  <text className="qa-label" x={labelX + 10} y={cy + 4}>
                    <tspan className="qa-kind">{s.node.node_type}</tspan> · {label}
                  </text>
                  <title>{s.node.label}</title>
                </>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
