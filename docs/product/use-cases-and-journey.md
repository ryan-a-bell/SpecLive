# Core Use Cases & User Journey

## Core use cases

| ID | Use case | Actor | Outcome |
|----|----------|-------|---------|
| UC-1 | Start / open a discovery session | Facilitator | Session anchored on a script |
| UC-2 | Ingest transcript segments (typed or streamed) | Facilitator / STT | Segments stored with speaker + timing |
| UC-3 | Derive candidate artifacts from a segment | System (mock LLM) | Inferred artifacts + evidence, never confirmed |
| UC-4 | Inspect an artifact's provenance | Facilitator | Source, rationale, confidence, evidence, state |
| UC-5 | Confirm / reject / edit / merge an artifact | Facilitator | Lifecycle transition + revision recorded |
| UC-6 | Follow the guided script; load a prompt | Facilitator | Next question in the composer |
| UC-7 | Advance the script stage | Facilitator | Progress + `script.stage.completed` event |
| UC-8 | Explore branches (git / subway) | Facilitator | See how answers branched and merged |
| UC-9 | Read the coverage matrix | Facilitator | See strong/partial/unanswered per stage×topic |
| UC-10 | Export the discovery package | Facilitator | JSON + Markdown with traceability |

## Primary user journey

```mermaid
journey
    title Discovery call with the copilot
    section Before
      Open session on script: 4: Facilitator
      Review script stage 1 prompt: 4: Facilitator
    section During
      Ask scripted question: 5: Facilitator
      Customer answers; segment streams in: 4: System
      Copilot derives candidate need/requirement: 4: System
      Facilitator clicks evidence to verify: 5: Facilitator
      Customer confirms; facilitator clicks Confirm: 5: Facilitator
      Answer spawns a branch; follow-ups suggested: 4: System
      Advance to next stage: 4: Facilitator
    section After
      Read coverage matrix for gaps: 4: Facilitator
      Generate discovery package: 5: Facilitator
      Hand package to architect: 5: Reviewer
```

## Walkthrough (seeded demo)

1. Open **Warehouse Modernization Discovery** (script: Operational Systems
   Discovery, currently on stage 3 "Workflow decisions").
2. The transcript shows the customer describing a lack of real-time visibility;
   `NEED-001` and `REQ-002` are highlighted in the text with evidence.
3. Click the "within 30 seconds" span → `REQ-002` opens in the provenance panel
   with its direct evidence and rationale.
4. The script panel recommends asking which states/exceptions matter; "Use this
   prompt" loads it into the composer.
5. The git/subway views show the States, Device, WMS, and Offline branches; the
   coverage matrix shows WMS integration strong on several stages but validation
   still open.
6. "Generate call package" downloads the Markdown discovery package.
