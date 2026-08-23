"use client";

import { useAddSegment, useAnalysisSettings } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { useToast } from "@/lib/toast";

export function StatementComposer({ sessionId }: { sessionId: string }) {
  const composerText = useWorkspaceStore((s) => s.composerText);
  const setComposerText = useWorkspaceStore((s) => s.setComposerText);
  const addSegment = useAddSegment(sessionId);
  const settings = useAnalysisSettings();
  const toast = useToast((s) => s.show);

  async function submit() {
    const text = composerText.trim();
    if (!text) return;
    // The server drafts candidate artifacts automatically once the segment is
    // finalized, but only when auto_analyze is enabled — so only promise
    // drafting when it actually happens.
    await addSegment.mutateAsync({ speaker: "customer", text });
    setComposerText("");
    toast(
      settings.data?.auto_analyze
        ? "Statement added — drafting discovery nodes…"
        : "Statement added",
    );
  }

  return (
    <div className="grid grid-cols-[1fr_auto] gap-2 border-t border-[var(--border)] bg-[var(--panel2)] p-[10px]">
      <textarea
        aria-label="Simulate a new customer statement"
        className="min-h-[64px] resize-none rounded-[10px] border border-[var(--border)] bg-[#091321] p-[10px] text-[var(--text)] outline-none focus:border-[var(--blue)]"
        placeholder="Simulate a new customer statement…"
        value={composerText}
        onChange={(e) => setComposerText(e.target.value)}
      />
      <button
        className="btn primary self-end"
        onClick={submit}
        disabled={addSegment.isPending}
      >
        Add statement
      </button>
    </div>
  );
}
