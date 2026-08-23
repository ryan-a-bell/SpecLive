"use client";

import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import type { ArtifactType, DiscoveryArtifact } from "@rdc/domain";
import { api } from "./api";
import { useSessions } from "./hooks";

/** The session fields the shell actually needs (a structural subset of
 * DiscoverySession, so it stays decoupled from schema-inference details). */
export interface WorkspaceSession {
  id: string;
  title: string;
  customer: string;
  status: string;
}

/**
 * A workspace is a client-side grouping of discovery conversations (sessions)
 * that share a customer. It is derived from the sessions list — there is no
 * separate backend entity yet — so every session for one customer rolls up
 * into a single focused workspace with a cross-section of its requirements.
 */
export interface Workspace {
  id: string; // slug of the customer
  name: string; // customer name
  sessions: WorkspaceSession[];
}

export function slugifyCustomer(customer: string): string {
  const slug = customer
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "workspace";
}

/** Two-letter initials for a customer/workspace mark. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const first = words[0];
  if (!first) return "?";
  if (words.length === 1) return first.slice(0, 2).toUpperCase();
  const second = words[1];
  return `${first[0] ?? ""}${second?.[0] ?? ""}`.toUpperCase();
}

/** Group sessions into workspaces by customer, alphabetically. */
export function groupWorkspaces(sessions: readonly WorkspaceSession[]): Workspace[] {
  const byCustomer = new Map<string, Workspace>();
  for (const session of sessions) {
    const id = slugifyCustomer(session.customer);
    const existing = byCustomer.get(id);
    if (existing) {
      existing.sessions.push(session);
    } else {
      byCustomer.set(id, { id, name: session.customer, sessions: [session] });
    }
  }
  return Array.from(byCustomer.values()).sort((a, b) => a.name.localeCompare(b.name));
}

export function findWorkspace(workspaces: Workspace[], id: string | null): Workspace | undefined {
  return workspaces.find((w) => w.id === id);
}

/** Workspaces derived from the live sessions list. */
export function useWorkspaces() {
  const query = useSessions();
  const workspaces = useMemo(() => groupWorkspaces(query.data ?? []), [query.data]);
  return { ...query, workspaces };
}

export interface RegisterRow {
  artifact: DiscoveryArtifact;
  sessionId: string;
  sessionTitle: string;
}

/**
 * Fetch and flatten the derived artifacts for every session in a workspace so
 * the Overview can show one requirements register across all its conversations.
 */
export function useWorkspaceArtifacts(sessions: WorkspaceSession[]): {
  rows: RegisterRow[];
  isLoading: boolean;
} {
  const results = useQueries({
    queries: sessions.map((s) => ({
      queryKey: ["artifacts", s.id] as const,
      queryFn: () => api.listArtifacts(s.id),
    })),
  });

  const isLoading = results.some((r) => r.isLoading);
  const rows = useMemo(() => {
    const out: RegisterRow[] = [];
    sessions.forEach((session, i) => {
      const artifacts = results[i]?.data ?? [];
      for (const artifact of artifacts) {
        if (artifact.status === "rejected" || artifact.validation_state === "rejected") continue;
        out.push({ artifact, sessionId: session.id, sessionTitle: session.title });
      }
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions, results.map((r) => r.dataUpdatedAt).join(",")]);

  return { rows, isLoading };
}

// --- presentation helpers -------------------------------------------------

export const ARTIFACT_TYPE_LABEL: Record<ArtifactType, string> = {
  objective: "Objective",
  stakeholder_need: "Need",
  requirement: "Requirement",
  constraint: "Constraint",
  assumption: "Assumption",
  risk: "Risk",
  decision: "Decision",
  open_question: "Open question",
  success_metric: "Success metric",
  integration: "Integration",
  stakeholder: "Stakeholder",
};

/** Map an artifact status to a register pill variant. */
export function statusPill(status: string): { label: string; cls: string } {
  switch (status) {
    case "confirmed":
      return { label: "Confirmed", cls: "confirmed" };
    case "baselined":
      return { label: "Baselined", cls: "confirmed" };
    case "candidate":
      return { label: "Candidate", cls: "candidate" };
    case "rejected":
      return { label: "Rejected", cls: "open" };
    case "superseded":
      return { label: "Superseded", cls: "open" };
    default:
      return { label: status, cls: "candidate" };
  }
}
