"""Workspace-level aggregation of discovery context for external consumers.

A *workspace* groups the discovery conversations (sessions) that share a
customer. There is no separate workspace entity yet — it is derived from the
sessions list, mirroring the web app's client-side grouping
(``apps/web/lib/workspaces.ts``) so a workspace id means the same thing on
both sides.

This service rolls every session's discovery package up into one context
bundle that an external tool (or an LLM in another app) can pull to architect
against the requirements gathered in SpecLive. The ``scope`` knob decides
whether the bundle is limited to human-confirmed items (``baseline``) or also
includes still-unconfirmed candidates (``all``); every item stays tagged with
the session it came from and keeps its traceability to source evidence.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from ..domain.enums import ContextScope
from ..repositories import SessionRepository
from ..repositories.mappers import session_to_domain
from .errors import NotFoundError
from .export_service import ExportService

# Section keys in a per-session package that hold lists of artifact briefs.
# When merged into a workspace bundle each item is tagged with its source
# session so a consumer can trace it back.
_ITEM_SECTIONS = (
    "objectives",
    "stakeholder_needs",
    "confirmed_requirements",
    "candidate_requirements",
    "constraints",
    "assumptions",
    "risks",
    "decisions",
    "open_questions",
    "success_metrics",
)

_SECTION_LABELS = {
    "objectives": "Customer objectives",
    "stakeholder_needs": "Stakeholder needs",
    "confirmed_requirements": "Confirmed requirements",
    "candidate_requirements": "Candidate requirements",
    "constraints": "Constraints",
    "assumptions": "Assumptions",
    "risks": "Risks",
    "decisions": "Decisions",
    "open_questions": "Open questions",
    "success_metrics": "Success metrics",
}


def slugify_customer(customer: str) -> str:
    """Slug a customer name into a workspace id.

    Mirrors ``slugifyCustomer`` in ``apps/web/lib/workspaces.ts`` so ids line
    up across the web app and the API.
    """

    slug = re.sub(r"[^a-z0-9]+", "-", customer.lower().strip())
    slug = re.sub(r"^-+|-+$", "", slug)
    return slug or "workspace"


class WorkspaceService:
    def __init__(self, repo: SessionRepository, export_service: ExportService) -> None:
        self._repo = repo
        self._export = export_service

    # --- grouping ---------------------------------------------------------
    def _grouped(self) -> list[tuple[str, str, list]]:
        """Return ``(id, name, sessions)`` per workspace.

        Sessions are grouped by their exact (trimmed) customer name and sorted
        alphabetically; slug collisions across distinct names get a numeric
        suffix. This matches ``groupWorkspaces`` on the web side.
        """

        sessions = [session_to_domain(r) for r in self._repo.list_sessions()]
        by_customer: dict[str, list] = {}
        for session in sessions:
            by_customer.setdefault(session.customer.strip(), []).append(session)

        grouped: list[tuple[str, str, list]] = []
        used: set[str] = set()
        for name in sorted(by_customer):
            base = slugify_customer(name)
            workspace_id = base
            suffix = 2
            while workspace_id in used:
                workspace_id = f"{base}-{suffix}"
                suffix += 1
            used.add(workspace_id)
            grouped.append((workspace_id, name, by_customer[name]))
        return grouped

    def _resolve(self, workspace_id: str) -> tuple[str, list]:
        for wid, name, sessions in self._grouped():
            if wid == workspace_id:
                return name, sessions
        raise NotFoundError(f"Workspace {workspace_id!r} not found")

    @staticmethod
    def _session_brief(session) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": session.id,
            "title": session.title,
            "customer": session.customer,
            "status": session.status.value,
        }

    # --- public API -------------------------------------------------------
    def list_workspaces(self) -> list[dict[str, Any]]:
        """Enumerate workspaces so an external tool can discover their ids."""

        return [
            {
                "id": wid,
                "name": name,
                "session_count": len(sessions),
                "sessions": [self._session_brief(s) for s in sessions],
            }
            for wid, name, sessions in self._grouped()
        ]

    def build_context(
        self, workspace_id: str, *, scope: ContextScope = ContextScope.ALL
    ) -> dict[str, Any]:
        """Aggregate every session's discovery package into one bundle."""

        name, sessions = self._resolve(workspace_id)

        merged: dict[str, list] = {key: [] for key in _ITEM_SECTIONS}
        traceability: list[dict] = []
        branch_summary: list[dict] = []
        per_session: list[dict] = []

        for session in sessions:
            package = self._export.build_package(session.id, scope=scope)
            source = {
                "source_session_id": session.id,
                "source_session_title": session.title,
            }
            for key in _ITEM_SECTIONS:
                merged[key].extend({**item, **source} for item in package[key])
            traceability.extend({**item, **source} for item in package["traceability"])
            branch_summary.extend({**item, **source} for item in package["branch_summary"])
            per_session.append(
                {**self._session_brief(session), "executive_summary": package["executive_summary"]}
            )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "workspace": {
                "id": workspace_id,
                "name": name,
                "session_count": len(sessions),
                "sessions": [self._session_brief(s) for s in sessions],
            },
            "scope": scope.value,
            "executive_summary": self._summary(name, scope, sessions, merged),
            **merged,
            "branch_summary": branch_summary,
            "traceability": traceability,
            "session_summaries": per_session,
        }

    # --- rendering --------------------------------------------------------
    @staticmethod
    def render_markdown(package: dict[str, Any]) -> str:
        ws = package["workspace"]
        lines: list[str] = []
        add = lines.append

        add(f"# Workspace Context — {ws['name']}")
        add("")
        add(f"- **Workspace:** `{ws['id']}`")
        add(f"- **Conversations:** {ws['session_count']}")
        add(f"- **Scope:** {package['scope']}")
        add(f"- **Generated:** {package['generated_at']}")
        add("")
        add("## Executive summary")
        add("")
        add(package["executive_summary"])
        add("")

        add("## Conversations")
        add("")
        for s in ws["sessions"]:
            add(f"- **{s['title']}** (`{s['id']}`) — status: {s['status']}")
        add("")

        for key in _ITEM_SECTIONS:
            WorkspaceService._section(add, _SECTION_LABELS[key], package[key])

        add("## Traceability appendix")
        add("")
        add(
            "| Artifact | Type | State | Confidence | Source session | Evidence (segment → quote) |"
        )
        add("|----------|------|-------|-----------|----------------|----------------------------|")
        for t in package["traceability"]:
            evidence = (
                "; ".join(
                    f"{e['segment_id'][:8]}… “{e['quoted_text']}” ({e['relationship']})"
                    for e in t["evidence"]
                )
                or "_none_"
            )
            add(
                f"| {t['title']} | {t['type']} | {t['validation_state']} "
                f"| {t['confidence']:.0%} | {t['source_session_title']} | {evidence} |"
            )
        add("")
        return "\n".join(lines)

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _section(add, heading: str, items: list[dict]) -> None:  # type: ignore[no-untyped-def]
        add(f"## {heading}")
        add("")
        if not items:
            add("_None recorded._")
            add("")
            return
        for it in items:
            conf = it.get("confidence")
            suffix = f" _(confidence {conf:.0%})_" if isinstance(conf, (int, float)) else ""
            source = it.get("source_session_title")
            origin = f" — _{source}_" if source else ""
            add(f"- **{it['title']}** — {it['statement']}{suffix}{origin}")
        add("")

    @staticmethod
    def _summary(name, scope, sessions, merged) -> str:  # type: ignore[no-untyped-def]
        confirmed = len(merged["confirmed_requirements"])
        candidate = len(merged["candidate_requirements"])
        n_open = len(merged["open_questions"])
        scope_note = (
            "Only human-confirmed items are included (baseline scope)."
            if scope is ContextScope.BASELINE
            else (
                "Includes candidate items not yet human-confirmed; weigh each "
                "by its validation_state and confidence."
            )
        )
        return (
            f"Aggregated discovery context for {name} across {len(sessions)} "
            f"conversation(s): {confirmed} confirmed and {candidate} candidate "
            f"requirement(s), with {n_open} open question(s). Every item retains "
            f"traceability to its source transcript evidence and is tagged with the "
            f"session it came from. {scope_note} Requirements are aggregated across "
            f"sessions, not de-duplicated."
        )
