import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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
          nodes: [],
        },
        {
          id: "BR-STATES",
          session_id: "S",
          name: "States and exceptions",
          topic: "states_exceptions",
          status: "active",
          source_stage_id: "STAGE-3",
          created_from_segment_id: "SEG-102",
          nodes: [
            {
              id: "N1",
              branch_id: "BR-STATES",
              node_type: "answer",
              label: "Delayed orders",
              sequence: 0,
            },
            {
              id: "N2",
              branch_id: "BR-STATES",
              node_type: "question",
              label: "Which states?",
              sequence: 1,
            },
          ],
        },
      ],
    },
  }),
  useScriptState: () => ({
    data: {
      current_index: 2,
      total_stages: 3,
      completed_stage_ids: [],
      current_stage: null,
      script: {
        id: "SCRIPT",
        name: "S",
        version: "1",
        description: "",
        stages: [
          {
            id: "STAGE-1",
            script_id: "SCRIPT",
            sequence: 1,
            title: "Driver",
            objective: "",
            primary_prompt: "",
            alternative_prompts: [],
            completion_criteria: [],
          },
          {
            id: "STAGE-2",
            script_id: "SCRIPT",
            sequence: 2,
            title: "Current",
            objective: "",
            primary_prompt: "",
            alternative_prompts: [],
            completion_criteria: [],
          },
          {
            id: "STAGE-3",
            script_id: "SCRIPT",
            sequence: 3,
            title: "Workflow",
            objective: "",
            primary_prompt: "",
            alternative_prompts: [],
            completion_criteria: [],
          },
        ],
      },
    },
  }),
}));

import { GitBranchView } from "./GitBranchView";

describe("GitBranchView (branch visualization)", () => {
  it("renders the main script lane and side-branch nodes", () => {
    render(<GitBranchView sessionId="S" />);
    expect(screen.getByText("Main script")).toBeInTheDocument();
    expect(screen.getByText("Driver")).toBeInTheDocument();
    expect(screen.getByText("States and exceptions")).toBeInTheDocument();
    expect(screen.getByText("Delayed orders")).toBeInTheDocument();
    expect(screen.getByText("Which states?")).toBeInTheDocument();
  });
});
