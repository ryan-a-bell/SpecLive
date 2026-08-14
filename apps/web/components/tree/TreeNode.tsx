"use client";

import type { TreeNode as TreeNodeType } from "@rdc/domain";
import { useWorkspaceStore } from "@/lib/store";

const TYPE_LABEL: Record<string, string> = {
  objective: "Objective",
  stakeholder_need: "Need",
  requirement: "Requirement",
  constraint: "Constraint",
  risk: "Risk",
  assumption: "Assumption",
  open_question: "Open question",
  success_metric: "Success metric",
  integration: "Integration",
  decision: "Decision",
  stakeholder: "Stakeholder",
};

export function TreeNodeRow({ node }: { node: TreeNodeType }) {
  const selectedArtifactId = useWorkspaceStore((s) => s.selectedArtifactId);
  const selectArtifact = useWorkspaceStore((s) => s.selectArtifact);

  const isQuestion = node.type === "open_question";
  const isStrong = node.evidence_count >= 1 && node.confidence >= 0.9 && !isQuestion;
  const dotClass = `type-dot ${node.type}${isQuestion ? " hollow" : ""}${isStrong ? " solid" : ""}`;

  return (
    <div className="my-[6px]">
      <div
        data-node-id={node.id}
        className={`node-row ${selectedArtifactId === node.id ? "selected" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => selectArtifact(node.id)}
        onKeyDown={(e) => e.key === "Enter" && selectArtifact(node.id)}
      >
        <i className={dotClass} />
        <span>
          <span className="text-[12px] font-bold">
            {node.id} {node.title}
          </span>
          <br />
          <span className="text-[10px] text-[var(--muted)]">
            {TYPE_LABEL[node.type] ?? node.type} · {node.validation_state.replace(/_/g, " ")} ·{" "}
            {node.evidence_count} evidence
          </span>
        </span>
        <span className="text-[11px] text-[var(--muted)]">
          {node.confidence > 0 ? `${Math.round(node.confidence * 100)}%` : "—"}
        </span>
      </div>
      {node.children.length > 0 && (
        <div className="node-children">
          {node.children.map((child) => (
            <TreeNodeRow key={child.id} node={child} />
          ))}
        </div>
      )}
    </div>
  );
}
