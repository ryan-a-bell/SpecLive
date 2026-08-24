"use client";

import { useMemo, useState } from "react";
import { DeleteConversationButton } from "@/components/ui/DeleteConversationDialog";
import { RenameConversationButton } from "@/components/ui/RenameConversationDialog";
import { useNavStore } from "@/lib/nav-store";
import {
  ARTIFACT_TYPE_LABEL,
  initials,
  statusPill,
  useWorkspaceArtifacts,
  type Workspace,
} from "@/lib/workspaces";

export function DatabaseView({ workspaces }: { workspaces: Workspace[] }) {
  const selectWorkspace = useNavStore((state) => state.selectWorkspace);
  const [mode, setMode] = useState<"workspaces" | "artifacts">("workspaces");

  const allSessions = useMemo(
    () => workspaces.flatMap((workspace) => workspace.sessions),
    [workspaces],
  );
  const { rows, isLoading } = useWorkspaceArtifacts(allSessions);

  const sessionToWorkspace = useMemo(() => {
    const map = new Map<string, Workspace>();
    for (const workspace of workspaces) {
      for (const session of workspace.sessions) map.set(session.id, workspace);
    }
    return map;
  }, [workspaces]);

  const requirementCount = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      if (row.artifact.artifact_type !== "requirement") continue;
      const workspaceId = sessionToWorkspace.get(row.sessionId)?.id;
      if (workspaceId) counts.set(workspaceId, (counts.get(workspaceId) ?? 0) + 1);
    }
    return counts;
  }, [rows, sessionToWorkspace]);

  const artifactCount = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) counts.set(row.sessionId, (counts.get(row.sessionId) ?? 0) + 1);
    return counts;
  }, [rows]);

  function openSession(sessionId: string) {
    const workspace = sessionToWorkspace.get(sessionId);
    useNavStore.setState({
      activeWorkspaceId: workspace?.id ?? null,
      activeSessionId: sessionId,
      view: "live",
    });
  }

  return (
    <section>
      <div className="db-toolbar">
        <div className="seg" aria-label="Database view">
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
        <>
          <div className="tiles">
            {workspaces.map((workspace) => (
              <button
                key={workspace.id}
                className="tile"
                onClick={() => selectWorkspace(workspace.id)}
              >
                <div className="thead">
                  <span className="tava">{initials(workspace.name)}</span>
                  <div>
                    <div className="tname">{workspace.name}</div>
                    <div className="topp">{workspace.industry || "Client workspace"}</div>
                  </div>
                </div>
                <div className="snippet">
                  {workspace.description ||
                    workspace.sessions
                      .map((session) => session.title)
                      .slice(0, 2)
                      .join(" · ") ||
                    "No client context yet"}
                </div>
                <div className="tfoot">
                  <span className="tstat good">{requirementCount.get(workspace.id) ?? 0} req</span>
                  <span className="tstat">{workspace.sessions.length} calls</span>
                </div>
              </button>
            ))}
          </div>

          <div className="database-section-head">
            <div>
              <h2>Conversation management</h2>
              <p>Open or permanently remove conversations across every workspace.</p>
            </div>
          </div>
          <div className="reg-wrap">
            <table className="register management-table">
              <thead>
                <tr>
                  <th>Conversation</th>
                  <th>Workspace</th>
                  <th>Status</th>
                  <th>Artifacts</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {allSessions.map((session) => (
                  <tr key={session.id} onClick={() => openSession(session.id)}>
                    <td className="rid">{session.title}</td>
                    <td className="rsource">
                      {sessionToWorkspace.get(session.id)?.name ?? session.customer}
                    </td>
                    <td>
                      <span className="reg-pill candidate">{session.status}</span>
                    </td>
                    <td>{artifactCount.get(session.id) ?? 0}</td>
                    <td className="table-actions">
                      <RenameConversationButton
                        session={session}
                        className="table-action"
                        label="Rename"
                      />
                      <DeleteConversationButton
                        session={session}
                        className="table-action table-delete"
                        label="Delete"
                      />
                    </td>
                  </tr>
                ))}
                {allSessions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="table-empty">
                      No conversations yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="reg-wrap">
          <table className="register database-requirements">
            <thead>
              <tr>
                <th>Title</th>
                <th>Requirement / artifact</th>
                <th>Type</th>
                <th>Workspace</th>
                <th>Source conversation</th>
                <th>Status</th>
                <th>Conf.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const pill = statusPill(row.artifact.status);
                return (
                  <tr key={row.artifact.id} onClick={() => openSession(row.sessionId)}>
                    <td className="rid">{row.artifact.title}</td>
                    <td className="ritem">{row.artifact.statement}</td>
                    <td>
                      <span className="rcell-type">
                        <i className={`type-dot ${row.artifact.artifact_type}`} />
                        {ARTIFACT_TYPE_LABEL[row.artifact.artifact_type]}
                      </span>
                    </td>
                    <td className="rsource">
                      {sessionToWorkspace.get(row.sessionId)?.name ?? "—"}
                    </td>
                    <td className="rsource">{row.sessionTitle}</td>
                    <td>
                      <span className={`reg-pill ${pill.cls}`}>{pill.label}</span>
                    </td>
                    <td>{Math.round(row.artifact.confidence * 100)}%</td>
                  </tr>
                );
              })}
              {!isLoading && rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="table-empty">
                    No requirements or discovery artifacts yet.
                  </td>
                </tr>
              ) : null}
              {isLoading && rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="table-empty">
                    Loading requirements…
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
