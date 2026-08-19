import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useWorkspaceStore } from "@/lib/store";

vi.mock("@/lib/hooks", () => ({
  useTranscript: () => ({
    data: [
      { id: "SEG-1", speaker: "facilitator", speaker_name: "Facilitator", text: "What matters most?" },
      { id: "SEG-2", speaker: "customer", speaker_name: "Customer", text: "Refresh within 30 seconds." },
    ],
  }),
  useSessionEvidence: () => ({
    data: [
      {
        id: "EV-1",
        artifact_id: "REQ-002",
        transcript_segment_id: "SEG-2",
        quote_start: "Refresh ".length,
        quote_end: "Refresh within 30 seconds".length,
        quoted_text: "within 30 seconds",
        relationship: "direct",
        confidence: 0.9,
      },
    ],
  }),
}));

import { FlowTranscript } from "./FlowTranscript";

describe("FlowTranscript (flow → transcript highlighting)", () => {
  it("highlights the segment carrying evidence for the selected artifact", () => {
    useWorkspaceStore.setState({ selectedArtifactId: null, selectedSegmentId: null });
    render(<FlowTranscript sessionId="S" />);

    const span = screen.getByText("within 30 seconds");
    expect(span).not.toHaveClass("active");

    // Selecting the requirement (as a flow click would) activates its evidence.
    act(() => useWorkspaceStore.setState({ selectedArtifactId: "REQ-002" }));
    expect(screen.getByText("within 30 seconds")).toHaveClass("active");
  });
});
