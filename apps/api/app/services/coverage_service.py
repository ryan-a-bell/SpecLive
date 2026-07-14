"""Coverage matrix: discovery-script stages × conversation topics.

Live sessions get a computed baseline (does a branch on this topic have nodes
that reach this stage, and are its artifacts validated?). The seed scenario
provides an explicit override in session metadata so the demo matches the
prototype's richer, hand-authored coverage picture.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.enums import ArtifactStatus, CoverageState
from app.models import DiscoverySession
from app.schemas import (
    CoverageCell,
    CoverageGap,
    CoverageMatrix,
    ScriptStageRead,
)
from app.services import artifact_service, branch_service, script_service
from app.services.session_service import get_session


def _metadata(session: DiscoverySession) -> dict:
    try:
        return json.loads(session.session_metadata or "{}")
    except json.JSONDecodeError:
        return {}


def coverage_percent(db: Session, session_id: str) -> int:
    session = get_session(db, session_id)
    meta = _metadata(session)
    if "coverage_percent" in meta:
        return int(meta["coverage_percent"])

    artifacts = artifact_service.list_artifacts(db, session_id)
    scored = [
        a for a in artifacts
        if a.status not in {ArtifactStatus.REJECTED, ArtifactStatus.MERGED}
    ]
    if not scored:
        return 0
    confirmed = sum(
        1 for a in scored
        if a.status in {ArtifactStatus.CUSTOMER_CONFIRMED, ArtifactStatus.BASELINED}
    )
    state = script_service.get_state(db, session_id)
    stage_ratio = (
        len(state.completed_stages) / state.total_stages if state.total_stages else 0.0
    )
    artifact_ratio = confirmed / len(scored)
    return round(100 * (0.5 * stage_ratio + 0.5 * artifact_ratio))


def build_matrix(db: Session, session_id: str) -> CoverageMatrix:
    session = get_session(db, session_id)
    meta = _metadata(session)
    stages = _stages(db, session)
    stage_titles = [s.title for s in stages]

    branches = [b for b in branch_service.list_branches(db, session_id) if not b.is_main]
    topics = [b.name for b in branches]

    override = meta.get("coverage_cells")
    if override:
        cells = [CoverageCell(**c) for c in override]
    else:
        cells = _compute_cells(branches, stages)

    gaps = [CoverageGap(**g) for g in meta.get("coverage_gaps", [])]
    return CoverageMatrix(
        session_id=session_id,
        topics=topics or stage_titles,
        stages=stages,
        cells=cells,
        gaps=gaps,
        coverage_percent=coverage_percent(db, session_id),
    )


def _stages(db: Session, session: DiscoverySession) -> list[ScriptStageRead]:
    if not session.script_id:
        return []
    script = script_service.get_script(db, session.script_id)
    return [script_service.stage_to_read(s) for s in
            sorted(script.stages, key=lambda s: s.sequence)]


def _compute_cells(branches, stages) -> list[CoverageCell]:
    cells: list[CoverageCell] = []
    for branch in branches:
        # A branch contributes to the stage it sprang from and any it merges to.
        node_count = len(branch.nodes)
        for stage in stages:
            state = CoverageState.UNANSWERED
            title = ""
            if branch.source_stage_id == stage.id and node_count:
                state = CoverageState.STRONG
                title = "Primary evidence"
            elif branch.merge_target_stage_id == stage.id:
                state = CoverageState.PARTIAL
                title = "Pending merge"
            if state is not CoverageState.UNANSWERED:
                cells.append(
                    CoverageCell(
                        stage_sequence=stage.sequence,
                        topic=branch.name,
                        state=state,
                        title=title,
                    )
                )
    return cells
