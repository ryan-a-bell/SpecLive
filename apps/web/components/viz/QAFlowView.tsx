"use client";

import { useMemo } from "react";
import { useConversationGraph, useScriptState } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";

type Graph = NonNullable<ReturnType<typeof useConversationGraph>["data"]>;
type ConversationBranch = Graph["branches"][number];
type ConversationNode = NonNullable<ConversationBranch["nodes"]>[number];

/**
 * Q&A flow — a cascading staircase of the questions the facilitator (SE) asks
 * and the answers the customer gives, with follow-up threads branching off the
 * answers that triggered them. Mirrors the classic "effective Q&A flow during
 * technical discovery" diagram, driven by the live conversation graph.
 *
 *   • Question asked by the facilitator  →  gray dot + "Q{n}"
 *   • Answer from the customer           →  circled "A"
 *   • Derived artifact (requirement …)   →  small colored chip
 *
 * Each answer can spawn a branch of targeted follow-ups; those branches drop
 * down and step to the right, exactly like Figure 3.
 */

const STEP_X = 138; // horizontal shift per step within a chain
const STEP_Y = 60; // vertical shift per row
const INDENT_X = 34; // extra indent per branch nesting level
const TOP = 30;
const LEFT = 26;
const CHIP_H = 30;

type StepKind = "qa" | "answer" | "artifact";

