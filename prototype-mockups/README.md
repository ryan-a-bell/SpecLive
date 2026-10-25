# SpecLive · Static GitHub Pages prototype site (v0.8)

SpecLive is a modular concept demonstrator for requirements elicitation and evidence-grounded engineering analysis. **The original standalone prototypes are preserved unchanged under [`mockup/`](mockup/index.html).** The new [`workbench/`](workbench/index.html) contains two independently navigable integrated interface options backed by one shared local projection engine.

## Directory structure

```text
speclive/
├── index.html                           # Overall site entrance
├── README.md
├── mockup/                              # 22 existing demo resources, unchanged
│   ├── index.html
│   ├── speclive_architecture.html
│   ├── speclive_module_01_transcription.html
│   ├── speclive_module_02_diarization.html
│   ├── speclive_module_04_evidence.html
│   ├── speclive_module_05_topics.html
│   ├── speclive_module_06_requirements.html
│   ├── speclive_module_07_coach.html
│   ├── speclive_module_08_validation.html
│   ├── *_preview.png
│   ├── f08_test_baseline.json
│   └── README.md
└── workbench/
    ├── index.html                      # Option comparison
    ├── option-a.html                   # Live Mission Control (facilitator-first)
    ├── option-b.html                   # Evidence Canvas (graph-first)
    ├── README.md
    ├── assets/
    │   ├── css/app.css                 # Shared responsive styling
    │   └── js/
    │       ├── engine.js               # Shared deterministic projections
    │       └── app.js                  # Shared controls, review and baseline
    └── data/sample_session.json
```

## Local preview and GitHub Pages

From repository root: `python -m http.server 8000`, then browse to `http://localhost:8000/`. Or deploy as a static GitHub Pages project from root or `/docs`. No installation, build step, server API, or credentials are required for the simulated experience. Do not publish confidential real conversation data on a public website.

Both options use the same engine and synchronize their working meeting state through browser `localStorage` on the same origin. Two fixtures support cloud/edge operating modes and a recovery target/capability gap. An imported F04 evidence ledger can replace the fixture. The graph uses a curated topic ontology and source-linked relationships, not LLM-created ontologies.

## Explicit limitations

These pages are functional interaction prototypes, **not LLM-backed engineering analysis**. F05–F07 use local keyword/rule projections. No microphone transcription/diarization integration is wired into the unified workbench yet. Review identity is typed, not authenticated. SHA-256 provides an integrity digest for the frozen exported baseline snapshot, not a digital signature or approval authority. Source citation references can establish *where a candidate came from* but cannot prove technical correctness. New source events invalidate existing review decisions to avoid stale approvals.

See [`workbench/README.md`](workbench/README.md) for the A/B design distinctions and behavior.
