"use client";

import { useMemo } from "react";
import type { DiscoveryArtifact, EvidenceLink } from "@rdc/domain";
import { useArtifacts, useSessionEvidence, useTranscript } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { EvidenceText } from "./EvidenceText";
import { StatementComposer } from "./StatementComposer";
import { LiveTranscriptionControls } from "./LiveTranscriptionControls";
import { SpeakerLabelEditor } from "./SpeakerLabelEditor";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "?";
}

export function TranscriptPanel({ sessionId }: { sessionId: string }) {
  const transcript = useTranscript(sessionId);
  const evidence = useSessionEvidence(sessionId);
  const artifacts = useArtifacts(sessionId);
  const selectArtifact = useWorkspaceStore((s) => s.selectArtifact);
  const selectedSegmentId = useWorkspaceStore((s) => s.selectedSegmentId);

  const evidenceBySegment = useMemo(() => {
    const map = new Map<string, EvidenceLink[]>();
    (evidence.data ?? []).forEach((link) => {
      const list = map.get(link.transcript_segment_id) ?? [];
      list.push(link);
      map.set(link.transcript_segment_id, list);
    });
    return map;
  }, [evidence.data]);

  const artifactById = useMemo(() => {
    const map = new Map<string, DiscoveryArtifact>();
    (artifacts.data ?? []).forEach((a) => map.set(a.id, a));
    return map;
  }, [artifacts.data]);

  return (
    <section className="panel flex h-full flex-col">
      <header className="panel-header">
        <div>
          <div className="panel-title">Live transcript</div>
          <div className="panel-subtitle">Click evidence or badges to reveal derivation</div>
        </div>
        <span className="status">
          <span className="dot" /> {transcript.data?.length ?? 0} segments
        </span>
      </header>

      <LiveTranscriptionControls sessionId={sessionId} />

      <div className="flex-1 overflow-auto p-3">
        {transcript.data?.map((seg) => {
          const links = evidenceBySegment.get(seg.id) ?? [];
          const badgeArtifactIds = Array.from(new Set(links.map((l) => l.artifact_id)));
          const selected = selectedSegmentId === seg.id;
          return (
            <div
              key={seg.id}
              id={seg.id}
              data-segment-id={seg.id}
              className={`mb-4 grid grid-cols-[34px_1fr] gap-[10px] rounded-[11px] border p-2 ${
                selected ? "border-[var(--blue)] bg-[rgba(103,168,255,0.08)]" : "border-transparent"
              }`}
            >
              <div
                className={`grid h-[34px] w-[34px] place-items-center rounded-full text-[11px] font-extrabold ${
                  seg.speaker === "customer" ? "bg-[#24433a] text-[#c6f4df]" : "bg-[#263a5c]"
                }`}
              >
                {initials(seg.speaker_name ?? seg.speaker)}
              </div>
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <SpeakerLabelEditor sessionId={sessionId} segment={seg} />
                  <span className="text-[10px] text-[var(--muted)]">{seg.id}</span>
                </div>
                <EvidenceText text={seg.text} links={links} onSelect={selectArtifact} />
                {badgeArtifactIds.length > 0 ? (
                  <div className="mt-[7px] flex flex-wrap gap-[6px]">
                    {badgeArtifactIds.map((id) => {
                      const artifact = artifactById.get(id);
                      return (
                        <button key={id} className="badge" onClick={() => selectArtifact(id)}>
                          {artifact ? artifact.id : id}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      <StatementComposer sessionId={sessionId} />
    </section>
  );
}
