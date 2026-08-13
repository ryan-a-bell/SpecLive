import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import type { TreeNode } from "@rdc/domain";
import { useWorkspaceStore } from "@/lib/store";
import { TreeNodeRow } from "./TreeNode";

const node: TreeNode = {
  id: "REQ-002",
  type: "requirement",
  title: "Status refresh within 30 seconds",
  statement: "The solution shall refresh order status within 30 seconds.",
  status: "candidate",
  confidence: 0.95,
  validation_state: "clarified",
  evidence_count: 2,
  parent_id: "NEED-001",
  children: [
    {
      id: "Q-005",
      type: "open_question",
      title: "Which states matter?",
      statement: "Which order states matter?",
      status: "candidate",
      confidence: 0,
      validation_state: "detected",
      evidence_count: 1,
      parent_id: "REQ-002",
      children: [],
    },
  ],
};

describe("TreeNodeRow (discovery-tree interaction)", () => {
  beforeEach(() => useWorkspaceStore.setState({ selectedArtifactId: null }));

  it("renders identifier, title, confidence, evidence count", () => {
    render(<TreeNodeRow node={node} />);
    expect(screen.getByText(/REQ-002 Status refresh/)).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText(/2 evidence/)).toBeInTheDocument();
  });

  it("renders children recursively", () => {
    render(<TreeNodeRow node={node} />);
    expect(screen.getByText(/Q-005 Which states matter/)).toBeInTheDocument();
  });

  it("clicking a node selects it", async () => {
    render(<TreeNodeRow node={node} />);
    await userEvent.click(screen.getByText(/REQ-002 Status refresh/));
    expect(useWorkspaceStore.getState().selectedArtifactId).toBe("REQ-002");
  });
});
