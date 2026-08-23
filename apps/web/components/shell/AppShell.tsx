"use client";

import { useEffect } from "react";
import { CONVERSATION_VIEWS, useNavStore, VIEW_LABEL, type ShellView } from "@/lib/nav-store";
import { findWorkspace, useWorkspaces } from "@/lib/workspaces";
import { useCreateSession } from "@/lib/hooks";
import { useToast } from "@/lib/toast";
import { Sidebar } from "./Sidebar";
import { LiveView } from "@/components/views/LiveView";
import { StructureView } from "@/components/views/StructureView";
import { PackageView } from "@/components/views/PackageView";
import { OverviewView } from "@/components/views/OverviewView";
import { ReviewInbox } from "@/components/views/ReviewInbox";
import { DatabaseView } from "@/components/views/DatabaseView";
import { ScriptsView } from "@/components/views/ScriptsView";
import { Toaster } from "@/components/ui/Toaster";

const VIEW_KEYS: Record<string, ShellView> = {
  "0": "overview",
  "1": "live",
  "2": "structure",
  "3": "package",
  "4": "database",
  "5": "scripts",
};

export function AppShell() {
  const { workspaces, isLoading } = useWorkspaces();
  const {
    activeWorkspaceId,
    activeSessionId,
    view,
    sidebarCollapsed,
    drawerOpen,
    wsMenuOpen,
    selectSession,
    setView,
    setDrawer,
    setWsMenu,
  } = useNavStore();
  const createSession = useCreateSession();
  const toast = useToast((s) => s.show);

  // Default to the first workspace once sessions load.
  useEffect(() => {
    const first = workspaces[0];
    if (!activeWorkspaceId && first) {
      useNavStore.setState({ activeWorkspaceId: first.id });
    }
  }, [activeWorkspaceId, workspaces]);

  const activeWorkspace = findWorkspace(workspaces, activeWorkspaceId) ?? workspaces[0];
  const sessions = activeWorkspace?.sessions ?? [];

  // Resolve the effective conversation for single-session views.
  const effectiveSessionId =
    (activeSessionId && sessions.some((s) => s.id === activeSessionId)
      ? activeSessionId
      : sessions[0]?.id) ?? null;

  const effectiveSession = sessions.find((s) => s.id === effectiveSessionId);
  const isConversationView = CONVERSATION_VIEWS.includes(view);
  const activeConversation = effectiveSession?.status === "active";

  // Keyboard view switching (ignores typing in inputs).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") return;
      const v = VIEW_KEYS[e.key];
      if (v) setView(v);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setView]);

  // Close the workspace menu on an outside click — only listen while it's open,
  // so the app isn't writing state on every click for the shell's lifetime.
  useEffect(() => {
    if (!wsMenuOpen) return;
    const onClick = () => setWsMenu(false);
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [wsMenuOpen, setWsMenu]);

  function onNewConversation() {
    if (!activeWorkspace) return;
    createSession.mutate(
      {
        title: "New discovery call",
        customer: activeWorkspace.name,
        facilitator: "Facilitator",
      },
      {
        onSuccess: (session) => {
          selectSession(session.id);
          toast(`Started a new conversation in ${activeWorkspace.name}`);
        },
        onError: () => toast("Could not create a conversation — is the API running?"),
      },
    );
  }

  // Navigate to the package view (or Overview when no conversation is active).
  function openPackage() {
    setView(effectiveSessionId ? "package" : "overview");
  }

  const conversationTitle = effectiveSession?.title ?? "…";

  return (
    <div
      className={`app-shell${sidebarCollapsed ? " collapsed" : ""}${drawerOpen ? " drawer-open" : ""}`}
    >
      <Sidebar
        workspaces={workspaces}
        active={activeWorkspace}
        onNewConversation={onNewConversation}
      />

      <div className="app-main">
        <header className="app-topbar">
          <div className="crumb">
            <button
              className="hamburger m-ham"
              aria-label="Open navigation"
              onClick={() => setDrawer(!drawerOpen)}
            >
              <span />
              <span />
              <span />
            </button>
            <div>
              <div className="ctitle">
                {activeWorkspace?.name ?? "SpecLive"}
                {isConversationView && (
                  <>
                    {" "}
                    <span className="sep">›</span> {conversationTitle}
                  </>
                )}
              </div>
              <div className="csub">
                {isConversationView && effectiveSession ? `${effectiveSession.customer} · ` : ""}
                {VIEW_LABEL[view]}
              </div>
            </div>
          </div>
          <div className="top-actions flex items-center gap-[9px]">
            {isConversationView && activeConversation && (
              <span className="status">
                <span
                  className="dot"
                  style={{
                    background: "var(--red)",
                    boxShadow: "0 0 0 5px rgba(255,127,143,0.14)",
                  }}
                />
                Active conversation
              </span>
            )}
            <button className="btn primary" onClick={openPackage}>
              Generate package
            </button>
          </div>
        </header>

        <div className="app-content">
          {isLoading && workspaces.length === 0 && (
            <div className="ws-empty">
              <div>
                <div className="big">◧</div>
                <h2>Loading workspaces…</h2>
                <p>Fetching your discovery conversations from the API.</p>
              </div>
            </div>
          )}

          {!isLoading && workspaces.length === 0 && (
            <div className="ws-empty">
              <div>
                <div className="big">＋</div>
                <h2>No conversations yet</h2>
                <p>
                  Seed the demo session or start a discovery call to create your first workspace.
                  Every call for one customer rolls up into that customer&apos;s workspace.
                </p>
              </div>
            </div>
          )}

          {activeWorkspace && view === "overview" && <OverviewView workspace={activeWorkspace} />}
          {activeWorkspace && view === "review" && <ReviewInbox workspace={activeWorkspace} />}
          {view === "database" && <DatabaseView workspaces={workspaces} />}
          {view === "scripts" && <ScriptsView />}

          {isConversationView &&
            (effectiveSessionId ? (
              <>
                {view === "live" && <LiveView sessionId={effectiveSessionId} />}
                {view === "structure" && <StructureView sessionId={effectiveSessionId} />}
                {view === "package" && <PackageView sessionId={effectiveSessionId} />}
              </>
            ) : (
              activeWorkspace && (
                <div className="ws-empty">
                  <div>
                    <div className="big">＋</div>
                    <h2>No conversation selected</h2>
                    <p>
                      This workspace has no conversations yet. Start a new discovery call to begin
                      capturing traceable requirements.
                    </p>
                    <div className="row">
                      <button className="btn primary" onClick={onNewConversation}>
                        New conversation
                      </button>
                    </div>
                  </div>
                </div>
              )
            ))}
        </div>
      </div>

      {drawerOpen && <div className="scrim show" onClick={() => setDrawer(false)} />}
      <Toaster />
    </div>
  );
}
