import { describe, expect, it } from "vitest";
import type { DiscoveryArtifact, DiscoverySession } from "@rdc/domain";
import {
  confidenceBand,
  groupWorkspaces,
  initials,
  isLiveSession,
  needsReview,
  slugifyCustomer,
  statusPill,
} from "./workspaces";

function session(id: string, customer: string, title: string): DiscoverySession {
  return {
    id,
    title,
    customer,
    facilitator: "Facilitator",
    status: "active",
    metadata: {},
  };
}

function artifact(overrides: Partial<DiscoveryArtifact> = {}): DiscoveryArtifact {
  return {
    id: "a1",
    session_id: "s1",
    artifact_type: "requirement",
    title: "REQ-1",
    statement: "The system must do X.",
    status: "candidate",
    confidence: 0.5,
    validation_state: "inferred",
    derivation_method: "llm",
    ...overrides,
  };
}

describe("slugifyCustomer", () => {
  it("slugifies names and falls back for empties", () => {
    expect(slugifyCustomer("Acme Logistics")).toBe("acme-logistics");
    expect(slugifyCustomer("  Northwind & Co.  ")).toBe("northwind-co");
    expect(slugifyCustomer("!!!")).toBe("workspace");
  });
});

describe("initials", () => {
  it("derives up to two initials", () => {
    expect(initials("Acme Logistics")).toBe("AL");
    expect(initials("Globex")).toBe("GL");
    expect(initials("")).toBe("?");
  });
});

describe("groupWorkspaces", () => {
  it("groups sessions by customer into workspaces", () => {
    const workspaces = groupWorkspaces([
      session("s1", "Acme Logistics", "Discovery: Operations"),
      session("s2", "Acme Logistics", "Discovery: IT"),
      session("s3", "Globex", "Field service"),
    ]);
    expect(workspaces).toHaveLength(2);
    const acme = workspaces.find((w) => w.id === "acme-logistics");
    expect(acme?.sessions).toHaveLength(2);
    expect(workspaces.find((w) => w.id === "globex")?.sessions).toHaveLength(1);
  });

  it("returns an empty list when there are no sessions", () => {
    expect(groupWorkspaces([])).toEqual([]);
  });

  it("keeps distinct customers that slugify the same separate, with unique ids", () => {
    const workspaces = groupWorkspaces([
      session("s1", "Acme, Inc.", "Discovery: Ops"),
      session("s2", "Acme Inc", "Discovery: IT"),
    ]);
    expect(workspaces).toHaveLength(2);
    expect(workspaces.map((w) => w.name).sort()).toEqual(["Acme Inc", "Acme, Inc."]);
    const ids = workspaces.map((w) => w.id);
    expect(new Set(ids).size).toBe(2);
    expect(ids).toContain("acme-inc");
    expect(ids).toContain("acme-inc-2");
  });

  it("merges sessions whose customer differs only by surrounding whitespace", () => {
    const workspaces = groupWorkspaces([
      session("s1", "Globex", "One"),
      session("s2", "  Globex  ", "Two"),
    ]);
    expect(workspaces).toHaveLength(1);
    expect(workspaces[0]?.sessions).toHaveLength(2);
  });
});

describe("isLiveSession", () => {
  it("treats active and paused as live, and nothing else", () => {
    expect(isLiveSession("active")).toBe(true);
    expect(isLiveSession("paused")).toBe(true);
    expect(isLiveSession("draft")).toBe(false);
    expect(isLiveSession("completed")).toBe(false);
    expect(isLiveSession("archived")).toBe(false);
    expect(isLiveSession("in_progress")).toBe(false);
  });
});

describe("statusPill", () => {
  it("maps artifact status to a pill variant", () => {
    expect(statusPill("confirmed").cls).toBe("confirmed");
    expect(statusPill("candidate").cls).toBe("candidate");
    expect(statusPill("superseded").cls).toBe("open");
  });
});

describe("needsReview", () => {
  it("flags unresolved candidates as awaiting validation", () => {
    expect(needsReview(artifact({ status: "candidate" }))).toBe(true);
  });

  it("excludes items a human has already acted on", () => {
    expect(needsReview(artifact({ status: "confirmed" }))).toBe(false);
    expect(needsReview(artifact({ status: "baselined" }))).toBe(false);
    expect(needsReview(artifact({ status: "rejected" }))).toBe(false);
    expect(needsReview(artifact({ status: "superseded" }))).toBe(false);
  });

  it("excludes a candidate whose validation state was rejected", () => {
    expect(needsReview(artifact({ status: "candidate", validation_state: "rejected" }))).toBe(false);
  });
});

describe("confidenceBand", () => {
  it("bands confidence into low/med/high at 0.6 and 0.8", () => {
    expect(confidenceBand(0.2)).toBe("low");
    expect(confidenceBand(0.59)).toBe("low");
    expect(confidenceBand(0.6)).toBe("med");
    expect(confidenceBand(0.79)).toBe("med");
    expect(confidenceBand(0.8)).toBe("high");
    expect(confidenceBand(1)).toBe("high");
  });
});
