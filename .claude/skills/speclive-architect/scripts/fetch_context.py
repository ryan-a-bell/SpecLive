#!/usr/bin/env python3
"""Pull a SpecLive workspace's aggregated requirements over the live HTTP API
and render a clean, architecture-ready context pack.

This is the deterministic "hit the endpoint and organize the data" step so the
model can spend its effort on the architecture, not on curl plumbing and
JSON wrangling. It:

  1. lists workspaces (``GET /api/v1/workspaces``) and resolves the one asked
     for (or the only one that exists);
  2. fetches the full context bundle (``scope=all``) so nothing is hidden;
  3. classifies every artifact by how much it can be trusted — ``firm`` for
     human-confirmed items (``customer_confirmed`` / ``baselined``) vs
     ``tentative`` for everything a model merely inferred — because the whole
     point of SpecLive is that you architect *against* the firm set and treat
     the rest as assumptions to confirm;
  4. writes ``context-pack.md`` (human/LLM-readable) and ``context.json`` (the
     raw bundle) and prints a short summary to stdout.

Stdlib only — no third-party dependencies — so it runs wherever Python does.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

# States a human explicitly confirmed. No automated derivation path can reach
# these in SpecLive, so they are the set that is safe to commit a design to.
FIRM_STATES = {"customer_confirmed", "baselined"}

# The artifact sections carried in a context bundle, in a sensible reading order.
SECTIONS = [
    ("objectives", "Objectives"),
    ("stakeholder_needs", "Stakeholder needs"),
    ("confirmed_requirements", "Confirmed requirements"),
    ("candidate_requirements", "Candidate requirements"),
    ("constraints", "Constraints"),
    ("assumptions", "Assumptions"),
    ("risks", "Risks"),
    ("decisions", "Decisions"),
    ("open_questions", "Open questions"),
    ("success_metrics", "Success metrics"),
]


def _get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        sys.exit(f"ERROR: {exc.code} {exc.reason} for {url}")
    except urllib.error.URLError as exc:
        sys.exit(
            f"ERROR: could not reach {url} ({exc.reason}).\n"
            f"Is the SpecLive API running? Start it, or pass --base-url. "
            f"See the skill for the offline-file plan (not yet available)."
        )


def resolve_workspace(base_url: str, workspace: str | None) -> str:
    workspaces = _get(f"{base_url}/api/v1/workspaces")
    if not workspaces:
        sys.exit("ERROR: no workspaces exist yet — run some discovery sessions first.")
    ids = [w["id"] for w in workspaces]
    if workspace:
        if workspace in ids:
            return workspace
        sys.exit(f"ERROR: workspace {workspace!r} not found. Available: {', '.join(ids)}")
    if len(ids) == 1:
        return ids[0]
    listing = "\n".join(
        f"  - {w['id']}  ({w['name']}, {w['session_count']} conversation(s))" for w in workspaces
    )
    sys.exit(f"ERROR: several workspaces exist — pass --workspace <id>:\n{listing}")


def is_firm(item: dict) -> bool:
    return item.get("validation_state") in FIRM_STATES


def _render_item(item: dict) -> str:
    trust = "FIRM" if is_firm(item) else "TENTATIVE"
    conf = item.get("confidence")
    conf_str = f", {conf:.0%} conf" if isinstance(conf, (int, float)) else ""
    ident = item.get("id", "?")
    title = item.get("title", "")
    statement = item.get("statement") or ""
    state = item.get("validation_state", "?")
    line = f"- **[{trust}] {ident} — {title}** ({state}{conf_str})"
    if statement:
        line += f"\n  {statement}"
    return line


def render_context_pack(bundle: dict) -> str:
    ws = bundle["workspace"]
    lines: list[str] = []
    add = lines.append

    add(f"# Context pack — {ws['name']}")
    add("")
    add(f"- Workspace: `{ws['id']}` · {ws['session_count']} conversation(s)")
    add(f"- Generated: {bundle['generated_at']}")
    add("")
    add("> **How to read this.** Items tagged **FIRM** are human-confirmed — architect")
    add("> against them. Items tagged **TENTATIVE** are model-inferred and NOT yet")
    add("> confirmed: design to accommodate them, but record each as an explicit")
    add("> assumption that still needs sign-off. Every item traces to transcript")
    add("> evidence in the traceability section below.")
    add("")

    firm_total = tentative_total = 0
    for key, label in SECTIONS:
        items = bundle.get(key) or []
        if not items:
            continue
        add(f"## {label}")
        add("")
        for it in items:
            add(_render_item(it))
            if is_firm(it):
                firm_total += 1
            else:
                tentative_total += 1
        add("")

    add("## Traceability (artifact → evidence)")
    add("")
    for t in bundle.get("traceability", []):
        quotes = (
            "; ".join(f"“{e['quoted_text']}” [{e['segment_id']}]" for e in t.get("evidence", []))
            or "_no evidence_"
        )
        add(f"- **{t['artifact_id']}** ({t['type']}, {t['validation_state']}): {quotes}")
    add("")

    add("## Summary")
    add("")
    add(f"- FIRM (confirmed) items: {firm_total}")
    add(f"- TENTATIVE (unconfirmed) items: {tentative_total}")
    add("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SPECLIVE_API_BASE_URL", "http://localhost:8000"),
        help="SpecLive API base URL (default: $SPECLIVE_API_BASE_URL or http://localhost:8000)",
    )
    parser.add_argument("--workspace", help="Workspace id (optional if only one exists)")
    parser.add_argument("--out", default=".", help="Directory to write context-pack.md + context.json")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    workspace_id = resolve_workspace(base_url, args.workspace)
    bundle = _get(f"{base_url}/api/v1/workspaces/{workspace_id}/context?scope=all")

    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "context.json")
    md_path = os.path.join(args.out, "context-pack.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_context_pack(bundle))

    firm = sum(
        is_firm(it)
        for key, _ in SECTIONS
        for it in (bundle.get(key) or [])
    )
    tentative = sum(
        not is_firm(it)
        for key, _ in SECTIONS
        for it in (bundle.get(key) or [])
    )
    print(f"Workspace: {bundle['workspace']['name']} ({workspace_id})")
    print(f"Conversations: {bundle['workspace']['session_count']}")
    print(f"FIRM (confirmed) items: {firm}")
    print(f"TENTATIVE (unconfirmed) items: {tentative}")
    print(f"Open questions: {len(bundle.get('open_questions') or [])}")
    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    main()
