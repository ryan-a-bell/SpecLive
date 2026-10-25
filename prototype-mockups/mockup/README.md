# SpecLive · Static HTML Prototype Lab (v0.6)

A browser-only, GitHub Pages compatible functional demonstration of the **eight-function SpecLive requirements-discovery architecture**. No package manager, bundler, external JavaScript, or backend is needed for the scripted and import-based prototypes.

## Included prototypes

| Page | Purpose |
|---|---|
| `index.html` | Interactive showcase with embedded module previews |
| `speclive_architecture.html` | Eight-function architecture and interface contracts |
| `speclive_module_01_transcription.html` | F03: speech-to-text / transcript events |
| `speclive_module_02_diarization.html` | F02: speaker attribution and interval events |
| `speclive_module_04_evidence.html` | F04: speaker–transcript time alignment, evidence citations, review history and live feed |
| `speclive_module_05_topics.html` | F05: evolving topics, coverage dashboard, interactive knowledge graph, three local detection strategies |
| `speclive_module_06_requirements.html` | F06: explicit candidates, guarded derived hypotheses, potential contradictions, feasibility gaps, structured-model-output validator |
| `speclive_module_07_coach.html` | F07: prioritized question queue, scoring strategy comparison, source explanations, response feedback, and external model adapter |
| `speclive_module_08_validation.html` | **NEW F08**: human decision authority, issue dispositions, traceability, controlled baseline exports |

## Functional architecture

```text
F01 Audio capture
   ├── F02 speaker diarization ──┐
   └── F03 speech-to-text ──────┴── F04 timestamped evidence ledger
                                          │
                             ┌────────────┴────────────┐
                             ▼                         ▼
                      F05 Topic state           F06 Requirements intelligence
                    coverage + graph           candidates / issues / synthesis
                             └────────────┬────────────┘
                                          ▼
                                F07 question coaching
                                          │
                                 Answers return to F04
                                          │
                               F08 human validation
```

F05 and F06 are parallel analyses, not necessarily a sequential blocking chain. Both may replay after a meeting. F07 consumes their outputs and recommends questions. F08 remains the only approval/baselining stage.

## F05 walkthrough

1. Open `speclive_module_05_topics.html`. Choose **Load scenario** and advance utterances individually, or click **Auto-play**.
2. Select **Knowledge graph** to switch from coverage cards to the relationship graph. Click topics to inspect cited evidence; drag topics, zoom, optionally show evidence nodes or hide uncovered topics.
3. Compare **Keyword rules**, **Local TF-IDF similarity**, and **Hybrid**. Change relevance threshold and observe matched topic state. Scores are not probabilities or validation coverage.
4. Use **Import F04 JSON** to load an exported F04 evidence ledger. The app validates schema, time bounds, unique evidence IDs and single-session consistency.
5. Export `speclive.topic_coverage.v0.1` with topic-to-evidence references, curated relationship labels, and outstanding topic questions.

The knowledge graph is a **visualization of the common topic model**, not an independently inferred ontology. Relationships between topics are curated and labeled. Evidence nodes are created from actual referenced utterance IDs. Discussion counts proxy for coverage; they do not prove elicitation completeness.

### F04 → F05 live browser link

The F04 and F05 pages can also communicate through an opt-in same-origin `BroadcastChannel` (supported browsers). On a deployed Pages site:

1. Open **F04** and **F05** in tabs of the **same published GitHub Pages origin**, or embed both in the hub.
2. In **F05**, click **Connect F04 live**.
3. In **F04**, select **Broadcast F04 evidence to F05 topic tracker**; load a scenario, advance a turn, or import/review evidence.
4. F05 receives versioned **F04 snapshots** and recomputes topic links. Source revisions replace earlier snapshots instead of accumulating duplicates.

This is same-browser inter-tab communication, not a persistent server push. `BroadcastChannel` is not a cross-device networking channel. F04 JSON import remains the portable integration mechanism.

## F06 walkthrough

1. Open `speclive_module_06_requirements.html`; load the **Service recovery** or **Offline vs cloud** scenario. Advance utterances and observe explicit requirement candidates, derived hypotheses (guarded mode) and issues.
2. Switch **Analysis strategy**:
   - **Strict rules**: surface explicit modal and target expressions; no derived hypothesis.
   - **Guarded hybrid**: add narrowly-scoped engineering hypotheses and pairwise known issue patterns. These are heuristic, not model reasoning.
   - **External structured-model output**: import a candidate JSON response generated **outside** GitHub Pages. No actual LLM inference is performed in this browser. An illustrative sample and JSON contract are included.
