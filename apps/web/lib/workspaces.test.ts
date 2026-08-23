import { describe, expect, it } from "vitest";
import type { DiscoverySession } from "@rdc/domain";
import { groupWorkspaces, initials, slugifyCustomer, statusPill } from "./workspaces";

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
});

describe("statusPill", () => {
  it("maps artifact status to a pill variant", () => {
    expect(statusPill("confirmed").cls).toBe("confirmed");
    expect(statusPill("candidate").cls).toBe("candidate");
    expect(statusPill("superseded").cls).toBe("open");
  });
});
