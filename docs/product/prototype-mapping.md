# Prototype → Component Mapping

Reference: `customer_requirements_copilot_v4.html` (supplied static prototype).
Every major panel in the prototype maps to a React component in `apps/web` and a
domain service in `apps/api`. No prototype capability was dropped.

| Prototype panel / element | React component (`apps/web/src/components`) | API surface | Domain service (`apps/api/app/services`) |
|---|---|---|---|
| Top bar (brand, live status, checkpoint, generate package) | `layout/TopBar.tsx` | `PATCH /sessions/{id}`, `GET /sessions/{id}/export` | `export_service` |
| Summary metrics strip | `SummaryBar.tsx` | `GET /sessions/{id}` (embedded stats) | `session_service.session_stats` |
| Live transcript (messages, evidence highlights, artifact badges) | `transcript/TranscriptPanel.tsx`, `transcript/MessageItem.tsx`, `transcript/EvidenceText.tsx` | `GET/POST /sessions/{id}/transcript`, WS `transcript.segment.received` | `transcript_service`, `analysis_service` |
| Conversation composer ("Simulate a new customer statement…") | `transcript/Composer.tsx` | `POST /sessions/{id}/transcript` | `transcript_service` → `analysis_service` (auto-derivation) |
| Live discovery tree (typed dots, confidence, evidence counts) | `tree/DiscoveryTreePanel.tsx`, `tree/TreeNode.tsx` | `GET /sessions/{id}/discovery-tree` | `tree_service` |
| Selected node provenance (type, status, rationale, evidence links, confirm/edit/reject actions) | `detail/ArtifactDetailPanel.tsx` | `PATCH /artifacts/{id}`, `POST /artifacts/{id}/confirm\|reject\|merge` | `artifact_service` (lifecycle state machine), `revision_service` |
| Guided discovery script (progress dots, current stage, "Say next" prompt, checkpoints) | `script/ScriptPanel.tsx` | `GET /scripts/{id}`, `POST /sessions/{id}/script/advance` | `script_service` |
| Conversation branch list + branch preview | `script/BranchList.tsx` | `GET /sessions/{id}/conversation-graph` | `branch_service` |
| Recommended next questions + active gaps | `questions/QuestionsPanel.tsx` | `GET /sessions/{id}/coverage` (gaps), recommended questions in script payload | `coverage_service`, `question_service` |
| Git branch tree visualization | `viz/GitBranchView.tsx` (custom CSS-grid/SVG lanes) | `GET /sessions/{id}/conversation-graph` | `branch_service` |
| Conversation subway visualization | `viz/SubwayView.tsx` | `GET /sessions/{id}/conversation-graph` (routes derived from branches + stages) | `branch_service` |
| Coverage matrix | `viz/CoverageMatrixView.tsx` | `GET /sessions/{id}/coverage` | `coverage_service` |
| Toast notifications | `ui/Toaster.tsx` | n/a (client-side) | n/a |
| `selectNode()` / `jumpTo()` cross-highlighting | `store/useWorkspaceStore.ts` (Zustand selection state) | n/a | n/a |

Deviations from the prototype's implied behavior are documented in ADRs
(`docs/adr`), most notably custom lane renderers instead of React Flow
(ADR-0008) and a slim monorepo without separate `packages/` (ADR-0001).
