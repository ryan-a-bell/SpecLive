"use client";

import { useMemo, useState } from "react";
import type { ArtifactType } from "@rdc/domain";
import { useNavStore } from "@/lib/nav-store";
import { useReviewActions } from "@/lib/hooks";
import { useToast } from "@/lib/toast";
import {
  ARTIFACT_TYPE_LABEL,
  confidenceBand,
  useWorkspaceReview,
  type ReviewItem,
  type Workspace,
} from "@/lib/workspaces";

type FilterId = ArtifactType | "all" | "low_confidence";

// Human-readable derivation method — the signal that tells a reviewer whether a
// model connected cross-turn evidence or a keyword rule matched a single phrase.
const METHOD_LABEL: Record<string, string> = {
  llm: "LLM inference",
  keyword_heuristic: "keyword heuristic",
  manual: "manual entry",
  imported: "imported",
};

function methodLabel(method: string): string {
  return METHOD_LABEL[method] ?? method.replace(/_/g, " ");
}

export function ReviewInbox({ workspace }: { workspace: Workspace }) {
  const selectSession = useNavStore((s) => s.selectSession);
  const setView = useNavStore((s) => s.setView);
  const { items, isLoading } = useWorkspaceReview(workspace.sessions);
  const { confirm, reject } = useReviewActions();
  const toast = useToast((s) => s.show);
  const [filter, setFilter] = useState<FilterId>("all");

  const { counts, lowConfidence } = useMemo(() => {
    const counts: Record<"requirement" | "open_question" | "risk", number> = {
      requirement: 0,
      open_question: 0,
      risk: 0,
    };
    let lowConfidence = 0;
    for (const it of items) {
      const t = it.artifact.artifact_type;
      if (t === "requirement" || t === "open_question" || t === "risk") counts[t]++;
      if (confidenceBand(it.artifact.confidence) === "low") lowConfidence++;
    }
    return { counts, lowConfidence };
  }, [items]);

  const filters: { id: FilterId; label: string; n: number }[] = [
    { id: "all", label: "All", n: items.length },
    { id: "requirement", label: "Requirements", n: counts.requirement },
    { id: "open_question", label: "Open questions", n: counts.open_question },
    { id: "risk", label: "Risks", n: counts.risk },
    { id: "low_confidence", label: "Low confidence", n: lowConfidence },
  ];

  const visible = items.filter((it) => {
    if (filter === "all") return true;
    if (filter === "low_confidence") return confidenceBand(it.artifact.confidence) === "low";
    return it.artifact.artifact_type === filter;
  });

  function openConversation(item: ReviewItem) {
    selectSession(item.sessionId);
    setView("live");
  }

  function onConfirm(item: ReviewItem) {
    confirm.mutate(
      { artifactId: item.artifact.id, sessionId: item.sessionId },
      {
        onSuccess: () => toast(`Confirmed ${item.artifact.title}`),
        onError: () => toast("Could not confirm — is the API running?"),
      },
    );
  }

  function onReject(item: ReviewItem) {
    reject.mutate(
      { artifactId: item.artifact.id, sessionId: item.sessionId },
      {
        onSuccess: () => toast(`Rejected ${item.artifact.title}`),
        onError: () => toast("Could not reject — is the API running?"),
      },
    );
  }

  return (
    <section>
      <div className="ov-head">
        <div>
          <div className="ov-title">Validation inbox</div>
          <div className="ov-subtitle">
            Every model-inferred item across {workspace.name} that hasn&apos;t been human-confirmed.
            Nothing here is baselined into the discovery package until you act on it — review the
            evidence, then confirm or reject. Lowest-confidence items are shown first.
          </div>
        </div>
      </div>

      <div className="summary">
        <div className="metric warn">
          <div className="label">Awaiting review</div>
          <div className="value">{items.length}</div>
        </div>
        <div className="metric crit">
          <div className="label">Low confidence</div>
          <div className="value">{lowConfidence}</div>
        </div>
        <div className="metric info">
          <div className="label">Open questions</div>
          <div className="value">{counts.open_question}</div>
        </div>
        <div className="metric">
          <div className="label">Conversations</div>
          <div className="value">{workspace.sessions.length}</div>
        </div>
      </div>

      <div className="reg-toolbar">
        <div className="reg-chips">
          {filters.map((f) => (
            <button
              key={f.id}
              className={`reg-chip${filter === f.id ? " active" : ""}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
              <span className="n">{f.n}</span>
            </button>
          ))}
        </div>
      </div>

      {isLoading && items.length === 0 && (
        <div className="rc-empty">Loading candidates awaiting validation…</div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="rc-empty rc-empty--clear">
          <div className="rc-empty-mark">✓</div>
          <h3>All caught up</h3>
          <p>Nothing in {workspace.name} is waiting on validation. New candidates land here as your conversations derive them.</p>
        </div>
      )}

      {visible.length > 0 && (
        <div className="inbox">
          {visible.map((item) => {
            const a = item.artifact;
            const band = confidenceBand(a.confidence);
            const evidence = item.evidence;
            const distinctSegments = new Set(
              evidence.map((l) => l.transcript_segment_id),
            ).size;
            const top = evidence.slice(0, 2);
            const busy = confirm.isPending || reject.isPending;
            return (
              <article key={a.id} className="rc">
                <div className="rc-body">
                  <div className="rc-main">
                    <div className="rc-top">
                      <span className={`type-dot ${a.artifact_type}`} />
                      <span className="rc-type">{ARTIFACT_TYPE_LABEL[a.artifact_type]}</span>
                      <span className="rc-id">{a.title}</span>
                      {distinctSegments > 1 && (
                        <span
                          className="xturn-pill"
                          title="Connected from evidence in more than one transcript turn"
                        >
                          cross-turn · {distinctSegments} segments
                        </span>
                      )}
                    </div>
                    <div className="rc-statement">{a.statement}</div>
                    {a.rationale && <div className="rc-rationale">{a.rationale}</div>}

                    <div className="evi">
                      <div className="evi-head">
                        Evidence · <span className="evi-src">{item.sessionTitle}</span>
                      </div>
                      {top.map((link) => (
                        <button
                          key={link.id}
                          className="evi-quote-btn"
                          onClick={() => openConversation(item)}
                          title="Open this conversation"
                        >
                          <span className="evi-rel">{link.relationship}</span>
                          <span className={`evidence ${link.relationship}`}>
                            “{link.quoted_text}”
                          </span>
                        </button>
                      ))}
                      {evidence.length === 0 && (
                        <div className="evi-none">No evidence linked yet.</div>
                      )}
                      {evidence.length > top.length && (
                        <div className="evi-more">
                          +{evidence.length - top.length} more evidence link
                          {evidence.length - top.length === 1 ? "" : "s"}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="rc-side">
                    <div className="conf">
                      <div className="conf-label">
                        Confidence <b>{a.confidence > 0 ? a.confidence.toFixed(2) : "—"}</b>
                      </div>
                      <div className="conf-bar">
                        <div
                          className={`conf-fill ${band}`}
                          style={{ width: `${Math.round(a.confidence * 100)}%` }}
                        />
                      </div>
                      <div className="conf-method">
                        <b>Method:</b> {methodLabel(a.derivation_method)}
                        {distinctSegments > 0 && (
                          <>
                            {" · "}
                            {distinctSegments} source{distinctSegments === 1 ? "" : "s"}
                          </>
                        )}
                      </div>
                    </div>

                    <div className="rc-actions">
                      <button
                        className="act confirm"
                        disabled={busy}
                        onClick={() => onConfirm(item)}
                      >
                        ✓ Confirm
                      </button>
                      <div className="act-row">
                        <button className="act" onClick={() => openConversation(item)}>
                          Open
                        </button>
                        <button
                          className="act reject"
                          disabled={busy}
                          onClick={() => onReject(item)}
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {!isLoading && items.length > 0 && visible.length === 0 && (
        <div className="rc-empty">No items match this filter.</div>
      )}
    </section>
  );
}
