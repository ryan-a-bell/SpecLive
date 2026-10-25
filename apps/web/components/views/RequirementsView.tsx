"use client";

import { RequirementsTable } from "@/components/requirements/RequirementsTable";
import { useNavStore } from "@/lib/nav-store";
import { useWorkspaceArtifacts, type Workspace } from "@/lib/workspaces";

export function RequirementsView({ workspace }: { workspace: Workspace }) {
  const selectSession = useNavStore((state) => state.selectSession);
  const setView = useNavStore((state) => state.setView);
  const { rows, isLoading } = useWorkspaceArtifacts(workspace.sessions);

  return (
    <section>
      <div className="ov-head">
        <div>
          <div className="ov-title">Requirements</div>
          <div className="ov-subtitle">All discovery artifacts across {workspace.name}</div>
        </div>
      </div>
      <RequirementsTable
        rows={rows}
        isLoading={isLoading}
        onOpenSession={(sessionId) => {
          selectSession(sessionId);
          setView("live");
        }}
      />
    </section>
  );
}
