"use client";

import { useEvidence, useConfirmArtifact, useRejectArtifact, useArtifacts } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import { Panel } from "@/components/ui/Panel";

export function ArtifactDetail({ sessionId }: { sessionId: string }) {
  const selectedArtifactId = useWorkspaceStore((s) => s.selectedArtifactId);
  const selectSegment = useWorkspaceStore((s) => s.selectSegment);
  const artifacts = useArtifacts(sessionId);
  const evidence = useEvidence(selectedArtifactId);
  const confirm = useConfirmArtifact(sessionId);
  const reject = useRejectArtifact(sessionId);
  const toast = useToast((s) => s.show);

  const artifact = artifacts.data?.find((a) => a.id === selectedArtifactId) ?? null;

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
              <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                Status / confidence
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
              <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
                Derivation rationale
              </div>
              <div className="mt-1 text-xs leading-snug">{artifact.rationale ?? "—"}</div>
              <div className="mt-2 grid gap-[6px]">
                {evidence.data?.map((link) => (
                  <button
                    key={link.id}
                    className="cursor-pointer rounded-[7px] border-l-[3px] border-[var(--blue)] bg-[var(--panel3)] px-2 py-[7px] text-left text-[11px]"
                    onClick={() => jumpTo(link.transcript_segment_id)}
                  >
                    {link.transcript_segment_id} · {link.relationship}: “{link.quoted_text}”
                  </button>
                ))}
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
