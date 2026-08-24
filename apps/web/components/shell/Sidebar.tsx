"use client";

import { useNavStore, type ShellView } from "@/lib/nav-store";
import { useAnalysisSettings } from "@/lib/hooks";
import { useWorkspaceArtifacts, type Workspace } from "@/lib/workspaces";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

function statusDot(status: string) {
  if (status === "active") return "live-dot";
  if (status === "draft" || status === "paused") return "draft-dot";
  return "done-dot";
}

export function Sidebar({
  workspaces,
  active,
  onNewConversation,
}: {
  workspaces: Workspace[];
  active: Workspace | undefined;
  onNewConversation: () => void;
}) {
  const view = useNavStore((s) => s.view);
  const activeSessionId = useNavStore((s) => s.activeSessionId);
  const setView = useNavStore((s) => s.setView);
  const selectSession = useNavStore((s) => s.selectSession);
  const search = useNavStore((s) => s.search);
  const setSearch = useNavStore((s) => s.setSearch);
  const setDrawer = useNavStore((s) => s.setDrawer);
  const toggleSidebar = useNavStore((s) => s.toggleSidebar);
  const toggleDrawer = useNavStore((s) => s.toggleDrawer);
  const settings = useAnalysisSettings();

  // Candidates awaiting validation across the whole workspace — the badge count.
  // rows are already register-scoped (non-rejected), so counting candidates here
  // matches the Validation inbox's needsReview() set. Query keys are shared with
  // the inbox, so React Query dedupes the fetch.
  const { rows: workspaceRows } = useWorkspaceArtifacts(active?.sessions ?? []);
  const reviewCount = workspaceRows.filter((r) => r.artifact.status === "candidate").length;

  const sessions = active?.sessions ?? [];
  const filtered = search.trim()
    ? sessions.filter((s) =>
        `${s.title} ${s.customer} ${s.status}`.toLowerCase().includes(search.trim().toLowerCase()),
      )
    : sessions;

  const providerLabel = settings.data
    ? settings.data.llm_provider === "mock"
      ? "mock LLM"
      : "LLM"
    : "…";
  const modeLabel = settings.data?.context_mode ?? "";

  function onHamburger() {
    if (typeof window !== "undefined" && window.innerWidth <= 820) toggleDrawer();
    else toggleSidebar();
  }

  function openView(v: ShellView) {
    setView(v);
    if (typeof window !== "undefined" && window.innerWidth <= 820) setDrawer(false);
  }

  function openSession(id: string) {
    selectSession(id);
    if (typeof window !== "undefined" && window.innerWidth <= 820) setDrawer(false);
  }

  const NavItem = ({
    v,
    ico,
    label,
    kbd,
    cls,
    badge,
  }: {
    v: ShellView;
    ico: string;
    label: string;
    kbd?: string;
    cls?: string;
    badge?: number;
  }) => (
    <button
      className={`nav-item${cls ? ` ${cls}` : ""}${view === v ? " active" : ""}`}
      onClick={() => openView(v)}
    >
      <span className="ico">{ico}</span>
      <span className="collapse-hide">{label}</span>
      {badge != null && badge > 0 && <span className="nbadge collapse-hide">{badge}</span>}
      {kbd && <span className="kbd collapse-hide">{kbd}</span>}
    </button>
  );

  return (
    <aside className="sidebar">
      <div className="side-top">
        <button className="hamburger" aria-label="Toggle navigation" onClick={onHamburger}>
          <span />
          <span />
          <span />
        </button>
        <div className="brand collapse-hide">
          <div className="mark">SL</div>
          <div>
            <div className="brand-name">SpecLive</div>
            <div className="brand-tag">Discovery Copilot</div>
          </div>
        </div>
      </div>

      <div className="side-scroll">
        <WorkspaceSwitcher workspaces={workspaces} active={active} />

        <button
          className="new-btn"
          onClick={() => {
            onNewConversation();
            if (typeof window !== "undefined" && window.innerWidth <= 820) setDrawer(false);
          }}
        >
          <span className="plus">+</span>
          <span className="collapse-hide">New conversation</span>
        </button>

        <div className="search collapse-hide">
          <span className="mag">⌕</span>
          <input
            placeholder="Search this workspace…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="section-label">Workspace</div>
        <NavItem v="overview" ico="◧" label="Overview" kbd="0" />
        <NavItem v="requirements" ico="≣" label="Requirements" kbd="R" />
        <NavItem v="review" ico="⚑" label="Needs review" cls="review" badge={reviewCount} />

        <div className="section-label">
          Conversations
          <span className="count collapse-hide">{sessions.length}</span>
        </div>
        {filtered.map((session, i) => (
          <button
            key={session.id}
            className={`convo${activeSessionId === session.id ? " active" : ""}`}
            onClick={() => openSession(session.id)}
          >
            <span className="ava">{i + 1}</span>
            <span>
              <span className="subttl">{session.title}</span>
              <span className="meta">
                <span className={statusDot(session.status)} />
                {session.status}
              </span>
            </span>
          </button>
        ))}
        {filtered.length === 0 && (
          <div
            className="collapse-hide"
            style={{ padding: "6px 9px", fontSize: 11, color: "var(--muted)" }}
          >
            No conversations match.
          </div>
        )}

        <div className="section-label">This conversation</div>
        <NavItem v="live" ico="▤" label="Live view" kbd="1" />
        <NavItem v="structure" ico="⑃" label="Conversation structure" kbd="2" />
        <NavItem v="package" ico="⤓" label="Discovery package" kbd="3" />

        <div className="section-label">Library</div>
        <NavItem v="database" ico="⊟" label="Database" kbd="4" />
        <NavItem v="scripts" ico="▧" label="Scripts" kbd="5" />
      </div>

      <div className="side-foot">
        <div className="mode-pill collapse-hide">
          <span className="d" />
          {modeLabel ? `${modeLabel} · ${providerLabel}` : providerLabel}
        </div>
        <div className="user">
          <span className="uava">RB</span>
          <span className="collapse-hide">
            <div className="uname">Facilitator</div>
            <div className="urole">SpecLive</div>
          </span>
          <span className="gear collapse-hide">⚙</span>
        </div>
      </div>
    </aside>
  );
}
