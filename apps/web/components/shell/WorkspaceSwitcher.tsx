"use client";

import { useNavStore } from "@/lib/nav-store";
import { initials, type Workspace } from "@/lib/workspaces";
import { useToast } from "@/lib/toast";

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
  const toast = useToast((s) => s.show);

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
        <span className="caret collapse-hide">▾</span>
      </button>
      {wsMenuOpen && (
        <div className="ws-menu collapse-hide" onClick={(e) => e.stopPropagation()}>
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
              toast("New workspace — create a session with a new customer to start one");
            }}
          >
            <span style={{ fontSize: 16 }}>+</span> New workspace
          </button>
        </div>
      )}
    </div>
  );
}
