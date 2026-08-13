import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const advanceMutate = vi.fn();

vi.mock("@/lib/hooks", () => ({
  useScriptState: () => ({
    data: {
      current_index: 2,
      total_stages: 7,
      completed_stage_ids: ["STAGE-1", "STAGE-2"],
      current_stage: {
        id: "STAGE-3",
        script_id: "SCRIPT",
        sequence: 3,
        title: "Workflow decisions",
        objective: "Define the decisions the customer must make",
        primary_prompt: "Which specific order states and exceptions must supervisors see?",
        alternative_prompts: [],
        completion_criteria: [],
      },
      script: { id: "SCRIPT", name: "S", version: "1", description: "", stages: [] },
    },
  }),
  useConversationGraph: () => ({ data: { session_id: "S", branches: [] } }),
  useAdvanceScript: () => ({ mutate: advanceMutate }),
}));

import { GuidedScriptPanel } from "./GuidedScriptPanel";
import { useWorkspaceStore } from "@/lib/store";

describe("GuidedScriptPanel (script advancement)", () => {
  it("shows the current stage and step counter", () => {
    render(<GuidedScriptPanel sessionId="S" />);
    expect(screen.getByText("Step 3 of 7")).toBeInTheDocument();
    expect(screen.getByText("Define the decisions the customer must make")).toBeInTheDocument();
  });

  it("'Use this prompt' loads the prompt into the composer", async () => {
    useWorkspaceStore.setState({ composerText: "" });
    render(<GuidedScriptPanel sessionId="S" />);
    await userEvent.click(screen.getByText("Use this prompt"));
    expect(useWorkspaceStore.getState().composerText).toContain("order states and exceptions");
  });

  it("'Mark answered' advances the script", async () => {
    render(<GuidedScriptPanel sessionId="S" />);
    await userEvent.click(screen.getByText("Mark answered"));
    expect(advanceMutate).toHaveBeenCalled();
  });
});
