"use client";

import { useRecommendations } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import { Panel } from "@/components/ui/Panel";

export function RecommendedQuestions({ sessionId }: { sessionId: string }) {
  const recommendations = useRecommendations(sessionId);
  const loadPrompt = useWorkspaceStore((s) => s.loadPrompt);
  const toast = useToast((s) => s.show);

  return (
    <Panel title="Recommended next questions" subtitle="Prioritized from discovery-tree gaps">
      {recommendations.data?.questions.map((q) => (
        <button
          key={q.rank}
          className="mb-2 block w-full rounded-[11px] border border-[var(--border)] bg-[var(--panel2)] p-[10px] text-left hover:border-[var(--yellow)]"
          onClick={() => {
            loadPrompt(q.question);
            toast("Question loaded into the composer");
          }}
        >
          <div className="text-[10px] font-extrabold text-[var(--yellow)]">{q.rank}</div>
          <div className="mt-[3px] text-xs leading-snug">{q.question}</div>
          <div className="mt-[5px] text-[10px] text-[var(--muted)]">{q.why}</div>
        </button>
      ))}

      <h3 className="my-2 text-xs font-bold">Active gaps and conflicts</h3>
      {recommendations.data?.gaps.map((gap, i) => (
        <div
          key={i}
          className="mb-2 rounded-[11px] border border-[var(--border)] border-l-[3px] border-l-[var(--red)] bg-[var(--panel2)] p-[10px]"
        >
          <div className="text-xs font-extrabold">{gap.title}</div>
          <div className="mt-1 text-[11px] leading-snug text-[var(--muted)]">{gap.body}</div>
        </div>
      ))}
    </Panel>
  );
}
