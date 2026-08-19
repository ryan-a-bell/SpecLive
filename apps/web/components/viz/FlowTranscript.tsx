"use client";

import { useEffect, useMemo, useRef } from "react";
import type { EvidenceLink } from "@rdc/domain";
import { useSessionEvidence, useTranscript } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { EvidenceText } from "@/components/transcript/EvidenceText";

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

/**
 * Read-only transcript companion for the Q&A flow. Reacts to the workspace
 * selection: choosing a question or requirement in the flow highlights the
 * transcript segments (and the exact evidence spans) that support it and
 * scrolls the first one into view.
 */
export function FlowTranscript({ sessionId }: { sessionId: string }) {
  const transcript = useTranscript(sessionId);
  const evidence = useSessionEvidence(sessionId);
  const selectArtifact = useWorkspaceStore((s) => s.selectArtifact);
  const selectedArtifactId = useWorkspaceStore((s) => s.selectedArtifactId);
  const selectedSegmentId = useWorkspaceStore((s) => s.selectedSegmentId);
  const scrollRef = useRef<HTMLDivElement>(null);

  const evidenceBySegment = useMemo(() => {
    const map = new Map<string, EvidenceLink[]>();
    (evidence.data ?? []).forEach((link) => {
      const list = map.get(link.transcript_segment_id) ?? [];
      list.push(link);
      map.set(link.transcript_segment_id, list);
    });
    return map;
  }, [evidence.data]);

  // Segments that carry evidence for the currently-selected artifact.
  const activeSegmentIds = useMemo(() => {
    if (!selectedArtifactId) return new Set<string>();
    const ids = new Set<string>();
    (evidence.data ?? []).forEach((link) => {
      if (link.artifact_id === selectedArtifactId) ids.add(link.transcript_segment_id);
    });
    return ids;
  }, [evidence.data, selectedArtifactId]);

  // Scroll the most relevant segment into view when the selection changes.
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    const targetId =
      selectedSegmentId ??
      (transcript.data ?? []).map((s) => s.id).find((id) => activeSegmentIds.has(id));
    if (!targetId) return;
    const el = container.querySelector<HTMLElement>(`[data-segment-id="${CSS.escape(targetId)}"]`);
    el?.scrollIntoView?.({ behavior: "smooth", block: "center" });
  }, [selectedSegmentId, activeSegmentIds, transcript.data]);

  const count = transcript.data?.length ?? 0;

  return (
    <div className="flex min-h-0 flex-col">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Transcript
        </div>
        <span className="text-[10px] text-[var(--muted)]">{count} segments</span>
      </div>
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto pr-1">
        {transcript.data?.map((seg) => {
          const links = evidenceBySegment.get(seg.id) ?? [];
          const selected = selectedSegmentId === seg.id || activeSegmentIds.has(seg.id);
          return (
            <div
              key={seg.id}
              data-segment-id={seg.id}
              className={`mb-2 grid grid-cols-[28px_1fr] gap-[9px] rounded-[10px] border p-2 transition-colors ${
                selected
                  ? "border-[var(--yellow)] bg-[rgba(255,211,111,0.06)]"
                  : "border-transparent"
              }`}
            >
              <div
                className={`grid h-[28px] w-[28px] place-items-center rounded-full text-[10px] font-extrabold ${
                  seg.speaker === "customer" ? "bg-[#24433a] text-[#c6f4df]" : "bg-[#263a5c]"
                }`}
              >
                {initials(seg.speaker_name ?? seg.speaker)}
              </div>
              <div>
                <div className="mb-[3px] flex items-center gap-2">
                  <span className="text-[11px] font-semibold capitalize">
                    {seg.speaker_name ?? seg.speaker}
                  </span>
                  <span className="text-[9px] text-[var(--muted)]">{seg.id}</span>
                </div>
                <EvidenceText
                  text={seg.text}
                  links={links}
                  onSelect={selectArtifact}
                  activeArtifactId={selectedArtifactId}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
