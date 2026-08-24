"use client";

import { useState } from "react";
import { useAnalysisSettings, useStorageSettings, useTranscriptionCapability } from "@/lib/hooks";

type Tab = "storage" | "llm" | "stt" | "analysis" | "privacy";

const TABS: { id: Tab; label: string; future?: boolean }[] = [
  { id: "storage", label: "Storage" },
  { id: "llm", label: "AI routing" },
  { id: "stt", label: "Speech-to-text" },
  { id: "analysis", label: "Analysis" },
  { id: "privacy", label: "Data & privacy", future: true },
];

/** Absolute-ish display of a possibly-relative local root, for the "where it lives" readout. */
function displayRoot(root: string | null | undefined): string {
  const value = (root ?? "./data").trim() || "./data";
  const withSlash = value.replace(/\/?$/, "/");
  return value.startsWith(".") ? `<API working dir>/${withSlash.replace(/^\.\//, "")}` : withSlash;
}

export function SettingsView() {
  const [tab, setTab] = useState<Tab>("storage");
  const storage = useStorageSettings();
  const analysis = useAnalysisSettings();
  const capability = useTranscriptionCapability();

  const backend = storage.data?.backend ?? "local";
  const isLocal = backend === "local";
  const root = storage.data?.local_root ?? "./data";
  const persistAudio = storage.data?.persist_audio ?? true;
  const schemaVersion = storage.data?.schema_version ?? "1";
  const rootLine = isLocal ? root.replace(/\/?$/, "/") : "db://stored_blobs/";
  const livesValue = isLocal ? displayRoot(root) : "database · table “stored_blobs”";

  return (
    <div className="settings-view">
      <div className="set-head">
        <h1>Settings</h1>
        <span className="scope-pill">
          <span className="d" /> Scope: Global (this deployment)
        </span>
      </div>

      <div className="set-banner">
        <span className="ic">ⓘ</span>
        <div>
          These reflect this deployment&apos;s <b>active configuration</b>, set through the environment
          (see <code>.env</code>). Runtime editing and per-workspace overrides are planned —{" "}
          <b>issue #24</b>. Secrets such as API keys are never shown here.
        </div>
      </div>

      <div className="set-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`set-tab${tab === t.id ? " active" : ""}${t.future ? " future" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.future && <span className="soon">SOON</span>}
          </button>
        ))}
      </div>

      {/* ---------------- STORAGE ---------------- */}
      {tab === "storage" && (
        <section className="set-section">
          <div className="sec-intro">
            <h2>Storage</h2>
            <p>
              Where SpecLive keeps each conversation&apos;s <b>recording</b>, <b>transcript</b>, derived{" "}
              <b>requirements</b>, and exported <b>discovery packages</b>. Structured data always lives
              in the database; this governs the content files.
            </p>
          </div>

          <div className="set-card">
            <div className="set-card-h">
              <div className="t">Storage location</div>
              <div className="s">One backend for the whole deployment.</div>
            </div>
            <div className="set-card-b">
              <div className="set-row">
                <div>
                  <div className="k">Backend</div>
                  <div className="h">
                    Local keeps a browsable folder tree you can back up with ordinary tools. Database
                    keeps everything in one store.
                  </div>
                </div>
                <div className="seg readonly">
                  <span className={`seg-opt${isLocal ? " on" : ""}`}>
                    Local directory
                    <span className="badge">DEFAULT</span>
                  </span>
                  <span className={`seg-opt${!isLocal ? " on" : ""}`}>Database</span>
                </div>
              </div>

              {isLocal && (
                <div className="set-row">
                  <div>
                    <div className="k">Local root directory</div>
                    <div className="h">The tree below is written under this path.</div>
                  </div>
                  <code className="val-field">{root}</code>
                </div>
              )}

              <div className="set-row">
                <div>
                  <div className="k">Store the raw recording</div>
                  <div className="h">
                    When off, transcripts and requirements are kept while captured audio is discarded.
                  </div>
                </div>
                <span className={`state-pill${persistAudio ? " on" : " off"}`}>
                  {persistAudio ? "On" : "Off"}
                </span>
              </div>

              <div className="lives">
                <span className="ic">◈</span>
                <div>
                  <div className="lbl">Where your data lives</div>
                  <div className="val">{storage.isLoading ? "…" : livesValue}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="set-card">
            <div className="set-card-h">
              <div className="t">Folder layout</div>
              <div className="s">
                One folder per conversation, keyed on its stable ID. Write-once audio is kept apart from
                regenerated files; a manifest records checksums and which models produced each item.
              </div>
            </div>
            <div className="set-card-b">
              <pre className="tree" aria-label="Storage layout preview">
                <span className="cm">{rootLine}</span>
                {"\n"}├─ <span className="cm">.speclive-storage.json</span>{"          "}
                <span className="cm"># layout v{schemaVersion}</span>
                {"\n"}└─ <span className="dir">workspaces/</span>
                {"\n"}
                {"   "}└─ <span className="accent">acme-corp/</span>
                {"                    "}
                <span className="cm"># workspace (from customer)</span>
                {"\n"}
                {"      "}├─ <span className="cm">workspace.json</span>
                {"\n"}
                {"      "}└─ <span className="dir">conversations/</span>
                {"\n"}
                {"         "}└─ <span className="accent">20260823-kickoff-9f8e7d/</span>
                {"    "}
                <span className="cm"># date · title · session id</span>
                {"\n"}
                {"            "}├─ <span className="cm">manifest.json</span>
                {"            "}
                <span className="cm"># index · checksums · provenance</span>
                {persistAudio ? (
                  <>
                    {"\n"}
                    {"            "}├─ <span className="raw">raw/</span>
                    {"                     "}
                    <span className="cm"># write-once</span>
                    {"\n"}
                    {"            "}│{"  "}├─ <span className="raw">recording.mp3</span>
                    {"\n"}
                    {"            "}│{"  "}└─ <span className="raw">recording.meta.json</span>
                  </>
                ) : (
                  <>
                    {"\n"}
                    {"            "}
                    <span className="cm faded">(raw/ omitted — audio not stored)</span>
                  </>
                )}
                {"\n"}
                {"            "}├─ <span className="tx">transcript/</span>
                {"\n"}
                {"            "}│{"  "}├─ <span className="tx">segments.json</span>
                {"\n"}
                {"            "}│{"  "}└─ <span className="tx">transcript.md</span>
                {"\n"}
                {"            "}├─ <span className="rq">requirements/</span>
                {"\n"}
                {"            "}│{"  "}├─ <span className="rq">artifacts.json</span>
                {"\n"}
                {"            "}│{"  "}└─ <span className="rq">evidence.json</span>
                {"\n"}
                {"            "}└─ <span className="ex">exports/</span>
                {"\n"}
                {"               "}├─ <span className="ex">discovery-package-…​.json</span>
                {"\n"}
                {"               "}└─ <span className="ex">discovery-package-…​.md</span>
              </pre>
              <div className="note info">
                <b>Recordings, transcripts and requirements</b> each get their own folder, so a
                retention rule can target one kind — e.g. drop <code>raw/</code> after 30 days while
                keeping requirements.
              </div>
            </div>
          </div>

          <div className="set-card">
            <div className="set-card-h">
              <div className="t">Applies to</div>
              <div className="s">This increment ships one setting for the whole deployment.</div>
              <span className="soon big">PER-WORKSPACE · PLANNED</span>
            </div>
            <div className="set-card-b">
              <div className="note warn">
                Per-workspace and per-conversation overrides — so one customer&apos;s calls can go
                somewhere different — are tracked in <b>issue #24</b>. Secrets like API keys always stay
                in the deployment environment, never in a saved setting.
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ---------------- AI ROUTING ---------------- */}
      {tab === "llm" && (
        <section className="set-section">
          <div className="sec-intro">
            <h2>AI routing</h2>
            <p>
              Which language model derives candidate requirements. The default runs a deterministic
              mock, so SpecLive works with no keys.
            </p>
          </div>
          <div className="set-card">
            <div className="set-card-h">
              <div className="t">Language model</div>
              <div className="s">Any OpenAI-compatible endpoint — OpenAI, local Ollama/vLLM, or Anthropic&apos;s compatible API.</div>
            </div>
            <div className="set-card-b">
              <ReadRow k="Provider" value={analysis.data?.llm_provider ?? "…"} />
              <ReadRow k="Base URL" value={analysis.data?.llm_api_base ?? "— (mock)"} mono />
              <ReadRow k="Model" value={analysis.data?.llm_model ?? "— (mock)"} mono />
              <div className="set-row">
                <div>
                  <div className="k">API key</div>
                  <div className="h">
                    Read from the environment (<code>LLM_API_KEY</code>). Never shown or stored here.
                  </div>
                </div>
                <span className="state-pill neutral">managed in environment</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ---------------- STT ---------------- */}
      {tab === "stt" && (
        <section className="set-section">
          <div className="sec-intro">
            <h2>Speech-to-text</h2>
            <p>
              How live microphone audio and uploaded recordings become transcript segments. Browser
              audio only ever goes to the SpecLive API.
            </p>
          </div>
          <div className="set-card">
            <div className="set-card-h">
              <div className="t">Transcription</div>
              <div className="s">Provider is selected server-side; mock and local Whisper need no keys.</div>
            </div>
            <div className="set-card-b">
              <div className="set-row">
                <div>
                  <div className="k">Transcription available</div>
                  <div className="h">Whether the configured provider is ready to accept audio.</div>
                </div>
                <span className={`state-pill${capability.data?.available ? " on" : " off"}`}>
                  {capability.isLoading ? "…" : capability.data?.available ? "Ready" : "Unavailable"}
                </span>
              </div>
              <div className="set-row">
                <div>
                  <div className="k">Detect speakers (diarization)</div>
                  <div className="h">Auto-group voices when the engine emits stable labels.</div>
                </div>
                <span
                  className={`state-pill${capability.data?.supports_speaker_detection ? " on" : " off"}`}
                >
                  {capability.data?.supports_speaker_detection ? "On" : "Off"}
                </span>
              </div>
              <ReadRow
                k="Partial results"
                value={capability.data?.supports_partials ? "Streaming" : "Final only"}
              />
            </div>
          </div>
        </section>
      )}

      {/* ---------------- ANALYSIS ---------------- */}
      {tab === "analysis" && (
        <section className="set-section">
          <div className="sec-intro">
            <h2>Analysis</h2>
            <p>
              How much of the conversation the model reasons over, and when candidates get drafted.
              Confirmation is always an explicit human step.
            </p>
          </div>
          <div className="set-card">
            <div className="set-card-h">
              <div className="t">Requirement derivation</div>
            </div>
            <div className="set-card-b">
              <div className="set-row">
                <div>
                  <div className="k">Auto-draft candidates</div>
                  <div className="h">Draft as soon as a segment finalizes, instead of on demand.</div>
                </div>
                <span className={`state-pill${analysis.data?.auto_analyze ? " on" : " off"}`}>
                  {analysis.data?.auto_analyze ? "On" : "Off"}
                </span>
              </div>
              <ReadRow k="Context window" value={analysis.data?.context_mode ?? "…"} />
              <ReadRow
                k="Window size"
                value={
                  analysis.data ? `${analysis.data.window_seconds}s` : "…"
                }
              />
            </div>
          </div>
        </section>
      )}

      {/* ---------------- DATA & PRIVACY (future) ---------------- */}
      {tab === "privacy" && (
        <section className="set-section">
          <div className="sec-intro">
            <h2>
              Data &amp; privacy <span className="soon big">FUTURE ENHANCEMENT</span>
            </h2>
            <p>
              Retention and redaction for the content SpecLive stores. These sit next to storage
              because they decide what survives and for how long.
            </p>
          </div>
          <div className="future-banner">
            <span className="ic">◷</span>
            <div>
              <b>Planned, not yet available.</b> These controls are on the roadmap — retention and
              redaction are still governed by deployment settings for now.
            </div>
          </div>
          <div className="set-card disabled">
            <div className="set-card-h">
              <div className="t">Retention &amp; redaction</div>
            </div>
            <div className="set-card-b">
              <ReadRow k="Keep recordings for" value="30 days" />
              <ReadRow k="Keep transcripts for" value="90 days" />
              <ReadRow k="Redact PII before storing" value="Off" />
              <ReadRow k="Consent prompt before recording" value="On" />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function ReadRow({ k, value, mono }: { k: string; value: string; mono?: boolean }) {
  return (
    <div className="set-row">
      <div>
        <div className="k">{k}</div>
      </div>
      <span className={mono ? "val-field" : "state-pill neutral"}>{value}</span>
    </div>
  );
}
