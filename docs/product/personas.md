# Primary Personas

## 1. Discovery Facilitator (primary user)

- **Role:** Solutions consultant / business analyst / pre-sales engineer running
  the customer conversation.
- **Goals:** Keep the conversation flowing, capture everything important, leave
  with a defensible set of requirements traced to what the customer said.
- **Pains:** Can't take deep notes while facilitating; loses nuance; later can't
  remember why a requirement was written or whether the customer confirmed it.
- **How the product helps:** Live derivation + evidence links + a guided script
  and next-question suggestions, so the facilitator can stay present and trust
  the record.

## 2. Customer Stakeholder (subject, not a user)

- **Role:** The customer being interviewed (supervisor, operations lead, IT).
- **Goals:** Be understood; not be misquoted; see their constraints respected.
- **How the product helps (indirectly):** Nothing is marked "confirmed" without
  an explicit facilitator action reflecting the customer's agreement; the
  read-back at the validation stage uses their own quoted words.

## 3. Requirements Reviewer / Architect (downstream consumer)

- **Role:** Consumes the discovery package to design a solution or write a spec.
- **Goals:** Understand each requirement's provenance, confidence, and open
  questions; distinguish confirmed from candidate items.
- **How the product helps:** The export separates confirmed vs. candidate items
  and includes a traceability appendix and open-question list.

## 4. Delivery / Ops (future)

- **Role:** Imports requirements into Jira/DOORS/ReqIF.
- **How the product helps (future):** The `ArtifactExporter` interface is built
  to add these formats without touching the core.
