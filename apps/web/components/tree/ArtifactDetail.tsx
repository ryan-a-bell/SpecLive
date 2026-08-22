"use client";

import {
  useEvidence,
  useConfirmArtifact,
  useRejectArtifact,
  useArtifacts,
  useTranscript,
} from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import { Panel } from "@/components/ui/Panel";

// How a candidate artifact was produced. LLM vs. keyword_heuristic is the
// signal that tells a reviewer whether a real model connected cross-turn
// evidence or a regex matched a single phrase.
const METHOD_META: Record<string, { label: string; color: string; bg: string }> = {
  llm: { label: "LLM", color: "#d6cbff", bg: "rgba(182,147,255,0.14)" },
  keyword_heuristic: { label: "keyword", color: "var(--muted)", bg: "var(--panel3)" },
  manual: { label: "manual", color: "#cdf6e3", bg: "rgba(100,214,155,0.14)" },
  imported: { label: "imported", color: "#d6e7ff", bg: "rgba(103,168,255,0.14)" },
};

export function ArtifactDetail({ sessionId }: { sessionId: string }) {
  const selectedArtifactId = useWorkspaceStore((s) => s.selectedArtifactId);
  const selectSegment = useWorkspaceStore((s) => s.selectSegment);
  const artifacts = useArtifacts(sessionId);
  const evidence = useEvidence(selectedArtifactId);
  const transcript = useTranscript(sessionId);
  const confirm = useConfirmArtifact(sessionId);
  const reject = useRejectArtifact(sessionId);
  const toast = useToast((s) => s.show);

  const artifact = artifacts.data?.find((a) => a.id === selectedArtifactId) ?? null;

  // Resolve each evidence link's segment id to who actually said it, so the
  // provenance reads "Elena: …" instead of a raw UUID — and multi-segment
  // evidence (the hallmark of a cross-turn LLM derivation) is legible.
  const speakerFor = (segmentId: string): string => {
    const seg = transcript.data?.find((t) => t.id === segmentId);
    if (!seg) return segmentId.slice(0, 8);
    return seg.speaker_name ?? seg.speaker;
  };

  const method = artifact ? (METHOD_META[artifact.derivation_method] ?? null) : null;
  const distinctSegments = new Set((evidence.data ?? []).map((l) => l.transcript_segment_id)).size;

  function jumpTo(segmentId: string) {
    selectSegment(segmentId);
    document.getElementById(segmentId)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <Panel
      title="Selected node provenance"
      subtitle="Source, interpretation, rationale, and status"
      aside={<span className="status">{artifact?.id ?? "—"}</span>}
      className="h-[280px]"
    >
      {!artifact && (
        <p className="text-xs text-[var(--muted)]">
          Select an artifact from the tree, a transcript badge, or an evidence highlight.
        </p>
      )}
      {artifact && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="detail-box">
              <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Type</div>
              <div className="mt-1 text-xs">{artifact.artifact_type.replace(/_/g, " ")}</div>
            </div>
            <div className="detail-box">
              <div className="flex items-center justify-between gap-1">
                <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                  Status / confidence
                </div>
                {method && (
                  <span
                    className="rounded-[5px] px-[6px] py-[2px] font-mono text-[9px] font-semibold"
                    style={{ color: method.color, background: method.bg }}
                    title={`Derivation method: ${artifact.derivation_method}`}
                  >
                    {method.label}
                  </span>
                )}
              </div>
              <div className="mt-1 text-xs">
                {artifact.validation_state.replace(/_/g, " ")} ·{" "}
                {artifact.confidence > 0 ? `${Math.round(artifact.confidence * 100)}%` : "—"}
              </div>
            </div>
            <div className="detail-box col-span-2">
              <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                Interpreted node
              </div>
              <div className="mt-1 text-xs leading-snug">{artifact.statement}</div>
            </div>
            <div className="detail-box col-span-2">
              <div className="flex items-center justify-between gap-1">
                <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                  Derivation rationale
                </div>
                {distinctSegments > 1 && (
                  <span
                    className="rounded-[5px] bg-[rgba(182,147,255,0.14)] px-[6px] py-[2px] text-[9px] font-semibold text-[#d6cbff]"
                    title="This artifact was connected from evidence in more than one transcript turn"
                  >
                    cross-turn · {distinctSegments} segments
                  </span>
                )}
              </div>
              <div className="mt-1 text-xs leading-snug">{artifact.rationale ?? "—"}</div>
              <div className="mt-2 grid gap-[6px]">
                {evidence.data?.map((link) => (
                  <button
                    key={link.id}
                    className="cursor-pointer rounded-[7px] border-l-[3px] border-[var(--blue)] bg-[var(--panel3)] px-2 py-[7px] text-left text-[11px]"
                    onClick={() => jumpTo(link.transcript_segment_id)}
                    title="Jump to this turn in the transcript"
                  >
                    <span className="font-mono text-[9px] uppercase tracking-wide text-[var(--blue)]">
                      {speakerFor(link.transcript_segment_id)} · {link.relationship}
                    </span>
                    <span className="mt-[2px] block leading-snug">“{link.quoted_text}”</span>
                  </button>
                ))}
                {evidence.data?.length === 0 && (
                  <span className="text-[11px] text-[var(--muted)]">No evidence linked yet.</span>
                )}
              </div>
            </div>
          </div>
          <div className="mt-[9px] flex flex-wrap gap-[7px]">
            <button
              className="btn"
              onClick={() =>
                confirm.mutate(artifact.id, { onSuccess: () => toast("Artifact confirmed") })
              }
            >
              Confirm
            </button>
            <button
              className="btn"
              onClick={() => toast("Edit mode is available via PATCH /artifacts")}
            >
              Edit
            </button>
            <button
              className="btn"
              onClick={() =>
                reject.mutate(artifact.id, { onSuccess: () => toast("Artifact rejected") })
              }
            >
              Reject
            </button>
          </div>
        </>
      )}
    </Panel>
  );
}