3. Select any requirement or issue to read **the precise original quotation, speaker, time range, and evidence ID**.
4. Download the F06 JSON payload, `speclive.requirements_intelligence.v0.1`, for later F07 integration.

**Difference between issue types:** a stated 30-second target versus current 120-second performance is a **feasibility gap**; incompatible stakeholder requirements for the same function can be a **potential conflict**; cloud/edge statements with unclear function scope represent **ambiguity**. An alternative rejected by a stakeholder must not be presented as a successful reconciliation.

### Model adapter

`F06` accepts `speclive.requirement_model_response.v0.1` with matching `session_id`, nonempty `evidence_ids` and unique finding IDs. Every cited evidence ID must exist in the imported/current F04 record. This is only provenance validation, not factual/semantic entailment validation. A future secure inference service can perform model calls server-side and return this typed response. Do not embed API tokens in public Pages HTML.

### Example F06 structured output

```json
{
  "schema": "speclive.requirement_model_response.v0.1",
  "session_id": "SESSION-ID-FROM-F04",
  "candidates": [
    {
      "id": "MODEL-R-001",
      "kind": "explicit",
      "statement": "A proposed requirement interpretation",
      "scope": "SERVICE_RECOVERY",
      "evidence_ids": ["EXACT-F04-EVIDENCE-ID"],
      "rationale": "Explain the cited source relationship"
    }
  ],
  "issues": []
}
```

Use F06 **Model contract** to download a session-specific starting template.

## F07 walkthrough

1. Open `speclive_module_07_coach.html`, load the **Offline/Cloud** scenario and advance four or five statements. Watch the conflict clarification question rise above less urgent uncovered topics. Use **Recovery** for a feasibility-gap example.
2. Compare **Balanced**, **Risk-first**, and **Coverage-first** strategies or adjust the relative issue/coverage sliders. Scores are explained (base salience, issue boost, coverage boost, reference count) and deliberately **not** described as calibrated confidence or expected information gain.
3. Select a recommendation to inspect the triggering F04 evidence records and precise speaker/timestamp/ID citations; coverage questions may intentionally have no evidence because that area was unaddressed.
4. Use example responses or type what a participant says. **Record & recalculate** appends provisional manual evidence, marks the question answered, and recomputes rankings. This is not an authenticated audio record or human approval. If imported F05/F06 snapshots become outdated after a manual response, they are invalidated and local fallback analysis resumes until new matching snapshots are imported.
5. Import same-session **F04**, **F05**, and **F06** JSON files in that order to prioritize actual upstream outputs. Imported references are checked against the F04 ledger; mismatched session IDs and unknown evidence references are rejected.
6. Download an **LLM request context** (sensitive: contains meeting utterances), send it to an authorized backend, and import a `speclive.coach_model_response.v0.1` response. The HTML does not call an LLM or store API keys. The **Load demo model suggestions** button only illustrates response format.
7. Export `speclive.question_coaching.v0.1`: ranked questions with rationale, actions, dispositions, and provisional answer evidence. Human approval belongs to F08.

Example external coach response (use the actual session and source ID from the generated request):

```json
{
  "schema": "speclive.coach_model_response.v0.1",
  "session_id": "SAME-SESSION-AS-F04",
  "suggestions": [{
    "id": "MODEL-Q-001",
    "title": "Clarify operating modes",
    "question": "Which critical functions must execute without connectivity?",
    "rationale": "The cited statement lacks specific functional scope.",
    "evidence_ids": ["EXACT-F04-EVIDENCE-ID"]
  }]
}
```

### F04 → F07 live browser link

The **Connect F04** button listens to the same-origin F04 `BroadcastChannel` snapshot stream. In F04 enable **Broadcast F04 evidence to F05** (the channel name is unchanged for compatibility) and step the meeting. F07 will recompute its local fallback queue. F05/F06 currently export compatible JSON but **do not publish live snapshots into F07**; for the full intelligence pipeline, import updated F05/F06 exports after source changes or add an orchestrating backend in a later iteration.

## F08 — Human Validation & Controlled Baseline (v0.6)

Open `speclive_module_08_validation.html` independently or from the hub. It supports **two illustrative meetings** (edge/cloud functional allocation and 30-second recovery feasibility).

