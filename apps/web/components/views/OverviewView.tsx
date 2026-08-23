"use client";

import { useMemo, useState } from "react";
import type { ArtifactType } from "@rdc/domain";
import { useNavStore } from "@/lib/nav-store";
import {
  ARTIFACT_TYPE_LABEL,
  isLiveSession,
  statusPill,
  useWorkspaceArtifacts,
  type Workspace,
} from "@/lib/workspaces";

const FILTERS: { id: ArtifactType | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "objective", label: "Objective" },
  { id: "stakeholder_need", label: "Need" },
  { id: "requirement", label: "Requirement" },
  { id: "constraint", label: "Constraint" },
  { id: "risk", label: "Risk" },
  { id: "open_question", label: "Open question" },
];

export function OverviewView({ workspace }: { workspace: Workspace }) {
  const selectSession = useNavStore((s) => s.selectSession);
  const setView = useNavStore((s) => s.setView);
  const { rows, isLoading } = useWorkspaceArtifacts(workspace.sessions);
  const [filter, setFilter] = useState<ArtifactType | "all">("all");

  const { requirements, confirmed, questions } = useMemo(() => {
    let confirmed = 0;
    let questions = 0;
    const requirements: typeof rows = [];
    for (const r of rows) {
      if (r.artifact.artifact_type === "requirement") requirements.push(r);
      if (r.artifact.artifact_type === "open_question") questions++;
      if (r.artifact.status === "confirmed" || r.artifact.status === "baselined") confirmed++;
    }
    return { requirements, confirmed, questions };
  }, [rows]);

  const perSession = useMemo(() => {
    const counts = new Map<string, number>();
    for (const r of rows) {
      if (r.artifact.artifact_type === "requirement") {
        counts.set(r.sessionId, (counts.get(r.sessionId) ?? 0) + 1);
      }
    }
    return counts;
  }, [rows]);

  const visible = filter === "all" ? rows : rows.filter((r) => r.artifact.artifact_type === filter);

  return (
    <section>
      <div className="ov-head">
        <div>
          <div className="ov-title">{workspace.name}</div>
          <div className="ov-subtitle">
            {workspace.sessions.length}{" "}
            {workspace.sessions.length === 1 ? "conversation" : "conversations"} in this workspace
          </div>
        </div>
      </div>

      <div className="summary">
        <div className="metric">
          <div className="label">Conversations</div>
          <div className="value">{workspace.sessions.length}</div>
        </div>
        <div className="metric">
          <div className="label">Requirements (all calls)</div>
          <div className="value">{requirements.length}</div>
        </div>
        <div className="metric">
          <div className="label">Confirmed / baselined</div>
          <div className="value">{confirmed}</div>
        </div>
        <div className="metric">
          <div className="label">Open questions</div>
          <div className="value">{questions}</div>
        </div>
        <div className="metric">
          <div className="label">Total artifacts</div>
          <div className="value">{rows.length}</div>
        </div>
      </div>

      <div className="section-label" style={{ paddingLeft: 2 }}>
        Conversations
      </div>
      <div className="conv-cards">
        {workspace.sessions.map((session, i) => {
          const live = isLiveSession(session.status);
          return (
            <button key={session.id} className="conv-card" onClick={() => selectSession(session.id)}>
              <div className="cc-top">
                <span className="cc-ico">{i + 1}</span>
                <div>
                  <div className="cc-name">{session.title}</div>
                  <div className="cc-when">{session.status}</div>
                </div>
              </div>
              <div className="cc-snip">{session.customer}</div>
              <div className="cc-foot">
                {live && <span className="cc-stat live">● Live</span>}
                <span className="cc-stat">{perSession.get(session.id) ?? 0} req</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="section-label" style={{ paddingLeft: 2 }}>
        Requirements register · every conversation
      </div>
      <div className="reg-toolbar">
        <div className="reg-chips">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              className={`reg-chip${filter === f.id ? " active" : ""}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="reg-wrap">
        <table className="register">
          <thead>
            <tr>
              <th>ID</th>
              <th>Item</th>
              <th>Type</th>
              <th>Source conversation</th>
              <th>Status</th>
              <th>Conf.</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => {
              const pill = statusPill(row.artifact.status);
              return (
                <tr
                  key={row.artifact.id}
                  onClick={() => {
                    selectSession(row.sessionId);
                    setView("live");
                  }}
                >
                  <td className="rid">{row.artifact.title}</td>
                  <td className="ritem">{row.artifact.statement}</td>
                  <td>
                    <span className="rcell-type">
                      <i className={`type-dot ${row.artifact.artifact_type}`} />
                      {ARTIFACT_TYPE_LABEL[row.artifact.artifact_type]}
                    </span>
                  </td>
                  <td className="rsource">{row.sessionTitle}</td>
                  <td>
                    <span className={`reg-pill ${pill.cls}`}>{pill.label}</span>
                  </td>
                  <td>{Math.round(row.artifact.confidence * 100)}%</td>
                </tr>
              );
            })}
            {!isLoading && visible.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--muted)", textAlign: "center" }}>
                  No artifacts yet for this filter.
                </td>
              </tr>
            )}
            {isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--muted)", textAlign: "center" }}>
                  Loading requirements across conversations…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
