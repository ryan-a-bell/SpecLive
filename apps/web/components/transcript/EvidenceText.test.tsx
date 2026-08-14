import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { EvidenceLink } from "@rdc/domain";
import { EvidenceText } from "./EvidenceText";

const text = "Ideally within 30 seconds. Anything over a couple of minutes is too stale.";

const link: EvidenceLink = {
  id: "EV-1",
  artifact_id: "REQ-002",
  transcript_segment_id: "SEG-104",
  quote_start: text.indexOf("within 30 seconds"),
  quote_end: text.indexOf("within 30 seconds") + "within 30 seconds".length,
  quoted_text: "within 30 seconds",
  relationship: "direct",
  confidence: 0.95,
};

describe("EvidenceText (transcript → artifact navigation)", () => {
  it("highlights the exact evidence span", () => {
    render(<EvidenceText text={text} links={[link]} onSelect={() => {}} />);
    const span = screen.getByText("within 30 seconds");
    expect(span).toHaveClass("evidence", "direct");
  });

  it("clicking evidence selects the linked artifact", async () => {
    const onSelect = vi.fn();
    render(<EvidenceText text={text} links={[link]} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("within 30 seconds"));
    expect(onSelect).toHaveBeenCalledWith("REQ-002");
  });

  it("renders surrounding text intact", () => {
    render(<EvidenceText text={text} links={[link]} onSelect={() => {}} />);
    expect(screen.getByText(/Ideally/)).toBeInTheDocument();
    expect(screen.getByText(/too stale/)).toBeInTheDocument();
  });
});
