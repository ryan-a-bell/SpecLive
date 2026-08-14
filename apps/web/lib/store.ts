import { create } from "zustand";

interface WorkspaceState {
  selectedArtifactId: string | null;
  selectedSegmentId: string | null;
  activeBranchId: string | null;
  composerText: string;
  selectArtifact: (id: string | null) => void;
  selectSegment: (id: string | null) => void;
  setActiveBranch: (id: string | null) => void;
  setComposerText: (text: string) => void;
  loadPrompt: (text: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  selectedArtifactId: null,
  selectedSegmentId: null,
  activeBranchId: null,
  composerText: "",
  selectArtifact: (selectedArtifactId) => set({ selectedArtifactId }),
  selectSegment: (selectedSegmentId) => set({ selectedSegmentId }),
  setActiveBranch: (activeBranchId) => set({ activeBranchId }),
  setComposerText: (composerText) => set({ composerText }),
  loadPrompt: (composerText) => set({ composerText }),
}));
