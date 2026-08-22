"use client";

import { useAnalysisSettings, useSession } from "@/lib/hooks";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";

const MODE_LABEL: Record<string, string> = {
  full: "full transcript",
  window: "sliding window",
  segment: "per segment",
};

const PROVIDER_LABEL: Record<string, string> = {
  mock: "mock",
  openai_compatible: "LLM",
};

export function TopBar({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const settings = useAnalysisSettings();
  const toast = useToast((s) => s.show);

  const s = settings.data;
  const modeLabel = s ? (MODE_LABEL[s.context_mode] ?? s.context_mode) : null;
  const modeDetail = s?.context_mode === "window" ? ` · ${Math.round(s.window_seconds)}s` : "";
  const providerLabel = s ? (PROVIDER_LABEL[s.llm_provider] ?? s.llm_provider) : null;
  const providerHost = s?.llm_api_base
    ? s.llm_api_base.replace(/^https?:\/\//, "").replace(/\/v1\/?$/, "")
    : null;

  async function generatePackage() {
    try {
      const markdown = await api.exportPackage(sessionId, "markdown");
      const blob = new Blob([markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "discovery_package.md";
      a.click();
      URL.revokeObjectURL(url);
      toast("Discovery package generated");
    } catch {
      toast("Export failed — is the API running?");
    }
  }

  return (
    <header className="sticky top-0 z-10 flex h-[66px] items-center justify-between border-b border-[var(--border)] bg-[rgba(8,15,28,0.9)] px-5 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="grid h-9 w-9 place-items-center rounded-[11px] bg-[linear-gradient(135deg,var(--blue),var(--purple))] font-black">
          R4
        </div>
        <div>
          <h1 className="m-0 text-base">Requirements Discovery Copilot</h1>
          <div className="mt-[2px] text-xs text-[var(--muted)]">
            Script-anchored conversation → derivative branches → traceable requirements
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-[9px]">
        {s && (
          <span
            className="status"
            title={
              `Requirement derivation runs in "${s.context_mode}" context mode` +
              (s.context_mode === "window" ? ` (${Math.round(s.window_seconds)}s windows)` : "") +
              ` via the ${s.llm_provider} provider` +
              (providerHost ? ` at ${providerHost}` : "") +
              `. Auto-analyze is ${s.auto_analyze ? "on" : "off"}. ` +
              "Read-only — set via server environment variables."
            }
          >
            <span
              className="inline-block h-[7px] w-[7px] rounded-full"
              style={{
                background:
                  s.llm_provider === "mock" ? "var(--muted)" : "var(--purple)",
              }}
            />
            {modeLabel}
            {modeDetail} · {providerLabel}
            {providerHost ? ` → ${providerHost}` : ""}
          </span>
        )}
        <span className="status">
          <span className="dot" /> {session.data?.status ?? "loading"}
        </span>
        <button className="btn primary" onClick={generatePackage}>
          Generate call package
        </button>
      </div>
    </header>
  );
}
