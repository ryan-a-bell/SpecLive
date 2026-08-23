import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const storageData = {
    backend: "local",
    persist_audio: true,
    schema_version: "1",
    local_root: "./data",
  };
  return {
    storageData,
    storage: {
      data: { ...storageData } as Record<string, unknown> | undefined,
      isLoading: false,
    },
  };
});
const { storageData } = mocks;

vi.mock("@/lib/hooks", () => ({
  useStorageSettings: () => mocks.storage,
  useAnalysisSettings: () => ({
    data: { context_mode: "full", window_seconds: 300, auto_analyze: true, llm_provider: "mock" },
    isLoading: false,
  }),
  useTranscriptionCapability: () => ({
    data: { available: true, supports_partials: true, supports_speaker_detection: false },
    isLoading: false,
  }),
}));

import { SettingsView } from "./SettingsView";

describe("SettingsView", () => {
  it("shows the local backend and root path from live config", () => {
    mocks.storage = { data: { ...storageData }, isLoading: false };
    render(<SettingsView />);
    // The active backend segment and the root path are surfaced.
    expect(screen.getByText("Local directory")).toBeInTheDocument();
    expect(screen.getByText("./data")).toBeInTheDocument();
    // "Where your data lives" resolves the relative root for display.
    expect(screen.getByText(/API working dir/)).toBeInTheDocument();
  });

  it("switches the location readout to the database table for the database backend", () => {
    mocks.storage = {
      data: { backend: "database", persist_audio: true, schema_version: "1", local_root: null },
      isLoading: false,
    };
    render(<SettingsView />);
    expect(screen.getByText(/database · table/)).toBeInTheDocument();
  });

  it("omits the raw/ recording folder from the layout when audio is not persisted", () => {
    mocks.storage = {
      data: { ...storageData, persist_audio: false },
      isLoading: false,
    };
    render(<SettingsView />);
    expect(screen.getByText(/audio not stored/)).toBeInTheDocument();
  });

  it("marks Data & privacy as a future enhancement", () => {
    mocks.storage = { data: { ...storageData }, isLoading: false };
    render(<SettingsView />);
    fireEvent.click(screen.getByRole("tab", { name: /Data & privacy/ }));
    expect(screen.getByText(/Planned, not yet available/)).toBeInTheDocument();
  });
});
