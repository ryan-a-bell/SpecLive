import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/hooks", () => ({
  useCoverage: () => ({
    data: {
      session_id: "S",
      stages: [
        { id: "STAGE-1", title: "Driver", sequence: 1 },
        { id: "STAGE-3", title: "Workflow", sequence: 3 },
      ],
      rows: [
        {
          branch_id: "BR-STATES",
          branch: "States and exceptions",
          topic: "states_exceptions",
          cells: [
            { stage_id: "STAGE-1", state: "unanswered", title: null, meta: null },
            { stage_id: "STAGE-3", state: "strong", title: "Primary evidence", meta: "States" },
          ],
        },
      ],
      summary: { counts: { strong: 1 }, total_cells: 2, coverage_percent: 50 },
    },
  }),
}));

import { CoverageMatrix } from "./CoverageMatrix";

describe("CoverageMatrix", () => {
  it("renders stage columns and branch rows with coverage shading", () => {
    render(<CoverageMatrix sessionId="S" />);
    expect(screen.getByText("Driver")).toBeInTheDocument();
    expect(screen.getByText("Workflow")).toBeInTheDocument();
    expect(screen.getByText("States and exceptions")).toBeInTheDocument();
    const strongCell = screen.getByText("Primary evidence").closest("td");
    expect(strongCell).toHaveClass("coverage-high");
  });
});
