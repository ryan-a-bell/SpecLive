"""Conversation branch + node management and the conversation-graph projection.

The conversation graph models the scripted conversation as the main branch;
customer answers create side branches carrying follow-up questions, findings,
requirements, risks and decisions, which may merge back into a script stage.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..db import models as m
from ..domain import entities as e
from ..domain.enums import BranchStatus, ConversationNodeType
from ..domain.events import DomainEvent, EventType
from ..events import EventBus
from ..repositories import SessionRepository
from ..repositories.mappers import branch_to_domain, node_to_domain
from .errors import NotFoundError


class BranchService:
    def __init__(self, repo: SessionRepository, bus: EventBus) -> None:
        self._repo = repo
        self._bus = bus

    def create_branch(
        self,
        session_id: str,
        *,
        name: str,
        topic: str,
        source_stage_id: str | None = None,
        parent_branch_id: str | None = None,
        created_from_segment_id: str | None = None,
        merge_target_stage_id: str | None = None,
        status: BranchStatus = BranchStatus.OPEN,
        branch_id: str | None = None,
    ) -> e.ConversationBranch:
        if self._repo.get_session(session_id) is None:
            raise NotFoundError(f"Session {session_id} not found")
        row = m.ConversationBranchORM(
            id=branch_id or str(uuid4()),
            session_id=session_id,
            parent_branch_id=parent_branch_id,
            source_stage_id=source_stage_id,
            name=name,
            topic=topic,
            status=BranchStatus(status).value,
            created_from_segment_id=created_from_segment_id,
            merge_target_stage_id=merge_target_stage_id,
        )
        self._repo.add_branch(row)
        self._repo.commit()
        branch = branch_to_domain(row)
        self._bus.publish(
            DomainEvent(
                type=EventType.BRANCH_CREATED,
                session_id=session_id,
                payload=branch.model_dump(mode="json"),
            )
        )
        return branch

    def add_node(
        self,
        branch_id: str,
        *,
        node_type: ConversationNodeType,
        label: str,
        transcript_segment_id: str | None = None,
        artifact_id: str | None = None,
        parent_node_id: str | None = None,
        sequence: int | None = None,
        node_id: str | None = None,
    ) -> e.ConversationNode:
        branch = self._repo.get_branch(branch_id)
        if branch is None:
            raise NotFoundError(f"Branch {branch_id} not found")
        seq = sequence if sequence is not None else len(self._repo.list_nodes(branch_id))
        row = m.ConversationNodeORM(
            id=node_id or str(uuid4()),
            branch_id=branch_id,
            node_type=ConversationNodeType(node_type).value,
            label=label,
            transcript_segment_id=transcript_segment_id,
            artifact_id=artifact_id,
            parent_node_id=parent_node_id,
            sequence=seq,
        )
        self._repo.add_node(row)
        self._repo.commit()
        node = node_to_domain(row)
        self._bus.publish(
            DomainEvent(
                type=EventType.BRANCH_NODE_CREATED,
                session_id=branch.session_id,
                payload=node.model_dump(mode="json"),
            )
        )
        return node

    def merge_branch(self, branch_id: str, *, merge_target_stage_id: str) -> e.ConversationBranch:
        branch = self._repo.get_branch(branch_id)
        if branch is None:
            raise NotFoundError(f"Branch {branch_id} not found")
        branch.status = BranchStatus.MERGED.value
        branch.merge_target_stage_id = merge_target_stage_id
        # Record the merge as a terminal node on the branch.
        self.add_node(
            branch_id,
            node_type=ConversationNodeType.MERGE,
            label=f"Merged into stage {merge_target_stage_id}",
        )
        self._repo.commit()
        return branch_to_domain(branch)

    def graph(self, session_id: str) -> dict[str, Any]:
        """Conversation-graph projection used by the git-branch and subway views."""

        branches = self._repo.list_branches(session_id)
        return {
            "session_id": session_id,
            "branches": [
                {
                    **branch_to_domain(b).model_dump(mode="json"),
                    "nodes": [
                        node_to_domain(n).model_dump(mode="json")
                        for n in self._repo.list_nodes(b.id)
                    ],
                }
                for b in branches
            ],
        }
