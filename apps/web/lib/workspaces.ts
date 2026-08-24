"use client";

import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import type {
  ArtifactType,
  DiscoveryArtifact,
  EvidenceLink,
  Workspace as DomainWorkspace,
  WorkspaceSession as DomainWorkspaceSession,
} from "@rdc/domain";
import { api } from "./api";

/** The session fields the shell actually needs (a structural subset of
 * DiscoverySession, so it stays decoupled from schema-inference details). */
export type WorkspaceSession = DomainWorkspaceSession;

/**
 * A workspace is a client-side grouping of discovery conversations (sessions)
 * that share a customer. It is derived from the sessions list — there is no
 * separate backend entity yet — so every session for one customer rolls up
 * into a single focused workspace with a cross-section of its requirements.
 */
export type Workspace = DomainWorkspace;

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

/**
 * Session statuses that mean a call is genuinely mid-flight (`paused` covers a
 * live call that is momentarily halted). Keep in sync with the session-status
 * enum: draft / active / paused / completed / archived.
 */
export function isLiveSession(status: string): boolean {
  return status === "active" || status === "paused";
}

/** Group sessions into workspaces by customer, alphabetically.
 *
 * Sessions are grouped by their exact (trimmed) customer name rather than by
 * slug, so distinct customers that happen to slugify the same — "Acme, Inc."
 * vs "Acme Inc" → `acme-inc` — stay separate. Slug collisions across those
 * distinct names are disambiguated with a numeric suffix so every workspace
 * still has a unique id. (Guard until workspaces become a real backend entity.)
 */
export function groupWorkspaces(sessions: readonly WorkspaceSession[]): Workspace[] {
  const byCustomer = new Map<string, WorkspaceSession[]>();
  for (const session of sessions) {
    const key = session.customer.trim();
    const existing = byCustomer.get(key);
    if (existing) existing.push(session);
    else byCustomer.set(key, [session]);
  }

  const entries = Array.from(byCustomer.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  const usedIds = new Set<string>();
  return entries.map(([name, groupedSessions]) => {
    const base = slugifyCustomer(name);
    let id = base;
    for (let n = 2; usedIds.has(id); n++) id = `${base}-${n}`;
    usedIds.add(id);
    return {
      id,
      name,
      description: "",
      industry: "",
      website: "",
      session_count: groupedSessions.length,
      sessions: groupedSessions,
    };
  });
}

export function findWorkspace(workspaces: Workspace[], id: string | null): Workspace | undefined {
  return workspaces.find((w) => w.id === id);
}

/** Workspaces derived from the live sessions list. */
export function useWorkspaces() {
  const query = useQuery({
    queryKey: ["workspaces"],
    queryFn: async (): Promise<Workspace[]> =>
      (await api.listWorkspaces()).map((workspace) => ({
        ...workspace,
        description: workspace.description ?? "",
        industry: workspace.industry ?? "",
        website: workspace.website ?? "",
      })),
    staleTime: 15_000,
  });
  return { ...query, workspaces: query.data ?? [] };
}

export interface RegisterRow {
  artifact: DiscoveryArtifact;
  sessionId: string;
  sessionTitle: string;
}

/**
 * Whether an artifact belongs in the requirements register / package totals.
 * Rejected artifacts (by status or validation state) are excluded. Shared by
 * the workspace Overview and the per-session Package view so their counts agree.
 */
export function isRegisterArtifact(artifact: DiscoveryArtifact): boolean {
  return artifact.status !== "rejected" && artifact.validation_state !== "rejected";
}

/**
 * Whether an artifact is still awaiting human validation — a model-inferred
 * candidate that has not yet been confirmed, rejected, or otherwise resolved.
 * These are exactly the items the Validation inbox surfaces: nothing here is
 * baselined into the discovery package until a facilitator acts on it.
 */
export function needsReview(artifact: DiscoveryArtifact): boolean {
  return artifact.status === "candidate" && isRegisterArtifact(artifact);
}

/** Band a 0–1 confidence into the low/med/high buckets the inbox colors by. */
export function confidenceBand(confidence: number): "low" | "med" | "high" {
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.6) return "med";
  return "low";
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
        if (!isRegisterArtifact(artifact)) continue;
        out.push({ artifact, sessionId: session.id, sessionTitle: session.title });
      }
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions, results.map((r) => r.dataUpdatedAt).join(",")]);

  return { rows, isLoading };
}

/** A candidate awaiting validation, joined to its source conversation and the
 * transcript evidence it was derived from. */
export interface ReviewItem extends RegisterRow {
  evidence: EvidenceLink[];
}

/**
 * Everything across a workspace that still needs human validation, with each
 * item joined to the evidence it was derived from. Backs the Validation inbox.
 *
 * Reuses the same query keys as the per-session artifact/evidence hooks, so
 * React Query dedupes the fetches with any conversation view already open and a
 * confirm/reject elsewhere refreshes the inbox automatically.
 */
export function useWorkspaceReview(sessions: WorkspaceSession[]): {
  items: ReviewItem[];
  isLoading: boolean;
} {
  const artifactResults = useQueries({
    queries: sessions.map((s) => ({
      queryKey: ["artifacts", s.id] as const,
      queryFn: () => api.listArtifacts(s.id),
    })),
  });
  const evidenceResults = useQueries({
    queries: sessions.map((s) => ({
      queryKey: ["session-evidence", s.id] as const,
      queryFn: () => api.getSessionEvidence(s.id),
    })),
  });

  const isLoading = artifactResults.some((r) => r.isLoading);

  // Data-freshness stamps: re-derive only when a query actually refetches.
  const artifactStamp = artifactResults.map((r) => r.dataUpdatedAt).join(",");
  const evidenceStamp = evidenceResults.map((r) => r.dataUpdatedAt).join(",");

  const items = useMemo(() => {
    const out: ReviewItem[] = [];
    sessions.forEach((session, i) => {
      const artifacts = artifactResults[i]?.data ?? [];
      const evidence = evidenceResults[i]?.data ?? [];
      const byArtifact = new Map<string, EvidenceLink[]>();
      for (const link of evidence) {
        const list = byArtifact.get(link.artifact_id);
        if (list) list.push(link);
        else byArtifact.set(link.artifact_id, [link]);
      }
      for (const artifact of artifacts) {
        if (!needsReview(artifact)) continue;
        out.push({
          artifact,
          sessionId: session.id,
          sessionTitle: session.title,
          evidence: byArtifact.get(artifact.id) ?? [],
        });
      }
    });
    // Lowest-confidence first: the items that most need a human eye rise to the top.
    out.sort((a, b) => a.artifact.confidence - b.artifact.confidence);
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions, artifactStamp, evidenceStamp]);

  return { items, isLoading };
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
