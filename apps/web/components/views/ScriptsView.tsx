"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Search, ChevronRight, X, ScrollText } from "lucide-react";
import type { ScriptDefinition, ScriptStage } from "@rdc/domain";
import type { ScriptDefinitionWrite, ScriptStageWrite } from "@rdc/client";
import {
  useArchiveScript,
  useCreateScript,
  useScripts,
  useSessions,
  useUpdateScript,
} from "@/lib/hooks";
import { useToast } from "@/lib/toast";

interface ScriptDraft {
  id: string | null;
  name: string;
  version: string;
  description: string;
  stages: ScriptStageWrite[];
}

const EMPTY_SCRIPTS: ScriptDefinition[] = [];

function stageToDraft(stage: ScriptStage): ScriptStageWrite {
  return {
    id: stage.id,
    title: stage.title,
    objective: stage.objective,
    primary_prompt: stage.primary_prompt,
    alternative_prompts: [...stage.alternative_prompts],
    completion_criteria: [...stage.completion_criteria],
  };
}

function scriptToDraft(script: ScriptDefinition): ScriptDraft {
  return {
    id: script.id,
    name: script.name,
    version: script.version,
    description: script.description,
    stages: script.stages.map(stageToDraft),
  };
}

function emptyDraft(): ScriptDraft {
  return {
    id: null,
    name: "Untitled discovery script",
    version: "1.0.0",
    description: "",
    stages: [
      {
        title: "Opening",
        objective: "",
        primary_prompt: "What would you like to understand or improve?",
        alternative_prompts: [],
        completion_criteria: [],
      },
    ],
  };
}

