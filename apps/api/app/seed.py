"""Seed the warehouse-modernization demonstration session.

Usage:
    python -m app.seed             # (re)seed, replacing any existing demo session
    python -m app.seed --if-empty  # seed only if the demo session is absent

Evidence character offsets are computed from the quoted text so the fixture
stays readable and robust to small edits.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from .database import SessionLocal, create_all
from .db import models as m
from .logging import configure_logging, get_logger

logger = get_logger(__name__)


def _fixture_path() -> Path:
    """Locate the seed fixture.

    Order: ``FIXTURE_PATH`` env var → repo-root ``fixtures/`` (local dev) →
    ``/fixtures`` (container). The first existing path wins.
    """

    env = os.getenv("FIXTURE_PATH")
    fixture_name = Path("fixtures/warehouse_modernization.json")
    module_path = Path(__file__).resolve()
    candidates = [Path(env)] if env else []
    candidates.extend(parent / fixture_name for parent in module_path.parents)
    candidates.append(Path("/fixtures/warehouse_modernization.json"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Preserve a useful, stable path in the eventual FileNotFoundError.
    return module_path.parent / fixture_name


FIXTURE_PATH = _fixture_path()


def _load_fixture() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _now() -> datetime:
    return datetime.now(UTC)


def seed(*, if_empty: bool = False) -> str:
    create_all()

    # Always make the pre-canned starter scripts available in the catalogue.
    from .scripts_catalog import seed_catalogue

    seed_catalogue()

    data = _load_fixture()
    session_id = data["session"]["id"]

    with SessionLocal() as db:
        existing = db.get(m.DiscoverySessionORM, session_id)
        if existing is not None:
            if if_empty:
                logger.info("seed.skipped", reason="session_exists", session_id=session_id)
                return session_id
            db.delete(existing)  # cascade removes children
            db.flush()

        # Script (shared catalogue entry) — upsert.
        if db.get(m.ScriptDefinitionORM, data["script"]["id"]) is None:
            script = data["script"]
            db.add(
                m.ScriptDefinitionORM(
                    id=script["id"],
                    name=script["name"],
                    version=script["version"],
                    description=script["description"],
                )
            )
            for stage in script["stages"]:
                db.add(
                    m.ScriptStageORM(
                        id=stage["id"],
                        script_id=script["id"],
                        sequence=stage["sequence"],
                        title=stage["title"],
                        objective=stage["objective"],
                        primary_prompt=stage["primary_prompt"],
                        alternative_prompts=stage.get("alternative_prompts", []),
                        completion_criteria=stage.get("completion_criteria", []),
                    )
                )

        # Session (fold the authored coverage map into metadata).
        s = data["session"]
        meta = dict(s.get("metadata", {}))
        meta["coverage"] = data.get("coverage", {})
        db.add(
            m.DiscoverySessionORM(
                id=s["id"],
                title=s["title"],
                customer=s["customer"],
                facilitator=s["facilitator"],
                status=s["status"],
                script_id=s.get("script_id"),
                started_at=_now(),
                meta=meta,
            )
        )

        # Transcript.
        segments_by_id: dict[str, str] = {}
        for seg in data["segments"]:
            db.add(
                m.TranscriptSegmentORM(
                    id=seg["id"],
                    session_id=session_id,
                    sequence_number=seg["sequence_number"],
                    speaker=seg["speaker"],
                    start_time=seg.get("start_time"),
                    end_time=seg.get("end_time"),
                    text=seg["text"],
                    is_final=True,
                )
            )
            segments_by_id[seg["id"]] = seg["text"]

        # Artifacts.
        from .domain.enums import ValidationState
        from .domain.lifecycle import status_for  # local import to avoid cycles

        for art in data["artifacts"]:
            state = ValidationState(art["validation_state"])
            db.add(
                m.DiscoveryArtifactORM(
                    id=art["id"],
                    session_id=session_id,
                    artifact_type=art["artifact_type"],
                    title=art["title"],
                    statement=art["statement"],
                    status=status_for(state).value,
                    confidence=art["confidence"],
                    validation_state=state.value,
                    derivation_method=art.get("derivation_method", "manual"),
                    parent_id=art.get("parent_id"),
                    branch_id=art.get("branch_id"),
                    rationale=art.get("rationale"),
                )
            )

        # Evidence — compute offsets from quoted text.
        for i, ev in enumerate(data["evidence"]):
            text = segments_by_id.get(ev["segment_id"], "")
            start = text.find(ev["quoted_text"])
            if start < 0:
                start, end = 0, len(ev["quoted_text"])
            else:
                end = start + len(ev["quoted_text"])
            db.add(
                m.EvidenceLinkORM(
                    id=f"EV-{i + 1:03d}",
                    artifact_id=ev["artifact_id"],
                    transcript_segment_id=ev["segment_id"],
                    quote_start=start,
                    quote_end=end,
                    quoted_text=ev["quoted_text"],
                    relationship_type=ev.get("relationship", "supporting"),
                    confidence=ev.get("confidence", 0.0),
                    rationale=ev.get("rationale"),
                )
            )

        # Branches + nodes.
        for br in data["branches"]:
            db.add(
                m.ConversationBranchORM(
                    id=br["id"],
                    session_id=session_id,
                    parent_branch_id=br.get("parent_branch_id"),
                    source_stage_id=br.get("source_stage_id"),
                    name=br["name"],
                    topic=br["topic"],
                    status=br["status"],
                    created_from_segment_id=br.get("created_from_segment_id"),
                    merge_target_stage_id=br.get("merge_target_stage_id"),
                )
            )
        for i, node in enumerate(data["nodes"]):
            db.add(
                m.ConversationNodeORM(
                    id=f"NODE-{i + 1:03d}",
                    branch_id=node["branch_id"],
                    node_type=node["node_type"],
                    label=node["label"],
                    transcript_segment_id=node.get("transcript_segment_id"),
                    artifact_id=node.get("artifact_id"),
                    parent_node_id=node.get("parent_node_id"),
                    sequence=node.get("sequence", i),
                )
            )

        db.commit()

    logger.info("seed.completed", session_id=session_id)
    return session_id


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Seed the demonstration session")
    parser.add_argument("--if-empty", action="store_true", help="Seed only if absent")
    args = parser.parse_args()
    session_id = seed(if_empty=args.if_empty)
    print(f"Seeded session: {session_id}")


if __name__ == "__main__":
    main()
    sys.exit(0)
