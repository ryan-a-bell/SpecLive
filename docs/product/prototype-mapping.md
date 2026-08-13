# Prototype → Component / Service Mapping

This document maps every panel and interaction concept in the supplied static
prototype (`docs/product/prototype/customer_requirements_copilot_v41.html`) to
the maintainable application components and backend services that replace it.

The static prototype held all state in the DOM and mutated it with inline
`onclick` handlers. The production design separates concerns into:

- **Typed domain models** (`packages/domain`, `apps/api/app/domain`)
- **Backend services** (`apps/api/app/services`)
- **REST + streaming API** (`apps/api/app/api`)
- **React components** (`apps/web/components`)
- **Client state** (`apps/web/lib` — TanStack Query + a typed API client)

## Panel-by-panel mapping

| # | Prototype panel / element | Prototype behavior | Target React component | Backing service(s) | API surface |
|---|---------------------------|--------------------|------------------------|--------------------|-------------|
| 1 | Top bar (`.topbar`) — "Transcribing live", Save checkpoint, Generate call package | `toast()` stubs | `components/layout/TopBar.tsx` | — / `ExportService` | `GET /sessions/{id}/export` |
| 2 | Summary metrics (`.summary`) — req count, links, questions, coverage | Static counts, `#reqCount`/`#linkCount` | `components/session/SessionMetrics.tsx` | `CoverageService`, `ArtifactService` | `GET /sessions/{id}/coverage`, `/artifacts` |
| 3 | Live transcript (`.transcript-panel`) with evidence highlights + badges | `selectNode()`, `addStatement()`, evidence `<span>` highlights | `components/transcript/TranscriptPanel.tsx`, `TranscriptSegment.tsx`, `EvidenceHighlight.tsx`, `ArtifactBadge.tsx` | `TranscriptService`, `AnalysisService`, `EventBus` | `GET/POST /sessions/{id}/transcript`, `POST /sessions/{id}/analyze`, WS `/stream` |
| 4 | Composer (`.composer`) — "Add statement" | `addStatement()` appends DOM node, fake "analyzing" | `components/transcript/StatementComposer.tsx` | `TranscriptService` → `AnalysisService` | `POST /sessions/{id}/transcript` |
| 5 | Live discovery tree (`.tree-panel`) | Hand-authored nested `div`s, `type-dot` classes | `components/tree/DiscoveryTree.tsx`, `TreeNode.tsx` | `DiscoveryTreeService` | `GET /sessions/{id}/discovery-tree` |
| 6 | Selected node provenance (`.detail-panel`) | `nodes{}` object + `selectNode()` innerHTML | `components/tree/ArtifactDetail.tsx` | `ArtifactService`, `EvidenceService`, `RevisionService` | `GET/PATCH /artifacts/{id}`, `/confirm`, `/reject`, `/merge` |
| 7 | Guided discovery script (`.script-panel`) | `scriptSteps[]`, `renderScript()`, `advanceScript()` | `components/script/GuidedScriptPanel.tsx`, `ScriptProgress.tsx` | `ScriptService` | `GET /scripts`, `GET /scripts/{id}`, `POST /sessions/{id}/script/advance` |
| 8 | Conversation branches list (`.branch-map`) | `branchData{}`, `selectBranch()` | `components/branch/BranchList.tsx`, `BranchPreview.tsx` | `BranchService` | `GET /sessions/{id}/conversation-graph` |
| 9 | Recommended next questions (`.questions-panel`) | Static cards, `insertQuestion()` | `components/questions/RecommendedQuestions.tsx`, `GapList.tsx` | `RecommendationService`, `CoverageService` | derived from `/coverage` + `/discovery-tree` |
| 10 | Git branch tree viz (`#viz-git`) | Hand-drawn grid of commit/branch nodes | `components/viz/GitBranchView.tsx` | `ConversationGraphService` | `GET /sessions/{id}/conversation-graph` |
| 11 | Conversation subway viz (`#viz-subway`) | Static station rows | `components/viz/SubwayView.tsx` | `ConversationGraphService` (route projection) | `GET /sessions/{id}/conversation-graph` |
| 12 | Coverage matrix viz (`#viz-matrix`) | Static `<table>` with coverage-* classes | `components/viz/CoverageMatrix.tsx` | `CoverageService` | `GET /sessions/{id}/coverage` |
| 13 | Viz tab switcher (`switchViz()`) | Toggles `.active` | `components/viz/ConversationStructure.tsx` (tab host) | — (client state) | — |
| 14 | Toast (`toast()`) | Transient message | `components/ui/useToast` | — | — |

## Interaction concepts preserved

| Prototype concept | Production equivalent |
|-------------------|-----------------------|
| Click evidence span → select node | `EvidenceHighlight` dispatches `selectArtifact(id)`; detail + tree react via shared selection store |
| Click badge → select node | `ArtifactBadge` → same selection store |
| Click provenance evidence link → jump to segment | `ArtifactDetail` evidence link → `scrollToSegment(segmentId)` + highlight |
| `hollow` (open question) / `solid` (strong evidence) node styling | Driven by `Artifact.validation_state` + `evidence_count`, rendered by `TreeNode` |
| Confirm / Edit / Ask follow-up / Reject actions | `ArtifactDetail` action bar → `confirm`/`reject`/`patch` mutations (TanStack Query) |
| Script "Use this prompt" loads composer | `GuidedScriptPanel` → shared composer store `loadPrompt(text)` |
| "Mark answered" advances script | `POST /sessions/{id}/script/advance` |
| Branch selection updates next prompt | `BranchList` selection → `RecommendationService` next-prompt projection |
| Evidence relationship colors (blue/orange/green) | Mapped from `EvidenceLink.relationship` (`direct`/`supporting`/`contradicting`/`superseding`/`contextual`) |

## What changes vs. the prototype

- All DOM-held state becomes server state fetched with TanStack Query and typed
  with Zod schemas generated from the shared domain package.
- Fake `setTimeout` "analysis" becomes a real (mock-backed) `AnalysisService`
  that emits domain events over the `EventBus`.
- Evidence is a first-class `EvidenceLink` entity with typed relationships,
  quote offsets, and rationale — not an inline CSS class.
- Artifact edits are versioned via `ArtifactRevision`; the lifecycle
  (`detected → inferred → clarified → customer_confirmed → baselined`) is
  enforced by the domain, not implied by styling.

No major capability represented in the prototype is dropped; each of the six
core visualizations is implemented as a dedicated component fed by a service.
