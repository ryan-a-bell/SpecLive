"use client";

import { useSession } from "@/lib/hooks";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";

export function TopBar({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const toast = useToast((s) => s.show);

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
