# Architecture

Requirements Discovery Copilot is a monorepo with a clear front-end / back-end
split. The back end owns the domain, persistence, an internal event bus, and the
provider abstractions; the front end renders the six visualizations over typed
server state. This document uses the C4 model (context → container → component)
plus event-flow, derivation-sequence, and data-model diagrams.

## 1. System context

```mermaid
flowchart TB
    facilitator["Facilitator<br/>(runs the discovery call)"]
    subgraph system["Requirements Discovery Copilot"]
      web["Web app"]
      api["API + domain"]
    end
    stt["Speech-to-Text providers<br/>(local / OpenAI / Wispr Flow / mock)"]:::ext
    llm["Language-Model provider<br/>(mock today)"]:::ext
    exporttarget["Downstream tools<br/>(Jira / DOORS / ReqIF — future)"]:::ext

    facilitator -->|opens session, confirms items| web
    web -->|REST + WebSocket| api
    api <-->|provider-specific audio + transcript| stt
    api -.->|artifact derivation| llm
    api -->|JSON / Markdown package| exporttarget

    classDef ext fill:#1b2740,stroke:#3a5279,color:#cfe0f5;
```

The customer is present in the room but does not use the software directly — the
facilitator is the only user. The browser sends microphone PCM only to SpecLive.
The API selects local faster-whisper, OpenAI Realtime, Wispr Flow, or mock STT;
provider credentials and protocols never enter the frontend. LLM analysis is
still mocked, and the default configuration has no external dependency.

## 2. Container diagram

```mermaid
flowchart LR
    subgraph web["apps/web — Next.js"]
      components["Visualization components"]
      client["@rdc/client (typed API client)"]
      query["TanStack Query cache"]
    end
    subgraph api["apps/api — FastAPI"]
      routes["REST + WS routes"]
      services["Services (business logic)"]
      providers["Provider adapters<br/>(local / OpenAI / Wispr / mock)"]
      bus["Event bus (in-memory)"]
      repo["SQLAlchemy repository"]
    end
    db[("PostgreSQL<br/>(SQLite fallback)")]
    redis[("Redis — optional")]:::opt

    components --> query --> client -->|REST + SpecLive audio WS| routes
    components <-->|events| routes
    routes --> services
    services --> repo --> db
    services --> providers
    services --> bus
    bus -.->|future| redis

    classDef opt fill:#1b2740,stroke:#3a5279,color:#cfe0f5,stroke-dasharray:4 3;
```

## 3. Component diagram (API services)

```mermaid
flowchart TB
    subgraph transport["Transport (no logic)"]
      rest["REST routers"]
      ws["Event + audio WebSockets"]
    end
    subgraph svc["Services"]
      session["SessionService"]
      transcript["TranscriptService"]
      analysis["AnalysisService"]
      artifact["ArtifactService"]
      tree["TreeService"]
      branch["BranchService"]
      script["ScriptService"]
      coverage["CoverageService"]
      recommend["RecommendationService"]
      export["ExportService"]
    end
    subgraph core["Domain + ports"]
      lifecycle["Lifecycle rules"]
      entities["Entities / enums / events"]
      repoport["SessionRepository (port)"]
      llmport["LanguageModelProvider (port)"]
      sttport["SpeechToTextProvider (port)"]
      exporter["ArtifactExporter (port)"]
    end

    rest --> session & transcript & analysis & artifact & tree & branch & script & coverage & recommend & export
    ws --> bus["EventBus"]
    ws --> sttport
    sttport --> transcript
    transcript --> analysis --> artifact --> lifecycle
    analysis --> llmport
    export --> exporter
    session & transcript & artifact & branch --> repoport
    artifact & transcript & branch & coverage --> bus
```

`AnalysisService` calls `ArtifactService` with `actor_is_human=False`, which the
lifecycle rules use to forbid any automated confirmation.

## 4. Event flow

```mermaid
flowchart LR
    seg["transcript.segment.finalized"] --> analyze["AnalysisService"]
    analyze --> cand["artifact.candidate.created"]
    analyze --> ev["evidence.link.created"]
    cand --> treeupd["discovery-tree refresh"]
    confirm["artifact.confirmed"] --> covupd["coverage.updated"]
    branchcr["branch.created"] --> graphupd["conversation-graph refresh"]
    subgraph bus["EventBus (sync now, queue-ready)"]
      seg; cand; ev; confirm; branchcr; covupd
    end
    bus -->|WebSocket frames| webclient["Web client"]
```

All events implement `DomainEvent.to_wire()`; the same frames feed the WebSocket
today and could feed a Redis/queue consumer later without code changes in the
services.

## 5. Transcript → requirement derivation sequence

```mermaid
sequenceDiagram
    participant F as Facilitator
    participant W as Web app
    participant A as API (services)
    participant L as LLM provider (mock)
    participant DB as Database

    F->>W: Add customer statement
    W->>A: POST /sessions/{id}/transcript
    A->>DB: persist TranscriptSegment
    A-->>W: 201 segment
    W->>A: POST /sessions/{id}/analyze
    A->>L: analyze_segment(text)
    L-->>A: [ArtifactCandidate + EvidenceCandidate]
    A->>DB: persist Artifact (state=inferred), EvidenceLink
    A-->>W: candidate artifacts (never confirmed)
    W->>A: POST /artifacts/{id}/confirm  (explicit human action)
    A->>DB: transition → customer_confirmed, write ArtifactRevision
    A-->>W: confirmed artifact
    F->>W: Generate call package
    W->>A: GET /sessions/{id}/export
    A-->>W: JSON + Markdown discovery package
```

## 6. Data model

```mermaid
erDiagram
    DiscoverySession ||--o{ TranscriptSegment : has
    DiscoverySession ||--o{ DiscoveryArtifact : has
    DiscoverySession ||--o{ ConversationBranch : has
    DiscoverySession }o--|| ScriptDefinition : uses
    ScriptDefinition ||--o{ ScriptStage : contains
    DiscoveryArtifact ||--o{ EvidenceLink : "supported by"
    DiscoveryArtifact ||--o{ ArtifactRevision : "versioned by"
    DiscoveryArtifact }o--o| DiscoveryArtifact : "parent / superseded_by"
    TranscriptSegment ||--o{ EvidenceLink : "quoted by"
    ConversationBranch ||--o{ ConversationNode : contains
    ConversationNode }o--o| TranscriptSegment : references
    ConversationNode }o--o| DiscoveryArtifact : references

    DiscoveryArtifact {
      string id PK
      string artifact_type
      string validation_state
      float confidence
      string derivation_method
      string parent_id FK
    }
    EvidenceLink {
      string id PK
      int quote_start
      int quote_end
      string relationship
    }
```

See the [ADR index](../adr/README.md) for the decisions behind these
structures.
