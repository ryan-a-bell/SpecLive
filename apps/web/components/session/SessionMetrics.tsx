"use client";

import { useArtifacts, useCoverage, useSession, useSessionEvidence } from "@/lib/hooks";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] px-3 py-[10px] shadow-panel">
      <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-sm font-extrabold">{value}</div>
    </div>
  );
}

export function SessionMetrics({ sessionId }: { sessionId: string }) {
  const session = useSession(sessionId);
  const artifacts = useArtifacts(sessionId);
  const evidence = useSessionEvidence(sessionId);
  const coverage = useCoverage(sessionId);

  const reqs = (artifacts.data ?? []).filter((a) => a.artifact_type === "requirement");
  const candidates = reqs.filter((a) => a.status === "candidate").length;
  const questions = (artifacts.data ?? []).filter(
    (a) => a.artifact_type === "open_question" && a.validation_state !== "rejected",
  ).length;

  return (
    <section className="grid grid-cols-2 gap-[10px] border-b border-[var(--border)] px-4 py-[11px] md:grid-cols-5">
      <Metric
        label="Customer / Opportunity"
        value={session.data ? `${session.data.customer} — ${session.data.title}` : "…"}
      />
      <Metric label="Requirements" value={`${candidates} candidate`} />
      <Metric label="Evidence links" value={`${evidence.data?.length ?? 0} linked`} />
      <Metric label="Open questions" value={`${questions} open`} />
      <Metric
        label="Discovery coverage"
        value={`${coverage.data?.summary.coverage_percent ?? 0}%`}
      />
    </section>
  );
}