1. Load a scripted meeting or import **matching session** `speclive.evidence.v0.1` **F04 JSON first**, then `speclive.requirements_intelligence.v0.1` **F06 JSON**. Optionally import `speclive.question_coaching.v0.1` **F07 JSON**. Requirements and issues are not implicitly approved. Incorrect schema, conflicting session IDs, unknown evidence IDs, duplicate identifiers, and malformed intervals are rejected.
2. Enter the **reviewer name and authority role** on the Baseline tab before any disposition. These are local, self-asserted values, **not authenticated electronic signatures**.
3. On the Requirements board, inspect the actual source quotation, speaker, timestamp and evidence ID. Change draft wording, specify an acceptance/verification method, adjust citation links, and explicitly **Approve**, **Reject**, **Defer** or **Reopen** with a written rationale. Approved revision is tracked as a distinct disposition.
4. On Conflicts, explicitly **Resolve**, **Accept risk/waiver**, **Not applicable**, **Defer** or **Reopen** each issue. Risk acceptance requires a risk register/waiver reference. An unresolved feasibility gap or contradictory assertion blocks release.
5. Inspect the Evidence matrix to see source-to-requirement links. Manually entered F07 answers are **provisional** and require source attribution verification and a reconciliation attestation. F07 responses do not silently rewrite earlier requirements.
6. When every gate passes, enter the baseline ID, version and release statement and press **Seal controlled baseline**. A snapshot is frozen and SHA-256 hashed using browser Web Crypto (requires HTTPS or localhost); export `speclive.specification_baseline.v0.1` JSON including full audit and citations, approved requirements CSV, and a Markdown specification with an evidence appendix.
7. **Save draft** exports `speclive.review_state.v0.1` for resuming later in a browser. The browser does not automatically persist sensitive transcript information. **Begin next revision** starts a new review draft, retaining citations but requiring renewed dispositions.

**Assurance boundary:** F08's gates enforce an example workflow; they cannot verify that statements are technically correct, that the person typing a reviewer's name is authorized, or that imported testimony is genuine. Deploying with a production configuration management system would require access control, reviewer authentication, independent verification, immutable backend storage and organization-specific release policies. The SHA-256 digest detects changes to the exported JSON payload but is not a signer identity proof.

### F08 output shapes

- `speclive.review_state.v0.1`: resumable draft, annotations, reviewer dispositions, issue states and audit log.
- `speclive.specification_baseline.v0.1`: sealed approval snapshot with source evidence, requirement dispositions, issues, reviewer declarations and SHA-256 digest.
- Approved-only CSV and evidence-linked Markdown report (non-approved decisions remain in the JSON baseline).

## GitHub Pages publish

1. Copy all HTML files to a repository root or `docs/`.
2. Under **Settings → Pages**, enable branch deployment and choose that folder.
3. Open the Pages URL. `index.html` is the default hub. Standalone modules use their own shareable URLs.

For embedding:

```html
<iframe src="speclive_module_05_topics.html" title="F05 Topic intelligence" width="100%" height="900"></iframe>
<iframe src="speclive_module_06_requirements.html" title="F06 Requirements intelligence" width="100%" height="900"></iframe>
<iframe src="speclive_module_07_coach.html" title="F07 Adaptive question coach" width="100%" height="900"></iframe>
<iframe src="speclive_module_08_validation.html" title="F08 Human validation and baseline" width="100%" height="900"></iframe>
```

For a microphone module, host over HTTPS/localhost and grant microphone permission as appropriate. To test locally: `python -m http.server 8000` and open `http://localhost:8000`.

## Safety, limits and fidelity

- F02 acoustic heuristic is not reliable production speaker diarization; F03 browser speech recognition can use external speech providers and timestamps may be approximate.
- F04 joins intervals by overlap; without a shared session clock, attribution alignment may be invalid. Mismatched clocks must remain explicitly flagged.
- F05 topic labels are rule/TF-IDF matches. Topic ontology edges are curated; no model infers actual engineering constraints.
- F06 is a deterministic proof of concept; there is **no live LLM reasoning, full natural-language entailment, or validated general-domain requirement extraction**.
- F05/F06 share evidence IDs and schemas but imported evidence does not contain audio. Exact textual citation != original waveform verification.
- F06 explicit candidates, derived hypotheses, and proposed resolutions are **not validated requirements**. Only F08 is an authority/approval gate.
- F07 is now implemented as an independent scoring/feedback prototype; its prioritization heuristics and entered answers remain unvalidated. F08 is now implemented as a browser-only review, disposition and controlled-baseline prototype. Its reviewer identity is self-asserted, not cryptographically authenticated.
