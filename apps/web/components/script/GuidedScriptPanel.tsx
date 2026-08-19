"use client";

import {
  useAdvanceScript,
  useConversationGraph,
  useScripts,
  useScriptState,
  useSetSessionScript,
} from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";
import { useToast } from "@/lib/toast";
import { Panel } from "@/components/ui/Panel";

export function GuidedScriptPanel({ sessionId }: { sessionId: string }) {
  const script = useScriptState(sessionId);
  const graph = useConversationGraph(sessionId);
  const advance = useAdvanceScript(sessionId);
  const scripts = useScripts();
  const setScript = useSetSessionScript(sessionId);
  const loadPrompt = useWorkspaceStore((s) => s.loadPrompt);
  const activeBranchId = useWorkspaceStore((s) => s.activeBranchId);
  const setActiveBranch = useWorkspaceStore((s) => s.setActiveBranch);
  const toast = useToast((s) => s.show);

  const state = script.data;
  const stage = state?.current_stage ?? null;
  const total = state?.total_stages ?? 0;
  const currentIndex = state?.current_index ?? 0;
  const activeScriptId = state?.script.id ?? "";
  const options = scripts.data ?? [];

  // Side branches (exclude the main script branch).
  const branches = (graph.data?.branches ?? []).filter((b) => b.topic !== "main_script");

  return (
    <Panel
      title="Guided discovery script"
      subtitle="Current step, next prompt, and answer-driven branches"
      aside={
        <span className="status">
          Step {currentIndex + 1} of {total}
        </span>
      }
    >
      <div className="mb-3">
        <label
          className="text-[10px] uppercase tracking-wide text-[var(--muted)]"
          htmlFor="script-picker"
        >
          Discovery script
        </label>
        <select
          id="script-picker"
          className="mt-1 w-full rounded-[9px] border border-[var(--border)] bg-[var(--panel2)] px-[9px] py-[7px] text-xs text-white disabled:opacity-60"
          value={activeScriptId}
          disabled={setScript.isPending || options.length === 0}
          onChange={(event) => {
            const nextId = event.target.value;
            if (!nextId || nextId === activeScriptId) return;
            setScript.mutate(nextId, {
              onSuccess: (session) => {
                const picked = options.find((s) => s.id === nextId);
                toast(`Script switched to ${picked?.name ?? "selected script"}`);
                void session;
              },
              onError: () => toast("Could not switch the discovery script"),
            });
          }}
        >
          {options.length === 0 && activeScriptId && (
            <option value={activeScriptId}>{state?.script.name}</option>
          )}
          {options.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {state?.script.description && (
          <p className="mt-1 text-[10px] leading-snug text-[var(--muted)]">
            {state.script.description}
          </p>
        )}
      </div>

      <div className="mb-3 flex items-center gap-[6px]">
        {Array.from({ length: total }).map((_, i) => (
          <i
            key={i}
            className={`h-[6px] flex-1 rounded-full ${
              i < currentIndex
                ? "bg-[var(--green)]"
                : i === currentIndex
                  ? "bg-[var(--yellow)] shadow-[0_0_0_3px_rgba(255,211,111,0.12)]"
                  : "bg-[#263752]"
            }`}
          />
        ))}
      </div>

      {stage && (
        <>
          <div className="text-[10px] font-extrabold uppercase tracking-wide text-[var(--yellow)]">
            {stage.title}
          </div>
          <div className="mt-1 text-sm font-extrabold">{stage.objective}</div>
          <div className="mt-2 rounded-[11px] border border-[rgba(255,211,111,0.35)] bg-[rgba(255,211,111,0.08)] p-[10px]">
            <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Say next</div>
            <div className="mt-1 text-xs text-white">{stage.primary_prompt}</div>
            <div className="mt-[9px] flex flex-wrap gap-[7px]">
              <button
                className="btn primary"
                onClick={() => {
                  loadPrompt(stage.primary_prompt);
                  toast("Prompt loaded into the composer");
                }}
              >
                Use this prompt
              </button>
              <button
                className="btn"
                onClick={() =>
                  advance.mutate(undefined, { onSuccess: () => toast("Discovery script advanced") })
                }
              >
                Mark answered
              </button>
            </div>
          </div>
        </>
      )}

      <div className="mt-3 grid gap-[7px]">
        <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
          Conversation branches
        </div>
        {branches.map((branch) => (
          <button
            key={branch.id}
            className={`grid grid-cols-[1fr_auto] items-center gap-[7px] rounded-[9px] border bg-[var(--panel2)] p-2 text-left ${
              activeBranchId === branch.id ? "border-[var(--yellow)]" : "border-[var(--border)]"
            }`}
            onClick={() => {
              setActiveBranch(branch.id);
              toast(`Branch selected: ${branch.name}`);
            }}
          >
            <span>
              <div className="text-[11px] font-semibold">{branch.name}</div>
              <div className="mt-[2px] text-[9px] text-[var(--muted)]">
                {(branch.nodes ?? []).length} nodes · triggered from{" "}
                {branch.created_from_segment_id ?? "—"}
              </div>
            </span>
            <span className="rounded-full border border-[var(--border)] px-[6px] py-[3px] text-[9px] capitalize text-[var(--muted)]">
              {branch.status}
            </span>
          </button>
        ))}
      </div>
    </Panel>
  );
}
