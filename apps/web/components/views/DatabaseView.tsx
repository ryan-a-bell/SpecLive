"use client";

import { useMemo, useState } from "react";
import { useNavStore } from "@/lib/nav-store";
import {
  ARTIFACT_TYPE_LABEL,
  initials,
  statusPill,
  useWorkspaceArtifacts,
  type Workspace,
} from "@/lib/workspaces";

export function DatabaseView({ workspaces }: { workspaces: Workspace[] }) {
  const selectWorkspace = useNavStore((s) => s.selectWorkspace);
  const [mode, setMode] = useState<"workspaces" | "artifacts">("workspaces");

  const allSessions = useMemo(() => workspaces.flatMap((w) => w.sessions), [workspaces]);
  const { rows } = useWorkspaceArtifacts(allSessions);

  const reqCountByWorkspace = useMemo(() => {
    const sessionToWs = new Map<string, string>();
    for (const w of workspaces) for (const s of w.sessions) sessionToWs.set(s.id, w.id);
    const counts = new Map<string, number>();
    for (const r of rows) {
      if (r.artifact.artifact_type !== "requirement") continue;
      const ws = sessionToWs.get(r.sessionId);
      if (ws) counts.set(ws, (counts.get(ws) ?? 0) + 1);
    }
    return counts;
  }, [rows, workspaces]);

  const sessionTitleToWorkspace = useMemo(() => {
    const map = new Map<string, string>();
    for (const w of workspaces) for (const s of w.sessions) map.set(s.id, w.name);
    return map;
  }, [workspaces]);

  return (
    <section>
      <div className="db-toolbar">
        <div className="seg">
          <button
            className={mode === "workspaces" ? "active" : ""}
            onClick={() => setMode("workspaces")}
          >
            Workspaces
          </button>
          <button
            className={mode === "artifacts" ? "active" : ""}
            onClick={() => setMode("artifacts")}
          >
            Requirements
          </button>
        </div>
      </div>

      {mode === "workspaces" ? (
        <div className="tiles">
          {workspaces.map((w) => (
            <button key={w.id} className="tile" onClick={() => selectWorkspace(w.id)}>
              <div className="thead">
                <span className="tava">{initials(w.name)}</span>
                <div>
                  <div className="tname">{w.name}</div>
                  <div className="topp">
                    {w.sessions.length}{" "}
                    {w.sessions.length === 1 ? "conversation" : "conversations"}
                  </div>
                </div>
              </div>
              <div className="snippet">
                {w.sessions.map((s) => s.title).slice(0, 2).join(" · ") || "No conversations yet"}
              </div>
              <div className="tfoot">
                <span className="tstat good">{reqCountByWorkspace.get(w.id) ?? 0} req</span>
                <span className="tstat">{w.sessions.length} calls</span>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="tiles">
          {rows.map((row) => {
            const pill = statusPill(row.artifact.status);
            return (
              <div key={row.artifact.id} className="tile">
                <div className="thead">
                  <i className={`type-dot ${row.artifact.artifact_type}`} />
                  <span className="tname" style={{ fontSize: 12 }}>
                    {row.artifact.title}
                  </span>
                  <span className="tstat" style={{ marginLeft: "auto" }}>
                    {Math.round(row.artifact.confidence * 100)}%
                  </span>
                </div>
                <div className="snippet">{row.artifact.statement}</div>
                <div className="tfoot">
                  <span className={`tstat${pill.cls === "confirmed" ? " good" : ""}`}>
                    {ARTIFACT_TYPE_LABEL[row.artifact.artifact_type]}
                  </span>
                  <span className="tstat">
                    {sessionTitleToWorkspace.get(row.sessionId) ?? row.sessionTitle}
                  </span>
                </div>
              </div>
            );
          })}
          {rows.length === 0 && (
            <div style={{ color: "var(--muted)", fontSize: 12 }}>No artifacts yet.</div>
          )}
        </div>
      )}
    </section>
  );
}
