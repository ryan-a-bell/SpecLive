import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConversationStructure } from "./ConversationStructure";

vi.mock("./FlowTranscript", () => ({ FlowTranscript: () => <div>Flow transcript</div> }));
vi.mock("./QAFlowView", () => ({ QAFlowView: () => <div>Q&amp;A content</div> }));
vi.mock("./GitBranchView", () => ({ GitBranchView: () => <div>Git content</div> }));
vi.mock("./CoverageMatrix", () => ({ CoverageMatrix: () => <div>Coverage content</div> }));

describe("ConversationStructure", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => values.get(key) ?? null,
        setItem: (key: string, value: string) => values.set(key, value),
        removeItem: (key: string) => values.delete(key),
        clear: () => values.clear(),
      },
    });
  });

  it("offers only the distinct structure views", () => {
    render(<ConversationStructure sessionId="SESSION" />);

    expect(screen.getByRole("button", { name: "Q&A flow" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Git branch tree" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Coverage matrix" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Conversation subway" })).not.toBeInTheDocument();
  });
});
