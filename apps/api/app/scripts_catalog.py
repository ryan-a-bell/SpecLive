"""Pre-canned discovery-script catalogue.

Loads the shareable starter scripts under ``fixtures/scripts/`` into the
``script_definitions`` catalogue so a facilitator can pick a script for a
session without seeding the full demo. Idempotent — safe to run on every
startup: an existing script is updated in place and its stages replaced, so
edits to a fixture propagate on the next boot.
"""

from __future__ import annotations

import json
from pathlib import Path

from .database import SessionLocal, create_all
from .db import models as m
from .logging import get_logger

logger = get_logger(__name__)


def _catalogue_dir() -> Path:
    """Locate the ``fixtures/scripts`` directory (repo-root or container)."""

    relative = Path("fixtures/scripts")
    for parent in Path(__file__).resolve().parents:
        candidate = parent / relative
        if candidate.is_dir():
            return candidate
    return Path("/fixtures/scripts")


def load_catalogue_scripts() -> list[dict]:
    """Read every ``*.json`` starter script, sorted for deterministic order."""

    directory = _catalogue_dir()
    if not directory.is_dir():
        return []
    scripts: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            scripts.append(json.load(fh))
    return scripts


def _upsert_script(db: object, script: dict) -> None:
    existing = db.get(m.ScriptDefinitionORM, script["id"])  # type: ignore[attr-defined]
    if existing is None:
        existing = m.ScriptDefinitionORM(id=script["id"])
        db.add(existing)  # type: ignore[attr-defined]
    existing.name = script["name"]
    existing.version = script["version"]
    existing.description = script["description"]
    # Replace stages wholesale (delete-orphan cascade removes the old rows).
    existing.stages = [
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
        for stage in script["stages"]
    ]


def seed_catalogue(*, create_tables: bool = False) -> int:
    """Upsert all starter scripts. Returns the number loaded."""

    if create_tables:
        create_all()
    scripts = load_catalogue_scripts()
    if not scripts:
        logger.info("catalogue.empty", directory=str(_catalogue_dir()))
        return 0
    with SessionLocal() as db:
        for script in scripts:
            _upsert_script(db, script)
        db.commit()
    logger.info("catalogue.seeded", count=len(scripts), ids=[s["id"] for s in scripts])
    return len(scripts)
