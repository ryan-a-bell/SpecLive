"use client";

// Preserved pre-workspace layout (tabs-on-top shell). Kept as a fallback while
// the workspace-switcher navigation beds in; reachable at /legacy. Safe to
// delete once the new shell is settled.
import { DEMO_SESSION_ID } from "@/lib/config";
import { TopBar } from "@/components/layout/TopBar";
import { SessionMetrics } from "@/components/session/SessionMetrics";
import { TranscriptPanel } from "@/components/transcript/TranscriptPanel";
import { DiscoveryTree } from "@/components/tree/DiscoveryTree";
import { ArtifactDetail } from "@/components/tree/ArtifactDetail";
import { GuidedScriptPanel } from "@/components/script/GuidedScriptPanel";
import { RecommendedQuestions } from "@/components/questions/RecommendedQuestions";
import { ConversationStructure } from "@/components/viz/ConversationStructure";
import { Toaster } from "@/components/ui/Toaster";

export default function LegacyWorkspacePage() {
  const sessionId = DEMO_SESSION_ID;
  return (
    <main>
      <TopBar sessionId={sessionId} />
      <SessionMetrics sessionId={sessionId} />

      <div className="grid min-h-[calc(100vh-144px)] grid-cols-1 gap-3 p-[14px] xl:grid-cols-[1.05fr_1.15fr_1.05fr]">
        <div className="flex min-h-0 flex-col gap-3">
          <div className="h-[calc(100vh-174px)] min-h-[520px]">
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

      <ConversationStructure sessionId={sessionId} />
      <Toaster />
    </main>
  );
}
