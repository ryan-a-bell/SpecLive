"use client";

import { api } from "@/lib/api";
import { useArtifacts, useCoverage, useSession } from "@/lib/hooks";
import { isRegisterArtifact } from "@/lib/workspaces";
import { useToast } from "@/lib/toast";

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  // The anchor must be in the DOM for a programmatic click to fire in some
  // browsers, and the object URL must stay alive until the browser has read
  // the blob — so revoke on a later tick rather than the same one.
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function PackageView({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const artifacts = useArtifacts(sessionId);
  const coverage = useCoverage(sessionId);
  const toast = useToast((s) => s.show);

  // Match the Overview register, which excludes rejected artifacts, so the
  // "Total artifacts" count here agrees with the same data shown there.
  const all = (artifacts.data ?? []).filter(isRegisterArtifact);
  const confirmed = all.filter((a) => a.status === "confirmed" || a.status === "baselined").length;
  const awaiting = all.filter((a) => a.status === "candidate").length;

  async function exportPackage(format: "markdown" | "json") {
    try {
      const content = await api.exportPackage(sessionId, format);
      download(
        format === "markdown" ? "discovery_package.md" : "discovery_package.json",
        content,
        format === "markdown" ? "text/markdown" : "application/json",
      );
      toast(`Discovery package exported (${format})`);
    } catch {
      toast("Export failed — is the API running?");
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <div className="panel-title">Discovery package</div>
          <div className="panel-subtitle">
            Structured export — every item traceable to transcript evidence
          </div>
        </div>
        <span className="status">JSON · Markdown</span>
      </header>
      <div className="panel-body">
        <p className="mb-3 text-[11px] leading-snug text-[var(--muted)]">
          Export {session.data ? `${session.data.customer} — ${session.data.title}` : "this session"}
          &apos;s objectives, needs, requirements, constraints, assumptions, risks, decisions, and
          open questions — each with source evidence, rationale, confidence, and validation state.
        </p>
        <div className="summary mb-3">
          <div className="metric">
            <div className="label">Total artifacts</div>
            <div className="value">{all.length}</div>
          </div>
          <div className="metric">
            <div className="label">Confirmed / baselined</div>
            <div className="value">{confirmed}</div>
          </div>
          <div className="metric">
            <div className="label">Awaiting validation</div>
            <div className="value">{awaiting}</div>
          </div>
          <div className="metric">
            <div className="label">Coverage</div>
            <div className="value">{coverage.data?.summary.coverage_percent ?? 0}%</div>
          </div>
          <div className="metric">
            <div className="label">Status</div>
            <div className="value">{session.data?.status ?? "…"}</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-[10px]">
          <button className="btn primary" onClick={() => exportPackage("markdown")}>
            Download Markdown
          </button>
          <button className="btn" onClick={() => exportPackage("json")}>
            Download JSON
          </button>
        </div>
      </div>
    </section>
  );
}
