"use client";

import { useEffect, useState } from "react";
import { CoverageMatrix } from "./CoverageMatrix";
import { FlowTranscript } from "./FlowTranscript";
import { GitBranchView } from "./GitBranchView";
import { QAFlowView } from "./QAFlowView";

type Tab = "qa" | "git" | "matrix";

const TABS: { id: Tab; label: string; note: string }[] = [
  {
    id: "qa",
    label: "Q&A flow",
    note: "Every question the facilitator asks and the customer's answer, read top-to-bottom. Follow-up threads branch to the right off the answer that triggered them. Click any question or requirement to highlight its supporting evidence in the transcript on the left.",
  },
  {
    id: "git",
    label: "Git branch tree",
    note: "The main line is the planned script. Customer answers branch into targeted follow-ups, then merge back as validated findings or requirements.",
  },
  {
    id: "matrix",
    label: "Coverage matrix",
    note: "Which branches contribute evidence to each script stage, where the conversation is strong, and where more questions are still needed.",
  },
];

const TAB_STORAGE_KEY = "speclive.conversation-structure.tab";
const isTab = (value: string | null): value is Tab =>
  value != null && TABS.some((t) => t.id === value);

export function ConversationStructure({ sessionId }: { sessionId: string }) {
  const [active, setActive] = useState<Tab>("qa");
  const note = TABS.find((t) => t.id === active)?.note;

  // Restore the last-viewed tab after mount (kept out of the initial render so
  // the server and first client render agree).
  useEffect(() => {
    const stored = window.localStorage.getItem(TAB_STORAGE_KEY);
    if (isTab(stored)) setActive(stored);
  }, []);

  const selectTab = (tab: Tab) => {
    setActive(tab);
    window.localStorage.setItem(TAB_STORAGE_KEY, tab);
  };

  return (
    <section className="panel mx-[14px] mb-4">
      <header className="panel-header">
        <div>
          <div className="panel-title">Conversation structure</div>
          <div className="panel-subtitle">
            The discovery script stays the anchor while every answer, follow-up, and derived
            requirement remains visible
          </div>
        </div>
        <div className="flex flex-wrap gap-[7px]">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`rounded-[9px] border px-[10px] py-[7px] text-[11px] font-semibold ${
                active === tab.id
                  ? "border-[var(--blue)] bg-[rgba(103,168,255,0.12)] text-white"
                  : "border-[var(--border)] bg-[var(--panel2)] text-[var(--muted)]"
              }`}
              onClick={() => selectTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>
      <div className="min-h-[420px] overflow-auto bg-[linear-gradient(180deg,rgba(9,19,33,0.65),rgba(14,23,39,0.88))] p-3">
        <p className="mb-[11px] text-[11px] leading-snug text-[var(--muted)]">{note}</p>
        {active === "qa" && (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="h-[520px] rounded-[11px] border border-[var(--border)] bg-[var(--panel2)] p-3">
              <FlowTranscript sessionId={sessionId} />
            </div>
            <div className="h-[520px] overflow-auto rounded-[11px] border border-[var(--border)] bg-[var(--panel2)] p-2">
              <QAFlowView sessionId={sessionId} />
            </div>
          </div>
        )}
        {active === "git" && <GitBranchView sessionId={sessionId} />}
        {active === "matrix" && <CoverageMatrix sessionId={sessionId} />}
      </div>
    </section>
  );
}
