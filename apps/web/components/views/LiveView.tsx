"use client";

import { SessionMetrics } from "@/components/session/SessionMetrics";
import { TranscriptPanel } from "@/components/transcript/TranscriptPanel";
import { DiscoveryTree } from "@/components/tree/DiscoveryTree";
import { ArtifactDetail } from "@/components/tree/ArtifactDetail";
import { GuidedScriptPanel } from "@/components/script/GuidedScriptPanel";
import { RecommendedQuestions } from "@/components/questions/RecommendedQuestions";

/**
 * The single-conversation working surface (formerly the whole page): live
 * transcript, discovery tree + provenance, and the guided script + questions.
 */
export function LiveView({ sessionId }: { sessionId: string }) {
  return (
    <div>
      <SessionMetrics sessionId={sessionId} />

      <div className="grid grid-cols-1 gap-3 pt-3 xl:grid-cols-[1.05fr_1.15fr_1.05fr]">
        <div className="flex min-h-0 flex-col gap-3">
          <div className="h-[calc(100vh-220px)] min-h-[520px]">
            <TranscriptPanel sessionId={sessionId} />
          </div>
        </div>

        <div className="flex min-h-0 flex-col gap-3">
          <DiscoveryTree sessionId={sessionId} />
          <ArtifactDetail sessionId={sessionId} />
        </div>

        <div className="flex min-h-0 flex-col gap-3">
          <GuidedScriptPanel sessionId={sessionId} />
          <RecommendedQuestions sessionId={sessionId} />
        </div>
      </div>
    </div>
  );
}
