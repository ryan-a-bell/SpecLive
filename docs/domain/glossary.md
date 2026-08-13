# Domain Glossary

| Term | Definition |
|------|------------|
| **Discovery session** | One customer discovery conversation, anchored on a script. Owns transcript, artifacts, and branches. |
| **Transcript segment** | One utterance with a stable id, speaker, start/end time, text, finality, and sequence number. |
| **Discovery artifact** | Any derived item: objective, stakeholder need, requirement, constraint, assumption, risk, decision, open question, success metric, integration, or stakeholder. |
| **Artifact type** | The category of an artifact (see above). |
| **Validation state** | Position in the lifecycle: `detected → inferred → clarified → customer_confirmed → baselined`, plus `rejected`/`superseded`/`merged`. |
| **Status** | UI rollup of validation state: candidate / confirmed / baselined / rejected / superseded. |
| **Confidence** | 0–1 score of how strongly the artifact is supported. Illustrative under the mock provider. |
| **Derivation method** | How an artifact was produced: manual, keyword_heuristic, llm, imported. |
| **Evidence link** | First-class connection from an artifact to an exact quoted span in a segment, with a typed relationship and rationale. |
| **Evidence relationship** | direct / supporting / contradicting / superseding / contextual. |
| **Artifact revision** | An immutable record of a change to an artifact (previous/new value, who, why). |
| **Script definition** | A versioned, ordered set of stages that guides the conversation. |
| **Script stage** | One step of a script: objective, primary prompt, alternatives, completion criteria. |
| **Conversation branch** | A thread spawned from a script stage/answer, holding follow-ups, findings, and artifacts; may merge back. |
| **Conversation node** | A point on a branch (script_stage/question/answer/finding/requirement/risk/decision/merge). |
| **Coverage state** | Per stage×topic strength: unanswered / partial / strong / contradictory / needs_validation / confirmed. |
| **Discovery tree** | The evolving hierarchy Objective → Need → (Requirement/Constraint/Risk/Assumption/Open question). |
| **Discovery package** | The structured export (JSON/Markdown) produced at the end of a session. |
| **Provider** | An adapter behind an interface (STT/LLM/embedding/exporter/repository/event bus); the only place external services are integrated. |
| **Domain event** | A typed record of something that happened (e.g. `artifact.confirmed`), published on the event bus. |
