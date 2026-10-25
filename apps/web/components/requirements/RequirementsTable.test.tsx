import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DiscoveryArtifact } from "@rdc/domain";
import type { RegisterRow } from "@/lib/workspaces";
import { RequirementsTable } from "./RequirementsTable";

function artifact(
  id: string,
  title: string,
  statement: string,
  artifactType: DiscoveryArtifact["artifact_type"],
  status: DiscoveryArtifact["status"],
  confidence: number,
): DiscoveryArtifact {
  return {
    id,
    session_id: `session-${id}`,
    title,
    statement,
    artifact_type: artifactType,
    status,
    confidence,
    validation_state: status === "candidate" ? "detected" : "customer_confirmed",
    derivation_method: "test",
  };
}

const rows: RegisterRow[] = [
  {
    artifact: artifact(
      "alpha",
      "Alpha visibility",
      "Show warehouse delays in real time",
      "objective",
      "confirmed",
      0.94,
    ),
    sessionId: "session-alpha",
    sessionTitle: "Operations discovery",
  },
  {
    artifact: artifact(
      "beta",
      "Beta mobile support",
      "Support the mobile picking workflow",
      "requirement",
      "candidate",
      0.5,
    ),
    sessionId: "session-beta",
    sessionTitle: "Floor leads",
  },
  {
    artifact: artifact(
      "gamma",
      "Gamma refresh",
      "Refresh status within 30 seconds",
      "requirement",
      "confirmed",
      0.8,
    ),
    sessionId: "session-gamma",
    sessionTitle: "Systems review",
  },
];

function renderedTitles() {
  return screen
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[0]?.textContent);
}

describe("RequirementsTable", () => {
  it("searches and combines type and status filters", async () => {
    const user = userEvent.setup();
    render(<RequirementsTable rows={rows} isLoading={false} onOpenSession={() => undefined} />);

    await user.type(screen.getByRole("searchbox", { name: "Search" }), "mobile");
    expect(screen.getByText("1 of 3")).toBeInTheDocument();
    expect(screen.getByText("Beta mobile support")).toBeInTheDocument();
    expect(screen.queryByText("Alpha visibility")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.click(screen.getByRole("button", { name: "Requirement" }));
    expect(screen.getByText("2 of 3")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "candidate");
    expect(screen.getByText("1 of 3")).toBeInTheDocument();
    expect(screen.getByText("Beta mobile support")).toBeInTheDocument();
  });

  it("sorts rows from accessible column headers and opens the selected source", async () => {
    const user = userEvent.setup();
    const onOpenSession = vi.fn();
    render(<RequirementsTable rows={rows} isLoading={false} onOpenSession={onOpenSession} />);

    expect(renderedTitles()).toEqual(["Alpha visibility", "Gamma refresh", "Beta mobile support"]);

    await user.click(screen.getByRole("button", { name: "Title" }));
    expect(renderedTitles()).toEqual(["Alpha visibility", "Beta mobile support", "Gamma refresh"]);

    await user.click(screen.getByText("Gamma refresh"));
    expect(onOpenSession).toHaveBeenCalledWith("session-gamma");
  });
});
