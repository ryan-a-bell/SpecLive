"use client";

import { useState } from "react";
import { CoverageMatrix } from "./CoverageMatrix";
import { GitBranchView } from "./GitBranchView";
import { SubwayView } from "./SubwayView";

type Tab = "git" | "subway" | "matrix";

const TABS: { id: Tab; label: string; note: string }[] = [
  {
    id: "git",
    label: "Git branch tree",
    note: "The main line is the planned script. Customer answers branch into targeted follow-ups, then merge back as validated findings or requirements.",
  },
  {
    id: "subway",
    label: "Conversation subway",
    note: "Each line is a topic thread. Transfer stations show where a branch reconnects to the script or shares evidence with another branch.",
  },
  {
    id: "matrix",
    label: "Coverage matrix",
    note: "Which branches contribute evidence to each script stage, where the conversation is strong, and where more questions are still needed.",
  },
];

export function ConversationStructure({ sessionId }: { sessionId: string }) {
  const [active, setActive] = useState<Tab>("git");
  const note = TABS.find((t) => t.id === active)?.note;

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
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>
      <div className="min-h-[420px] overflow-auto bg-[linear-gradient(180deg,rgba(9,19,33,0.65),rgba(14,23,39,0.88))] p-3">
        <p className="mb-[11px] text-[11px] leading-snug text-[var(--muted)]">{note}</p>
        {active === "git" && <GitBranchView sessionId={sessionId} />}
        {active === "subway" && <SubwayView sessionId={sessionId} />}
        {active === "matrix" && <CoverageMatrix sessionId={sessionId} />}
      </div>
    </section>
  );
}
