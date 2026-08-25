"use client";

import { useState } from "react";
import { ChevronDown, Plus } from "lucide-react";
import { useNavStore } from "@/lib/nav-store";
import { initials, type Workspace } from "@/lib/workspaces";
import { WorkspaceDialog } from "@/components/ui/WorkspaceDialog";

export function WorkspaceSwitcher({
  workspaces,
  active,
}: {
  workspaces: Workspace[];
  active: Workspace | undefined;
}) {
  const wsMenuOpen = useNavStore((s) => s.wsMenuOpen);
  const toggleWsMenu = useNavStore((s) => s.toggleWsMenu);
  const setWsMenu = useNavStore((s) => s.setWsMenu);
  const selectWorkspace = useNavStore((s) => s.selectWorkspace);
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <div className="ws-switch">
      <button
        className="ws-btn"
        onClick={(e) => {
          e.stopPropagation();
          toggleWsMenu();
        }}
      >
        <span className="wmark">{active ? initials(active.name) : "?"}</span>
        <span className="wmeta collapse-hide">
          <span className="wlabel">Workspace</span>
          <span className="wname">{active?.name ?? "Select workspace"}</span>
        </span>
        <span className="caret collapse-hide">
          <ChevronDown size={14} strokeWidth={2} />
        </span>
      </button>
      {wsMenuOpen && (
        <div className="ws-menu" onClick={(e) => e.stopPropagation()}>
          <div className="mlabel">Switch workspace</div>
          {workspaces.map((w) => (
            <button
              key={w.id}
              className={`ws-opt${active?.id === w.id ? " active" : ""}`}
              onClick={() => selectWorkspace(w.id)}
            >
              <span className="wmark">{initials(w.name)}</span>
              <span>
                <div className="on">{w.name}</div>
                <div className="om">
                  {w.sessions.length} {w.sessions.length === 1 ? "call" : "calls"}
                </div>
              </span>
              <span className="obadge">{w.sessions.length}</span>
            </button>
          ))}
          <button
            className="newws"
            onClick={() => {
              setWsMenu(false);
              setCreateOpen(true);
            }}
          >
            <Plus size={15} strokeWidth={2} /> New workspace
          </button>
        </div>
      )}
      <WorkspaceDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
