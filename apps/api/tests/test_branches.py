"""Conversation branch creation, node addition, and merge."""

from __future__ import annotations

from app.domain.enums import BranchStatus, ConversationNodeType
from app.events import get_event_bus
from app.repositories import SqlAlchemySessionRepository
from app.services.branch_service import BranchService
from app.services.session_service import SessionService


def _setup(db):  # type: ignore[no-untyped-def]
    repo = SqlAlchemySessionRepository(db)
    bus = get_event_bus()
    sessions = SessionService(repo, bus)
    branches = BranchService(repo, bus)
    session = sessions.create(title="T", customer="Acme", facilitator="R")
    return branches, session.id


def test_create_branch_and_nodes(db) -> None:  # type: ignore[no-untyped-def]
    branches, session_id = _setup(db)
    branch = branches.create_branch(
        session_id, name="States", topic="states_exceptions", source_stage_id="STAGE-3"
    )
    assert branch.status is BranchStatus.OPEN
    branches.add_node(branch.id, node_type=ConversationNodeType.ANSWER, label="Delayed orders")
    branches.add_node(branch.id, node_type=ConversationNodeType.QUESTION, label="Which states?")
    graph = branches.graph(session_id)
    assert len(graph["branches"]) == 1
    assert len(graph["branches"][0]["nodes"]) == 2


def test_merge_branch_sets_status_and_adds_merge_node(db) -> None:  # type: ignore[no-untyped-def]
    branches, session_id = _setup(db)
    branch = branches.create_branch(session_id, name="WMS", topic="integration")
    branches.add_node(branch.id, node_type=ConversationNodeType.REQUIREMENT, label="Interface")
    merged = branches.merge_branch(branch.id, merge_target_stage_id="STAGE-6")
    assert merged.status is BranchStatus.MERGED
    assert merged.merge_target_stage_id == "STAGE-6"
    nodes = branches.graph(session_id)["branches"][0]["nodes"]
    assert nodes[-1]["node_type"] == "merge"
