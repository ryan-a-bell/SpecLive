"use client";

import { useState } from "react";
import type { ArtifactType } from "@rdc/domain";
import { useNavStore } from "@/lib/nav-store";
import {
  ARTIFACT_TYPE_LABEL,
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

export function RequirementsView({ workspace }: { workspace: Workspace }) {
  const selectSession = useNavStore((state) => state.selectSession);
  const setView = useNavStore((state) => state.setView);
  const { rows, isLoading } = useWorkspaceArtifacts(workspace.sessions);
  const [filter, setFilter] = useState<ArtifactType | "all">("all");
  const visible =
    filter === "all" ? rows : rows.filter((row) => row.artifact.artifact_type === filter);

  return (
    <section>
      <div className="ov-head">
        <div>
          <div className="ov-title">Requirements</div>
          <div className="ov-subtitle">All discovery artifacts across {workspace.name}</div>
        </div>
      </div>
      <div className="reg-toolbar">
        <div className="reg-chips">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              className={`reg-chip${filter === item.id ? " active" : ""}`}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      <div className="reg-wrap">
        <table className="register">
          <thead>
            <tr>
              <th>Title</th>
              <th>Requirement / artifact</th>
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
            {!isLoading && visible.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty">
                  No artifacts yet for this filter.
                </td>
              </tr>
            ) : null}
            {isLoading && rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty">
                  Loading requirements across conversations…
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
