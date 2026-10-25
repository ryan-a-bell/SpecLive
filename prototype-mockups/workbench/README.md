# SpecLive integrated workbench — two interactive options

Choose between `option-a.html` (Live Mission Control, facilitator-focused) and `option-b.html` (Evidence Canvas, evidence/graph-focused). `index.html` compares both.

Both pages share the same **actual JavaScript projection engine** and browser-local session state. These are two operational perspectives on a common working prototype, not separate screenshots or iframe composites. They use regular `<script>` tags and no external packages, so opening a page directly works; serving with `python -m http.server 8000` from the site root or GitHub Pages is recommended for reliable browser storage and SHA-256 digests.

## Directory

```text
workbench/
├── index.html
├── option-a.html
├── option-b.html
├── assets/
│   ├── css/app.css          # Shared responsive design system
│   └── js/
│       ├── engine.js        # Deterministic, inspectable F05–F07 projections
│       └── app.js           # F04 data imports, simulation, graph, F08 decisions/export
└── data/
    └── sample_session.json  # Demonstration metadata
```

## Interactive paths

1. Select the cloud/edge or service-recovery session; use **Next turn** or **Auto play**.
2. Click a transcript line, topic, graph node, candidate, issue, or question to inspect exact citations.
3. Switch coaching strategies (`Balanced`, `Risk first`, `Coverage first`). Enter a participant's exact response to create **new provisional evidence**.
4. Select a candidate requirement, enter a reviewer and rationale, and approve/revise/reject/defer. Select an issue to record an explicit human resolution. 
5. Seal the baseline once all gates pass; SHA-256 of the frozen snapshot is attached to export. New revisions unlock editing without silently modifying the old exported baseline.
6. Option A includes a **Coverage / Knowledge graph** switch. Option B defaults to a knowledge graph and offers **Topics / Traceability** views.
7. Import an exported `speclive.evidence.v0.1` JSON file from `../mockup/speclive_module_04_evidence.html`. The source evidence IDs, timestamps, and speaker attribution fields are preserved. There are deliberately no API keys in the browser.

## Important limitations

- **Simulated analysis**: F05 topic detection is keyword-based and F06 extraction/issue pairing is a constrained rule demonstration. None of these outputs constitute validated engineering requirements. Runtime LLM calls and actual microphone processing are not integrated.
- **Citation references ≠ semantic proof**: a cited statement is inspectable, but the browser does not guarantee that a candidate requirement follows correctly from the statement.
- **Graph edges**: Topic-to-topic edges are a **curated taxonomy**. Requirement-to-topic edges derive from predefined rule topic assignments. Issue-to-requirement edges indicate **shared source evidence**, not guaranteed logical entailment.
- **Review and identity**: Human review records a typed identity and rationale but cannot authenticate individuals. The SHA-256 digest detects subsequent snapshot changes; it is **not** a signature, an independent timestamp, or proof of legal authority.
- **Sync**: browser `localStorage` allows switching between the two views on the same origin; it is not a database. Other devices will not sync.
- **Baseline gate**: requires a named reviewer, at least one approved/revised candidate, decisions for all candidates, and explicit disposition of every issue. Deferred items block the baseline.
- **Mockups**: all original pages in `../mockup/` are left byte-for-byte unchanged.
