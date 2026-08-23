"use client";

import { create } from "zustand";

/** The primary surfaces the shell can show. */
export type ShellView = "overview" | "live" | "structure" | "package" | "database";

/** Views that operate on a single conversation (need an active session). */
export const CONVERSATION_VIEWS: ShellView[] = ["live", "structure", "package"];

/** Views that operate on the whole workspace (or the library). */
export const WORKSPACE_VIEWS: ShellView[] = ["overview", "database"];

export const VIEW_LABEL: Record<ShellView, string> = {
  overview: "Overview",
  live: "Live view",
  structure: "Conversation structure",
  package: "Discovery package",
  database: "Database",
};

interface NavState {
  activeWorkspaceId: string | null;
  activeSessionId: string | null;
  view: ShellView;
  sidebarCollapsed: boolean;
  drawerOpen: boolean;
  wsMenuOpen: boolean;
  search: string;

  /** Switch workspace and land on its cross-section Overview. */
  selectWorkspace: (id: string) => void;
  /** Open a conversation (single session) in its Live view. */
  selectSession: (id: string) => void;
  setView: (view: ShellView) => void;
  toggleSidebar: () => void;
  toggleDrawer: () => void;
  setDrawer: (open: boolean) => void;
  toggleWsMenu: () => void;
  setWsMenu: (open: boolean) => void;
  setSearch: (search: string) => void;
}

export const useNavStore = create<NavState>((set) => ({
  activeWorkspaceId: null,
  activeSessionId: null,
  view: "live",
  sidebarCollapsed: false,
  drawerOpen: false,
  wsMenuOpen: false,
  search: "",

  selectWorkspace: (activeWorkspaceId) =>
    set({ activeWorkspaceId, activeSessionId: null, view: "overview", wsMenuOpen: false }),
  selectSession: (activeSessionId) => set({ activeSessionId, view: "live" }),
  setView: (view) => set({ view }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  setDrawer: (drawerOpen) => set({ drawerOpen }),
  toggleWsMenu: () => set((s) => ({ wsMenuOpen: !s.wsMenuOpen })),
  setWsMenu: (wsMenuOpen) => set({ wsMenuOpen }),
  setSearch: (search) => set({ search }),
}));
