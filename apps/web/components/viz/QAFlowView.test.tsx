import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const selectArtifact = vi.fn();
const selectSegment = vi.fn();

vi.mock("@/lib/store", () => ({
  useWorkspaceStore: (selector: (s: unknown) => unknown) =>
    selector({ selectArtifact, selectSegment }),
}));

vi.mock("@/lib/hooks", () => ({
  useConversationGraph: () => ({
    data: {
      session_id: "S",
      branches: [
        {
          id: "BR-MAIN",
          session_id: "S",
          name: "Main discovery script",
          topic: "main_script",
          status: "active",
          nodes: [
            {
              id: "M0",
              branch_id: "BR-MAIN",
              node_type: "script_stage",
              label: "Business driver",
              sequence: 0,
            },
            {
              id: "M1",
              branch_id: "BR-MAIN",
              node_type: "script_stage",
              label: "Current state",
              sequence: 1,
            },
          ],
        },
        {
          id: "BR-STATES",
          session_id: "S",
          name: "States and exceptions",
          topic: "states_exceptions",
          status: "active",
          source_stage_id: "M1",
          nodes: [
            {
              id: "N0",
              branch_id: "BR-STATES",
              node_type: "answer",
              label: "Delayed orders discovered late",
              transcript_segment_id: "SEG-102",
              sequence: 0,
            },
            {
              id: "N1",
              branch_id: "BR-STATES",
              node_type: "question",
              label: "Which states matter?",
              artifact_id: "Q-005",
              sequence: 1,
            },
            {
              id: "N2",
              branch_id: "BR-STATES",
              node_type: "requirement",
              label: "Alert requirement",
              sequence: 2,
            },
          ],
        },
      ],
    },
  }),
}));

import { QAFlowView } from "./QAFlowView";

describe("QAFlowView (Q&A flow visualization)", () => {
  beforeEach(() => {
    selectArtifact.mockClear();
    selectSegment.mockClear();
  });

  it("renders the legend, numbered questions, and a branched answer", () => {
    render(<QAFlowView sessionId="S" />);
    expect(screen.getByText("Question asked by SE")).toBeInTheDocument();
    expect(screen.getByText("Answer from customer")).toBeInTheDocument();
    // script stages are numbered as facilitator questions
    expect(screen.getByText("Q1")).toBeInTheDocument();
    expect(screen.getByText("Q2")).toBeInTheDocument();
    // the follow-up question inside the branch continues the numbering
    expect(screen.getByText("Q3")).toBeInTheDocument();
    // the standalone customer answer that opened the branch
    expect(screen.getByText("Delayed orders discover…")).toBeInTheDocument();
    // a derived artifact chip
    expect(screen.getByText("requirement")).toBeInTheDocument();
  });

  it("selects the artifact when a question node carrying one is activated", () => {
    render(<QAFlowView sessionId="S" />);
    fireEvent.click(screen.getByText("Which states…"));
    expect(selectArtifact).toHaveBeenCalledWith("Q-005");
  });
});