function asWriteBody(draft: ScriptDraft): ScriptDefinitionWrite {
  return {
    name: draft.name.trim(),
    version: draft.version.trim() || "1.0.0",
    description: draft.description.trim(),
    stages: draft.stages.map((stage) => ({
      ...stage,
      title: stage.title.trim(),
      objective: stage.objective.trim(),
      primary_prompt: stage.primary_prompt.trim(),
      alternative_prompts: stage.alternative_prompts.filter(Boolean),
      completion_criteria: stage.completion_criteria.filter(Boolean),
    })),
  };
}

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function ScriptsView() {
  const scriptsQuery = useScripts();
  const sessionsQuery = useSessions();
  const createScript = useCreateScript();
  const updateScript = useUpdateScript();
  const archiveScript = useArchiveScript();
  const toast = useToast((state) => state.show);
  const importRef = useRef<HTMLInputElement>(null);

  const scripts = scriptsQuery.data ?? EMPTY_SCRIPTS;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ScriptDraft | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [filter, setFilter] = useState("");
  const [previewing, setPreviewing] = useState(false);

  const usedScriptIds = useMemo(
    () =>
      new Set(
        (sessionsQuery.data ?? []).flatMap((session) =>
          session.script_id ? [session.script_id] : [],
        ),
      ),
    [sessionsQuery.data],
  );

  const visibleScripts = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return scripts;
    return scripts.filter((script) =>
      `${script.name} ${script.version} ${script.description}`.toLowerCase().includes(needle),
    );
  }, [filter, scripts]);

  const dirty = draft !== null && JSON.stringify(draft) !== savedSnapshot;
  const pending = createScript.isPending || updateScript.isPending || archiveScript.isPending;
  const selectedInUse = Boolean(draft?.id && usedScriptIds.has(draft.id));

  function loadDraft(next: ScriptDraft) {
    setDraft(next);
    setSavedSnapshot(JSON.stringify(next));
    setPreviewing(false);
  }

  useEffect(() => {
    if (draft?.id === null) return;
    const selected = scripts.find((script) => script.id === selectedId) ?? scripts[0];
    if (!selected) {
      setSelectedId(null);
      setDraft(null);
      setSavedSnapshot("");
      return;
    }
    if (selected.id !== selectedId) setSelectedId(selected.id);
    if (
      draft?.id !== selected.id ||
      (!dirty && JSON.stringify(scriptToDraft(selected)) !== savedSnapshot)
    ) {
      loadDraft(scriptToDraft(selected));
    }
  }, [dirty, draft?.id, savedSnapshot, scripts, selectedId]);

  function confirmDiscard(): boolean {
    return !dirty || window.confirm("Discard the unsaved changes to this script?");
  }

  function selectScript(script: ScriptDefinition) {
    if (!confirmDiscard()) return;
    setSelectedId(script.id);
    loadDraft(scriptToDraft(script));
  }

  function startNewScript() {
    if (!confirmDiscard()) return;
    setSelectedId(null);
    const next = emptyDraft();
    setDraft(next);
    setSavedSnapshot("");
    setPreviewing(false);
  }

  function updateDraft(changes: Partial<ScriptDraft>) {
    setDraft((current) => (current ? { ...current, ...changes } : current));
  }

  function updateStage(index: number, changes: Partial<ScriptStageWrite>) {
    setDraft((current) => {
      if (!current) return current;
      return {
        ...current,
        stages: current.stages.map((stage, stageIndex) =>
          stageIndex === index ? { ...stage, ...changes } : stage,
        ),
      };
    });
  }

  function addStage() {
    setDraft((current) =>
      current
        ? {
            ...current,
            stages: [
              ...current.stages,
              {
                title: "New stage",
                objective: "",
                primary_prompt: "Add the anchor question for this stage…",
                alternative_prompts: [],
                completion_criteria: [],
              },
            ],
          }
        : current,
    );
  }

  function removeStage(index: number) {
    setDraft((current) =>
      current && current.stages.length > 1
        ? { ...current, stages: current.stages.filter((_, stageIndex) => stageIndex !== index) }
        : current,
    );
  }

  function save() {
    if (!draft) return;
    const body = asWriteBody(draft);
    if (!body.name || body.stages.some((stage) => !stage.title || !stage.primary_prompt)) {
      toast("Add a script name, stage title, and primary prompt before saving");
      return;
    }
    const onSuccess = (script: ScriptDefinition) => {
      setSelectedId(script.id);
      loadDraft(scriptToDraft(script));
      toast(draft.id ? "Script changes saved" : "Discovery script created");
    };
    const onError = (error: Error) => toast(error.message || "Could not save the script");
    if (draft.id) updateScript.mutate({ scriptId: draft.id, body }, { onSuccess, onError });
    else createScript.mutate(body, { onSuccess, onError });
  }

  function duplicate() {
    if (!draft || !confirmDiscard()) return;
    const next: ScriptDraft = {
      ...draft,
      id: null,
      name: `${draft.name} copy`,
      stages: draft.stages.map(({ id: _id, ...stage }) => stage),
    };
    setSelectedId(null);
    setDraft(next);
    setSavedSnapshot("");
    setPreviewing(false);
  }

  function discard() {
    if (draft?.id) {
      const current = scripts.find((script) => script.id === draft.id);
      if (current) loadDraft(scriptToDraft(current));
      return;
    }
    const first = scripts[0];
    if (first) {
      setSelectedId(first.id);
      loadDraft(scriptToDraft(first));
    } else {
      setSelectedId(null);
      setDraft(null);
      setSavedSnapshot("");
    }
  }

  function archive() {
    if (!draft?.id || selectedInUse) return;
    if (
      !window.confirm(
        `Archive “${draft.name}”? It will no longer be available for new conversations.`,
      )
    ) {
      return;
    }
    archiveScript.mutate(draft.id, {
      onSuccess: () => {
        setDraft(null);
        setSelectedId(null);
        setSavedSnapshot("");
        toast("Discovery script archived");
      },
      onError: (error) => toast(error.message || "Could not archive the script"),
    });
  }

  async function importScript(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !confirmDiscard()) return;
    try {
      const raw = JSON.parse(await file.text()) as Partial<ScriptDefinition>;
      if (!raw.name || !Array.isArray(raw.stages) || raw.stages.length === 0) {
        throw new Error("The file does not contain a discovery script");
      }
      const next: ScriptDraft = {
        id: null,
        name: raw.name,
        version: raw.version ?? "1.0.0",
        description: raw.description ?? "",
        stages: raw.stages.map((stage) => ({
          title: stage.title,
          objective: stage.objective ?? "",
          primary_prompt: stage.primary_prompt,
          alternative_prompts: stage.alternative_prompts ?? [],
          completion_criteria: stage.completion_criteria ?? [],
        })),
      };
      setSelectedId(null);
      setDraft(next);
      setSavedSnapshot("");
      setPreviewing(false);
      toast("Script imported as a new draft");
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not import that script");
    }
  }

  return (
    <section className="scripts-page">
      <input
        ref={importRef}
        className="sr-only"
        type="file"
        accept="application/json,.json"
        aria-label="Import discovery script"
        onChange={importScript}
      />

      <div className="scripts-heading">
        <div>
          <h1>Discovery scripts</h1>
          <p>
            Reusable question sequences that anchor a conversation while follow-up branches adapt to
            what the customer says.
          </p>
        </div>
        <div className="scripts-heading-actions">
          <button className="btn" onClick={() => importRef.current?.click()}>
            Import JSON
          </button>
          <button className="btn primary" onClick={startNewScript}>
            + New script
          </button>
        </div>
      </div>

      <div className="scripts-manager">
        <aside className="script-list-panel" aria-label="Available discovery scripts">
          <div className="script-panel-header">
            <strong>Available scripts</strong>
            <span>{scripts.length} active</span>
          </div>
          <div className="script-filter">
            <span aria-hidden="true">
              <Search size={13} strokeWidth={2} />
            </span>
            <input
              type="search"
              aria-label="Filter discovery scripts"
              placeholder="Filter scripts…"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
          </div>

          <div className="script-list">
            {visibleScripts.map((script) => (
              <button
                key={script.id}
                className={`script-list-item${selectedId === script.id ? " active" : ""}`}
                onClick={() => selectScript(script)}
              >
                <span className="script-list-title">
                  <i />
                  <strong>{script.name}</strong>
                  <span aria-hidden="true">
                    <ChevronRight size={15} strokeWidth={2} />
                  </span>
                </span>
                <span className="script-list-description">{script.description}</span>
                <span className="script-list-meta">
                  {script.stages.length} stages · v{script.version}
                  {usedScriptIds.has(script.id) ? " · In use" : ""}
                </span>
              </button>
            ))}
            {!scriptsQuery.isLoading && visibleScripts.length === 0 && (
              <div className="script-list-empty">
                {filter ? "No scripts match this filter." : "No active scripts yet."}
              </div>
            )}
            {scriptsQuery.isLoading && scripts.length === 0 && (
              <div className="script-list-empty">Loading scripts…</div>
            )}
            {scriptsQuery.isError && (
              <div className="script-list-empty error">Could not load the script catalogue.</div>
            )}
          </div>
        </aside>

        <div className="script-editor-panel">
          {draft ? (
            <>
              <div className="script-panel-header editor">
                <div>
                  <strong>{draft.id ? "Edit script" : "New script draft"}</strong>
                  <span>{dirty ? "Unsaved changes" : "Saved"}</span>
                </div>
                <button className="btn preview" onClick={() => setPreviewing((value) => !value)}>
                  {previewing ? "Edit stages" : "Preview flow"}
                </button>
              </div>

              <div className="script-editor-body">
                <div className="script-form-row">
                  <label className="script-field grow">
                    <span>Script name</span>
                    <input
                      value={draft.name}
                      onChange={(event) => updateDraft({ name: event.target.value })}
                    />
                  </label>
                  <label className="script-field version">
                    <span>Version</span>
                    <input
                      value={draft.version}
                      onChange={(event) => updateDraft({ version: event.target.value })}
                    />
                  </label>
                </div>
                <label className="script-field">
                  <span>Description</span>
                  <textarea
                    value={draft.description}
                    onChange={(event) => updateDraft({ description: event.target.value })}
                  />
                </label>

                <div className="script-stages-heading">
                  <strong>Conversation stages</strong>
                  <span>{draft.stages.length} stages</span>
                </div>

                {previewing ? (
                  <ol className="script-flow-preview">
                    {draft.stages.map((stage, index) => (
                      <li key={stage.id ?? `preview-${index}`}>
                        <span className="script-flow-number">{index + 1}</span>
                        <div>
                          <strong>{stage.title || "Untitled stage"}</strong>
                          <p>{stage.primary_prompt || "No primary prompt yet."}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="script-stage-list">
                    {draft.stages.map((stage, index) => (
                      <div className="script-stage" key={stage.id ?? `stage-${index}`}>
                        <span className="script-stage-number">{index + 1}</span>
                        <div className="script-stage-fields">
                          <input
                            aria-label={`Stage ${index + 1} title`}
                            value={stage.title}
                            onChange={(event) => updateStage(index, { title: event.target.value })}
                          />
                          <input
                            aria-label={`Stage ${index + 1} primary prompt`}
                            value={stage.primary_prompt}
                            onChange={(event) =>
                              updateStage(index, { primary_prompt: event.target.value })
                            }
                          />
                          <details>
                            <summary>Advanced stage details</summary>
                            <label className="script-field">
                              <span>Objective</span>
                              <textarea
                                value={stage.objective}
                                onChange={(event) =>
                                  updateStage(index, { objective: event.target.value })
                                }
                              />
                            </label>
                            <div className="script-advanced-grid">
                              <label className="script-field">
                                <span>Alternative prompts · one per line</span>
                                <textarea
                                  value={stage.alternative_prompts.join("\n")}
                                  onChange={(event) =>
                                    updateStage(index, {
                                      alternative_prompts: splitLines(event.target.value),
                                    })
                                  }
                                />
                              </label>
                              <label className="script-field">
                                <span>Completion criteria · one per line</span>
                                <textarea
                                  value={stage.completion_criteria.join("\n")}
                                  onChange={(event) =>
                                    updateStage(index, {
                                      completion_criteria: splitLines(event.target.value),
                                    })
                                  }
                                />
                              </label>
                            </div>
                          </details>
                        </div>
                        <button
                          className="script-remove-stage"
                          aria-label={`Remove stage ${index + 1}`}
                          disabled={draft.stages.length === 1}
                          onClick={() => removeStage(index)}
                        >
                          <X size={15} strokeWidth={2.25} />
                        </button>
                      </div>
                    ))}
                    <button className="script-add-stage" onClick={addStage}>
                      + Add stage
                    </button>
                  </div>
                )}
              </div>

              <div className="script-editor-footer">
                <div>
                  <button className="btn" onClick={duplicate}>
                    Duplicate
                  </button>
                  <button
                    className="btn danger"
                    disabled={!draft.id || selectedInUse || pending}
                    title={
                      selectedInUse
                        ? "This script is attached to an existing conversation"
                        : undefined
                    }
                    onClick={archive}
                  >
                    Archive
                  </button>
                </div>
                <div>
                  <button className="btn" disabled={!dirty || pending} onClick={discard}>
                    Discard
                  </button>
                  <button className="btn primary" disabled={!dirty || pending} onClick={save}>
                    {pending ? "Saving…" : "Save changes"}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="script-editor-empty">
              <span>
                <ScrollText size={22} strokeWidth={2} />
              </span>
              <h2>Select a discovery script</h2>
              <p>Review its stages, edit the anchor prompts, or create a reusable script.</p>
              <button className="btn primary" onClick={startNewScript}>
                New script
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