interface Step {
  id: string;
  kind: StepKind;
  qNum?: number;
  question?: ConversationNode;
  answer?: ConversationNode;
  node: ConversationNode; // primary node (question for "qa", else the node itself)
  x: number;
  y: number;
  /** id of the step this one flows from within its chain, if any */
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
): Omit<Step, "x" | "y" | "flowFrom" | "branchFrom">[] {
  const nodes = [...(branch.nodes ?? [])].sort((a, b) => a.sequence - b.sequence);
  const out: Omit<Step, "x" | "y" | "flowFrom" | "branchFrom">[] = [];
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

export function QAFlowView({ sessionId }: { sessionId: string }) {
  const graph = useConversationGraph(sessionId);
  const script = useScriptState(sessionId);
  const selectArtifact = useWorkspaceStore((s) => s.selectArtifact);
  const selectSegment = useWorkspaceStore((s) => s.selectSegment);

  const stages = script.data?.script.stages;

  const { steps, width, height } = useMemo(() => {
    const branches = graph.data?.branches ?? [];
    if (branches.length === 0) return { steps: [] as Step[], width: 640, height: 200 };

    const main =
      branches.find((b) => b.topic === "main_script") ??
      branches.find((b) => (b.parent_branch_id ?? null) === null) ??
      branches[0];
    if (!main) return { steps: [] as Step[], width: 640, height: 200 };

    // A branch names the *script stage* it was spawned from (e.g. "STAGE-3"),
    // not a conversation-node id — so resolve that to the stage's position and
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
      const baseX = LEFT + depth * INDENT_X;
      const chain = stepsForBranch(branch);
      let prevId: string | undefined;
      chain.forEach((raw, i) => {
        const step: Step = {
          ...raw,
          x: baseX + i * STEP_X,
          y: TOP + row * STEP_Y,
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

    const width = Math.max(640, ...laid.map((s) => s.x)) + 320;
    const height = Math.max(200, TOP + row * STEP_Y + 20);
    return { steps: laid, width, height };
  }, [graph.data, stages]);

  const byId = useMemo(() => new Map(steps.map((s) => [s.id, s])), [steps]);

  if (steps.length === 0) {
    return (
      <p className="text-[12px] text-[var(--muted)]">
        No conversation yet — questions and answers appear here as the discovery call unfolds.
      </p>
    );
  }

  const anchorRight = (s: Step) => ({ x: s.x + 214, y: s.y + CHIP_H / 2 });
  const anchorLeft = (s: Step) => ({ x: s.x, y: s.y + CHIP_H / 2 });
  const anchorBottom = (s: Step) => ({ x: s.x + 46, y: s.y + CHIP_H });

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
        aria-label="Cascading question-and-answer flow for the discovery conversation"
      >
        <defs>
          <marker
            id="qa-arrow"
            viewBox="0 0 8 8"
            refX="6"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M0 0 L8 4 L0 8 z" fill="var(--muted)" />
          </marker>
        </defs>

        {/* Connectors first, so chips sit on top. */}
        {steps.map((s) => {
          const paths = [];
          if (s.flowFrom && byId.has(s.flowFrom)) {
            const from = anchorRight(byId.get(s.flowFrom)!);
            const to = anchorLeft(s);
            paths.push(
              <path
                key={`flow-${s.id}`}
                className="qa-link flow"
                d={`M${from.x} ${from.y} H${(from.x + to.x) / 2} V${to.y} H${to.x}`}
                markerEnd="url(#qa-arrow)"
              />,
            );
          }
          if (s.branchFrom && byId.has(s.branchFrom)) {
            const from = anchorBottom(byId.get(s.branchFrom)!);
            const to = anchorLeft(s);
            paths.push(
              <path
                key={`branch-${s.id}`}
                className="qa-link branch"
                d={`M${from.x} ${from.y} V${to.y} H${to.x}`}
                markerEnd="url(#qa-arrow)"
              />,
            );
          }
          return paths;
        })}

        {/* Steps */}
        {steps.map((s) => {
          const clickable = Boolean(s.node.artifact_id || s.node.transcript_segment_id);
          const onActivate = () => {
            if (s.node.artifact_id) selectArtifact(s.node.artifact_id);
            if (s.node.transcript_segment_id) selectSegment(s.node.transcript_segment_id);
          };
          return (
            <g
              key={s.id}
              transform={`translate(${s.x}, ${s.y})`}
              className={`qa-step ${clickable ? "clickable" : ""}`}
              onClick={clickable ? onActivate : undefined}
              role={clickable ? "button" : undefined}
              tabIndex={clickable ? 0 : undefined}
              onKeyDown={
                clickable
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") onActivate();
                    }
                  : undefined
              }
            >
              {s.kind === "qa" && (
                <>
                  <circle className="qa-glyph se" cx={9} cy={CHIP_H / 2} r={5} />
                  <text className="qa-num" x={22} y={CHIP_H / 2 + 4}>
                    Q{s.qNum}
                  </text>
                  <rect className="qa-chip q" x={54} y={4} rx={7} width={92} height={CHIP_H - 8} />
                  <text className="qa-label" x={64} y={CHIP_H / 2 + 4}>
                    {truncate(s.question?.label ?? "", 13)}
                  </text>
                  {s.answer ? (
                    <>
                      <line
                        className="qa-inline"
                        x1={146}
                        y1={CHIP_H / 2}
                        x2={162}
                        y2={CHIP_H / 2}
                        markerEnd="url(#qa-arrow)"
                      />
                      <circle className="qa-ring" cx={178} cy={CHIP_H / 2} r={11} />
                      <text className="qa-ring-label" x={178} y={CHIP_H / 2 + 4}>
                        A
                      </text>
                      <title>{s.answer.label}</title>
                    </>
                  ) : (
                    <title>{s.question?.label}</title>
                  )}
                </>
              )}

              {s.kind === "answer" && (
                <>
                  <circle className="qa-ring" cx={11} cy={CHIP_H / 2} r={11} />
                  <text className="qa-ring-label" x={11} y={CHIP_H / 2 + 4}>
                    A
                  </text>
                  <rect className="qa-chip a" x={30} y={4} rx={7} width={172} height={CHIP_H - 8} />
                  <text className="qa-label" x={40} y={CHIP_H / 2 + 4}>
                    {truncate(s.node.label, 24)}
                  </text>
                  <title>{s.node.label}</title>
                </>
              )}

              {s.kind === "artifact" && (
                <>
                  <circle
                    className="qa-glyph art"
                    cx={9}
                    cy={CHIP_H / 2}
                    r={5}
                    style={{ fill: ARTIFACT_COLOR[s.node.node_type] ?? "var(--muted)" }}
                  />
                  <rect
                    className="qa-chip art"
                    x={22}
                    y={4}
                    rx={7}
                    width={190}
                    height={CHIP_H - 8}
                    style={{ stroke: ARTIFACT_COLOR[s.node.node_type] ?? "var(--border)" }}
                  />
                  <text className="qa-label" x={32} y={CHIP_H / 2 + 4}>
                    <tspan className="qa-kind">{s.node.node_type}</tspan> ·{" "}
                    {truncate(s.node.label, 20)}
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

function truncate(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
