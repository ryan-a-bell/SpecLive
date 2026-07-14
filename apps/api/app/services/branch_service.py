from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import BranchStatus, NodeType
from app.errors import NotFoundError
from app.events import DomainEvent, EventType, get_event_bus
from app.ids import new_branch_id, new_node_id
from app.models import ConversationBranch, ConversationNode
from app.schemas import BranchCreate, ConversationGraph
from app.services import script_service
from app.services.session_service import get_session


def list_branches(db: Session, session_id: str) -> list[ConversationBranch]:
    get_session(db, session_id)
    return list(
        db.scalars(
            select(ConversationBranch)
            .where(ConversationBranch.session_id == session_id)
            .order_by(ConversationBranch.lane)
        )
    )


def get_branch(db: Session, branch_id: str) -> ConversationBranch:
    branch = db.get(ConversationBranch, branch_id)
    if branch is None:
        raise NotFoundError(f"Branch {branch_id} not found")
    return branch


def _next_lane(db: Session, session_id: str) -> int:
    current = db.scalar(
        select(func.max(ConversationBranch.lane)).where(
            ConversationBranch.session_id == session_id
        )
    )
    return (current or 0) + 1


async def create_branch(
    db: Session, session_id: str, data: BranchCreate, *, is_main: bool = False, emit: bool = True
) -> ConversationBranch:
    get_session(db, session_id)
    branch = ConversationBranch(
        id=new_branch_id(),
        session_id=session_id,
        parent_branch_id=data.parent_branch_id,
        source_stage_id=data.source_stage_id,
        name=data.name,
        topic=data.topic,
        status=BranchStatus.OPEN if not is_main else BranchStatus.ACTIVE,
        is_main=is_main,
        created_from_segment_id=data.created_from_segment_id,
        merge_target_stage_id=data.merge_target_stage_id,
        lane=0 if is_main else _next_lane(db, session_id),
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    if emit:
        await get_event_bus().publish(
            DomainEvent(
                type=EventType.BRANCH_CREATED,
                session_id=session_id,
                payload={"branch_id": branch.id, "name": branch.name},
            )
        )
    return branch


async def add_node(
    db: Session,
    branch_id: str,
    node_type: NodeType,
    label: str,
    *,
    transcript_segment_id: str | None = None,
    artifact_id: str | None = None,
    parent_node_id: str | None = None,
    emit: bool = True,
) -> ConversationNode:
    branch = get_branch(db, branch_id)
    sequence = db.scalar(
        select(func.count()).select_from(ConversationNode).where(
            ConversationNode.branch_id == branch_id
        )
    ) or 0
    node = ConversationNode(
        id=new_node_id(),
        branch_id=branch_id,
        node_type=node_type,
        label=label,
        transcript_segment_id=transcript_segment_id,
        artifact_id=artifact_id,
        parent_node_id=parent_node_id,
        sequence=sequence,
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    if emit:
        await get_event_bus().publish(
            DomainEvent(
                type=EventType.BRANCH_NODE_CREATED,
                session_id=branch.session_id,
                payload={"branch_id": branch_id, "node_id": node.id},
            )
        )
    return node


async def merge_branch(db: Session, branch_id: str, target_stage_id: str) -> ConversationBranch:
    branch = get_branch(db, branch_id)
    branch.status = BranchStatus.MERGED
    branch.merge_target_stage_id = target_stage_id
    db.commit()
    db.refresh(branch)
    return branch


def build_graph(db: Session, session_id: str) -> ConversationGraph:
    session = get_session(db, session_id)
    stages = []
    if session.script_id:
        script = script_service.get_script(db, session.script_id)
        stages = [script_service.stage_to_read(s) for s in
                  sorted(script.stages, key=lambda s: s.sequence)]
    return ConversationGraph(
        session_id=session_id,
        stages=stages,
        current_stage_sequence=session.current_stage_sequence,
        branches=list_branches(db, session_id),  # type: ignore[arg-type]
    )
