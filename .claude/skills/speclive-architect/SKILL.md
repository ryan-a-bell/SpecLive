---
name: speclive-architect
description: >-
  Turn requirements gathered in SpecLive (the Requirements Discovery Copilot)
  into a software architecture. Use this whenever the user wants to design,
  architect, or propose a system, service, or technical solution FROM a
  SpecLive workspace, discovery session, or its gathered requirements — e.g.
  "architect a solution for the Acme workspace", "design the system that meets
  these discovery requirements", "pull the requirements from SpecLive and
  propose an architecture", "what should we build for <customer>". Trigger it
  even when the user doesn't say "SpecLive" explicitly but points at a
  workspace/customer's discovered requirements and wants an architecture. It
  pulls the aggregated, evidence-traced requirements over SpecLive's live HTTP
  API and produces two artifacts: a context pack and an architecture document
  in which every design decision is traced back to the requirement IDs and
  transcript evidence it satisfies. Do NOT use it for gathering or editing
  requirements, running discovery calls, or generic architecture questions
  unconnected to a SpecLive workspace.
---

# Architect from SpecLive requirements

SpecLive captures customer-discovery conversations and derives requirements that
stay traceable to the exact transcript evidence they came from — and, crucially,
tracks which items a human has **confirmed** versus which a model merely
**inferred**. This skill consumes that data through the workspace context API and
turns it into an architecture you can defend, because every decision points back
to the requirement and evidence behind it.

You produce **two artifacts**:

1. `context-pack.md` — the workspace's requirements, organized and labelled by how
   much they can be trusted. This is the input an architect (human or model)
   reasons from.
2. `architecture.md` — the proposed architecture that meets those requirements,
   with each decision traced to requirement IDs.

## The one idea that makes this valuable

SpecLive's whole purpose is to stop requirements from being *prematurely
"confirmed"*. So the trust label on each item is not decoration — it changes what
you may do with it:

- **FIRM** = `validation_state` of `customer_confirmed` or `baselined`. A human
  signed off. **Architect against these**; they are the contract.
- **TENTATIVE** = anything else (`detected`, `inferred`, `clarified`). A model
  proposed it; nobody confirmed it. **Design to accommodate these, but record each
  as an explicit assumption that still needs sign-off.** Never present a tentative
  item as a settled requirement.

A common and important case: the confirmed set is thin — often the *objectives*
and *constraints* are confirmed while the functional *requirements* are still
candidates. When that happens, build on the confirmed objectives and constraints,
and be honest that the feature-level requirements are assumptions pending
confirmation. Don't paper over it.

## Workflow

### 1. Pull the context

Run the bundled fetch script — it lists workspaces, resolves the one you want,
pulls the full bundle (`scope=all`, so nothing is hidden), classifies every item
FIRM vs TENTATIVE, and writes `context-pack.md` + `context.json`:

```bash
python <skill>/scripts/fetch_context.py --out <work-dir> [--workspace <id>] [--base-url <url>]
```

- The base URL defaults to `$SPECLIVE_API_BASE_URL` or `http://localhost:8000`.
- Omit `--workspace` when only one exists; if several do, the script lists them
  and asks you to pick.
- If the API is unreachable, the script says so. Check whether the SpecLive API is
  running and confirm the base URL with the user rather than inventing data. (An
  offline exported-file mode is planned but not yet available.)

Read the resulting `context-pack.md`. If you need raw detail (all evidence quotes,
per-session tags), read `context.json`.

### 2. Understand before you design

From the context pack, get clear on:

- the **firm contract** — the confirmed objectives, needs, requirements, and
  constraints the design must satisfy;
- the **tentative items** you'll carry as assumptions, and which are high-stakes if
  wrong (low confidence + load-bearing);
- **constraints** (existing systems to keep, target hardware, deadlines) — these
  shape the architecture more than features do;
- **success metrics** — turn these into measurable non-functional targets;
- **open questions & risks** — these become design risks or deferred decisions.

If the firm contract is too thin to design against at all, say so and ask the user
how to proceed (e.g. treat specific candidates as provisional) rather than
silently promoting candidates.

### 3. Write the architecture document

Follow `references/architecture-doc.md` for the exact structure. It mirrors this
repo's own house style: C4 context/container/component views with **Mermaid**
diagrams, ADR-style decision blocks (Context / Decision / Consequences), a
requirements-coverage table, and an assumptions/risks section.

Non-negotiables that make the output worth trusting:

- **Trace every load-bearing choice to requirement IDs** inline (e.g. "a status
  cache fed by change-data-capture keeps refresh under 30s (REQ-002)").
- **Keep firm and tentative visibly separate** — a "commits to" table for firm
  items, an "assumptions to confirm" table for tentative ones.
- **Honor constraints and hit success metrics** explicitly in the design and its
  decisions.
- **Never invent requirements.** If the design needs something the workspace never
  captured, record it as a new assumption or open question — don't fold it in as
  if the customer asked for it.

### 4. Hand back both artifacts

Tell the user where `context-pack.md` and `architecture.md` are, and lead with the
honest headline: what the design commits to, and the biggest assumption or open
question a reviewer should challenge before it's baselined.

## Files

- `scripts/fetch_context.py` — pulls + classifies the workspace context (stdlib only).
- `references/architecture-doc.md` — the architecture document template and rules.
