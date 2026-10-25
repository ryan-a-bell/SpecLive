import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const createMutate = vi.fn();
const updateMutate = vi.fn();
const archiveMutate = vi.fn();
const toast = vi.fn();

const scripts = [
  {
    id: "SCRIPT-OPS",
    name: "Operational Systems Discovery",
    version: "1.0.0",
    description: "Operational discovery",
    archived: false,
    stages: [
      {
        id: "STAGE-OPS-1",
        script_id: "SCRIPT-OPS",
        sequence: 0,
        title: "Business driver",
        objective: "Understand the business driver",
        primary_prompt: "What problem are you trying to solve?",
        alternative_prompts: [],
        completion_criteria: [],
      },
    ],
  },
  {
    id: "SCRIPT-SPIN",
    name: "Needs Discovery",
    version: "1.0.0",
    description: "SPIN needs discovery",
    archived: false,
    stages: [
      {
        id: "STAGE-SPIN-1",
        script_id: "SCRIPT-SPIN",
        sequence: 0,
        title: "Situation",
        objective: "Understand context",
        primary_prompt: "What does the current environment look like?",
        alternative_prompts: [],
        completion_criteria: [],
      },
      {
        id: "STAGE-SPIN-2",
        script_id: "SCRIPT-SPIN",
        sequence: 1,
        title: "Problem",
        objective: "Find the problem",
        primary_prompt: "What is not working?",
        alternative_prompts: [],
        completion_criteria: [],
      },
    ],
  },
];

vi.mock("@/lib/hooks", () => ({
  useScripts: () => ({ data: scripts, isLoading: false, isError: false }),
  useSessions: () => ({ data: [{ id: "SESSION", script_id: "SCRIPT-OPS" }] }),
  useCreateScript: () => ({ mutate: createMutate, isPending: false }),
  useUpdateScript: () => ({ mutate: updateMutate, isPending: false }),
  useArchiveScript: () => ({ mutate: archiveMutate, isPending: false }),
}));

vi.mock("@/lib/toast", () => ({
  useToast: (selector: (state: { show: typeof toast }) => unknown) => selector({ show: toast }),
}));

import { ScriptsView } from "./ScriptsView";

describe("ScriptsView", () => {
  beforeEach(() => {
    createMutate.mockClear();
    updateMutate.mockClear();
    archiveMutate.mockClear();
    toast.mockClear();
  });

  it("lists scripts and opens the selected script in the editor", async () => {
    render(<ScriptsView />);
    expect(screen.getByText("2 active")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Operational Systems Discovery")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Needs Discovery/ }));
    expect(screen.getByDisplayValue("Needs Discovery")).toBeInTheDocument();
    expect(screen.getByText("2 stages")).toBeInTheDocument();
    expect(screen.getByDisplayValue("What is not working?")).toBeInTheDocument();
  });

  it("creates a new editable draft and submits it", async () => {
    const user = userEvent.setup();
    render(<ScriptsView />);

    await user.click(screen.getByRole("button", { name: /New script/ }));
    const name = screen.getByDisplayValue("Untitled discovery script");
    await user.clear(name);
    await user.type(name, "Customer onboarding discovery");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(createMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Customer onboarding discovery",
        stages: [expect.objectContaining({ title: "Opening" })],
      }),
      expect.anything(),
    );
  });

  it("prevents archiving a script that is attached to a conversation", () => {
    render(<ScriptsView />);
    expect(screen.getByRole("button", { name: "Archive" })).toBeDisabled();
  });
});
