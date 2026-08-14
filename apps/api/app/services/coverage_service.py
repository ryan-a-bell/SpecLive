"""Coverage matrix: discovery-script stages × conversation branches.

A cell's :class:`CoverageState` reflects how strongly a branch informs a stage.
For seeded/authored sessions an explicit coverage map may be supplied in session
metadata (``meta['coverage']``); otherwise the matrix is derived from artifacts,
their evidence, and validation state.
"""

from __future__ import annotations

from typing import Any

from ..domain.enums import ArtifactType, CoverageState, EvidenceRelationship, ValidationState
from ..domain.events import DomainEvent, EventType
from ..events import EventBus
from ..repositories import SessionRepository
from ..repositories.mappers import artifact_to_domain
from .errors import NotFoundError

# Which stage titles an artifact type most naturally informs (derivation fallback).
_TYPE_STAGE_AFFINITY: dict[ArtifactType, tuple[str, ...]] = {
    ArtifactType.OBJECTIVE: ("driver",),
    ArtifactType.STAKEHOLDER_NEED: ("current", "workflow"),
    ArtifactType.REQUIREMENT: ("workflow", "measures"),
    ArtifactType.SUCCESS_METRIC: ("measures",),
    ArtifactType.CONSTRAINT: ("environment", "constraints"),
    ArtifactType.INTEGRATION: ("environment", "constraints"),
    ArtifactType.RISK: ("constraints",),
    ArtifactType.OPEN_QUESTION: ("validation",),
}


class CoverageService:
    def __init__(self, repo: SessionRepository, bus: EventBus | None = None) -> None:
        self._repo = repo
        self._bus = bus

    def build(self, session_id: str) -> dict[str, Any]:
        session = self._repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")

        stages = self._stage_columns(session)
        branches = self._repo.list_branches(session_id)

        authored = (session.meta or {}).get("coverage")
        if authored:
            matrix = self._from_authored(authored, stages, branches)
        else:
            matrix = self._derive(session_id, stages, branches)

        summary = self._summarize(matrix)
        result = {
            "session_id": session_id,
            "stages": stages,
            "rows": matrix,
            "summary": summary,
        }
        if self._bus is not None:
            self._bus.publish(
                DomainEvent(
                    type=EventType.COVERAGE_UPDATED,
                    session_id=session_id,
                    payload={"summary": summary},
                )
            )
        return result

    # --- column source ----------------------------------------------------
    def _stage_columns(self, session) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
        if session.script_id:
            script = self._repo.get_script(session.script_id)
            if script is not None:
                return [
                    {"id": s.id, "title": s.title, "sequence": s.sequence} for s in script.stages
                ]
        return []

    # --- authored path ----------------------------------------------------
    def _from_authored(self, authored: dict, stages, branches) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
        rows: list[dict[str, Any]] = []
        for b in branches:
            cells = authored.get(b.topic) or authored.get(b.name) or {}
            rows.append(
                {
                    "branch_id": b.id,
                    "branch": b.name,
                    "topic": b.topic,
                    "cells": [self._authored_cell(cells, st) for st in stages],
                }
            )
        return rows

    @staticmethod
    def _authored_cell(cells: dict, stage: dict) -> dict[str, Any]:
        key = str(stage["sequence"])
        cell = cells.get(key) or cells.get(stage["title"].lower()) or {}
        return {
            "stage_id": stage["id"],
            "state": cell.get("state", CoverageState.UNANSWERED.value),
            "title": cell.get("title"),
            "meta": cell.get("meta"),
        }

    # --- derivation path --------------------------------------------------
    def _derive(self, session_id: str, stages, branches) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
        artifacts = [artifact_to_domain(r) for r in self._repo.list_artifacts(session_id)]
        evidence = self._repo.list_evidence(session_id)
        ev_by_artifact: dict[str, list] = {}
        for link in evidence:
            ev_by_artifact.setdefault(link.artifact_id, []).append(link)

        rows: list[dict[str, Any]] = []
        for b in branches:
            branch_artifacts = [a for a in artifacts if a.branch_id == b.id]
            cells = []
            for st in stages:
                cells.append(self._derive_cell(st, branch_artifacts, ev_by_artifact))
            rows.append(
                {
                    "branch_id": b.id,
                    "branch": b.name,
                    "topic": b.topic,
                    "cells": cells,
                }
            )
        return rows

    def _derive_cell(self, stage, branch_artifacts, ev_by_artifact) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        title_key = stage["title"].lower()
        relevant = [
            a
            for a in branch_artifacts
            if any(tok in title_key for tok in _TYPE_STAGE_AFFINITY.get(a.artifact_type, ()))
        ]
        state = CoverageState.UNANSWERED
        if relevant:
            has_contradiction = any(
                link.relationship_type == EvidenceRelationship.CONTRADICTING.value
                for a in relevant
                for link in ev_by_artifact.get(a.id, [])
            )
            confirmed = any(
                a.validation_state
                in (ValidationState.CUSTOMER_CONFIRMED, ValidationState.BASELINED)
                for a in relevant
            )
            has_evidence = any(ev_by_artifact.get(a.id) for a in relevant)
            only_questions = all(a.artifact_type == ArtifactType.OPEN_QUESTION for a in relevant)
            if has_contradiction:
                state = CoverageState.CONTRADICTORY
            elif confirmed:
                state = CoverageState.CONFIRMED
            elif only_questions:
                state = CoverageState.NEEDS_VALIDATION
            elif has_evidence:
                state = CoverageState.STRONG
            else:
                state = CoverageState.PARTIAL
        return {"stage_id": stage["id"], "state": state.value, "title": None, "meta": None}

    # --- summary ----------------------------------------------------------
    @staticmethod
    def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        total = 0
        answered = 0
        for row in rows:
            for cell in row["cells"]:
                total += 1
                state = cell["state"]
                counts[state] = counts.get(state, 0) + 1
                if state not in (CoverageState.UNANSWERED.value,):
                    answered += 1
        percent = round((answered / total) * 100) if total else 0
        return {"counts": counts, "total_cells": total, "coverage_percent": percent}
