"use client";

import { useMemo, useState } from "react";
import { WorkspaceDialog } from "@/components/ui/WorkspaceDialog";
import { useNavStore } from "@/lib/nav-store";
import { isLiveSession, useWorkspaceArtifacts, type Workspace } from "@/lib/workspaces";

function websiteHref(value: string): string {
  return /^https?:\/\//i.test(value) ? value : `https://${value}`;
}

export function OverviewView({ workspace }: { workspace: Workspace }) {
  const selectSession = useNavStore((state) => state.selectSession);
  const { rows } = useWorkspaceArtifacts(workspace.sessions);
  const [editOpen, setEditOpen] = useState(false);

  const summary = useMemo(() => {
    let requirements = 0;
    let confirmed = 0;
    let questions = 0;
    const perSession = new Map<string, number>();
    for (const row of rows) {
      if (row.artifact.artifact_type === "requirement") {
        requirements++;
        perSession.set(row.sessionId, (perSession.get(row.sessionId) ?? 0) + 1);
      }
      if (row.artifact.artifact_type === "open_question") questions++;
      if (row.artifact.status === "confirmed" || row.artifact.status === "baselined") confirmed++;
    }
    return { requirements, confirmed, questions, perSession };
  }, [rows]);

  return (
    <section>
      <div className="ov-head">
        <div>
          <div className="ov-title">{workspace.name}</div>
          <div className="ov-subtitle">
            {workspace.sessions.length}{" "}
            {workspace.sessions.length === 1 ? "conversation" : "conversations"}
            {workspace.industry ? ` · ${workspace.industry}` : ""}
          </div>
        </div>
        <button className="btn" onClick={() => setEditOpen(true)}>
          Edit client context
        </button>
      </div>

      <div className="client-context-card">
        <div className="context-kicker">Client context</div>
        <div className="context-body">
          <div>
            <h2>{workspace.name}</h2>
            <p>
              {workspace.description ||
                "Add a short client profile so everyone enters discovery with the same context."}
            </p>
          </div>
          <div className="context-meta">
            <div>
              <span>Industry</span>
              <strong>{workspace.industry || "Not set"}</strong>
            </div>
            <div>
              <span>Website</span>
              {workspace.website ? (
                <a href={websiteHref(workspace.website)} target="_blank" rel="noreferrer">
                  {workspace.website}
                </a>
              ) : (
                <strong>Not set</strong>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="summary overview-summary">
        <div className="metric">
          <div className="label">Conversations</div>
          <div className="value">{workspace.sessions.length}</div>
        </div>
        <div className="metric">
          <div className="label">Requirements</div>
          <div className="value">{summary.requirements}</div>
        </div>
        <div className="metric">
          <div className="label">Confirmed / baselined</div>
          <div className="value">{summary.confirmed}</div>
        </div>
        <div className="metric">
          <div className="label">Open questions</div>
          <div className="value">{summary.questions}</div>
        </div>
      </div>

      <div className="section-label" style={{ paddingLeft: 2 }}>
        Conversations
      </div>
      <div className="conv-cards">
        {workspace.sessions.map((session, index) => {
          const live = isLiveSession(session.status);
          return (
            <button
              key={session.id}
              className="conv-card"
              onClick={() => selectSession(session.id)}
            >
              <div className="cc-top">
                <span className="cc-ico">{index + 1}</span>
                <div>
                  <div className="cc-name">{session.title}</div>
                  <div className="cc-when">{session.status}</div>
                </div>
              </div>
              <div className="cc-snip">
                Open the conversation transcript, structure, and package.
              </div>
              <div className="cc-foot">
                {live ? <span className="cc-stat live">● Live</span> : null}
                <span className="cc-stat">{summary.perSession.get(session.id) ?? 0} req</span>
              </div>
            </button>
          );
        })}
        {workspace.sessions.length === 0 ? (
          <div className="overview-empty">
            <strong>No conversations yet</strong>
            <span>
              Use “New conversation” in the sidebar when you are ready to begin discovery.
            </span>
          </div>
        ) : null}
      </div>

      <WorkspaceDialog open={editOpen} onClose={() => setEditOpen(false)} workspace={workspace} />
    </section>
  );
}
