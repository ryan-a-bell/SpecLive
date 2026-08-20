# SpecLive frontend explorations

## Facilitator Cockpit

Open [`facilitator-cockpit.html`](facilitator-cockpit.html) directly in a browser.
It is a standalone, responsive prototype with no build step or external assets.

This concept deliberately moves away from the production UI's three-panel
dashboard and graph-heavy conversation views. It prioritizes what a facilitator
needs in the moment:

- **One best-next-move card** keeps the recommended question prominent while
  the facilitator is speaking and listening.
- **Meaning attached to conversation** places evidence and derived artifacts
  inline instead of separating transcript and discovery tree.
- **A decision queue** turns human confirmation into a small, actionable inbox
  and explicitly calls out interpretation boundaries.
- **Topic threads** replace git/subway metaphors with a lightweight way to
  revisit answer-driven branches.
- **Discovery health** summarizes where the conversation is strong and names
  the highest-value gap.
- **Trace drawers** preserve evidence, rationale, structured meaning, and
  revision history without permanently occupying the workspace.
- **Read-back mode** creates a customer-safe summary that hides model language,
  confidence scores, and internal artifact structure.

The demo interactions include loading recommended questions, adding a prompt to
the conversation, inspecting provenance, confirming or rejecting candidates,
switching to customer read-back mode, and changing read-back confirmation
states.

The **Requirement map** tab adds a selectable decomposition from business
objective to stakeholder need, requirements, constraints, and risks. Its detail
panel shows evidence, verification intent, and the lower-level behaviors or open
decisions beneath each node.

## Conversation Trajectory Map

Open [`conversation-trajectory.html`](conversation-trajectory.html) directly in
a browser. This is a separate map-first interface rather than a variation on
the cockpit layout.

The main canvas treats discovery as a trajectory through time:

- Facilitator questions and customer answers form the main route.
- Answers visibly fork into topic branches such as states, integration, and
  offline operation.
- Derived requirements sit at the points where customer language becomes
  structured meaning.
- Gaps appear as unresolved destinations along a route, including missing
  success measures and unbounded offline behavior.
- A playback scrubber reconstructs how the map developed over the session.
- Lenses isolate conversation events, requirements, or gaps.
- Selecting any point explains its evidence, path through the conversation,
  and remaining unknowns.
