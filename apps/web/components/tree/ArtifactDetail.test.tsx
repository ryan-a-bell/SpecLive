import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// A cross-turn LLM artifact: two evidence links from two different segments
// (Elena + Marcus), the exact shape full-transcript context produces.
const ARTIFACT = {
  id: "REQ-010",
  session_id: "S",
  artifact_type: "requirement",
  title: "Low-latency fabric",
  statement: "The solution shall provide a path to a low-latency interconnect.",
  status: "candidate",
  confidence: 0.91,
  validation_state: "inferred",
  derivation_method: "llm",
  rationale: "Connected Elena's InfiniBand comment with Marcus confirming commitment.",
};

const EVIDENCE = [
  {
    id: "EV-1",
    artifact_id: "REQ-010",
    transcript_segment_id: "seg-elena",
    quote_start: 0,
    quote_end: 10,
    quoted_text: "InfiniBand or they'll scale terribly",
    relationship: "direct",
  },
  {
    id: "EV-2",
    artifact_id: "REQ-010",
    transcript_segment_id: "seg-marcus",
    quote_start: 0,
    quote_end: 10,
    quoted_text: "It's committed",
    relationship: "supporting",
  },
];

const TRANSCRIPT = [
  { id: "seg-elena", speaker: "participant", speaker_name: "Elena", text: "…InfiniBand…" },
  { id: "seg-marcus", speaker: "customer", speaker_name: "Marcus", text: "It's committed…" },
];

vi.mock("@/lib/hooks", () => ({
  useArtifacts: () => ({ data: [ARTIFACT] }),
  useEvidence: () => ({ data: EVIDENCE }),
  useTranscript: () => ({ data: TRANSCRIPT }),
  useConfirmArtifact: () => ({ mutate: vi.fn() }),
  useRejectArtifact: () => ({ mutate: vi.fn() }),
}));

import { ArtifactDetail } from "./ArtifactDetail";
import { useWorkspaceStore } from "@/lib/store";

describe("ArtifactDetail (derivation transparency)", () => {
  it("shows the LLM derivation-method badge for an LLM-derived artifact", () => {
    useWorkspaceStore.setState({ selectedArtifactId: "REQ-010" });
    render(<ArtifactDetail sessionId="S" />);
    expect(screen.getByText("LLM")).toBeInTheDocument();
  });

  it("labels multi-segment evidence as cross-turn", () => {
    useWorkspaceStore.setState({ selectedArtifactId: "REQ-010" });
    render(<ArtifactDetail sessionId="S" />);
    expect(screen.getByText(/cross-turn · 2 segments/)).toBeInTheDocument();
  });

  it("resolves evidence segment ids to speaker names, not raw uuids", () => {
    useWorkspaceStore.setState({ selectedArtifactId: "REQ-010" });
    render(<ArtifactDetail sessionId="S" />);
    expect(screen.getByText(/Elena · direct/)).toBeInTheDocument();
    expect(screen.getByText(/Marcus · supporting/)).toBeInTheDocument();
  });
});
