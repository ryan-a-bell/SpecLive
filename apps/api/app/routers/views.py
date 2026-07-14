"""Read-model endpoints: discovery tree, conversation graph, coverage matrix."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    BranchCreate,
    BranchRead,
    ConversationGraph,
    CoverageMatrix,
    DiscoveryTree,
)
from app.services import branch_service, coverage_service, tree_service

router = APIRouter(prefix="/api/v1/sessions", tags=["views"])


@router.get("/{session_id}/discovery-tree", response_model=DiscoveryTree)
def discovery_tree(session_id: str, db: Session = Depends(get_db)) -> DiscoveryTree:
    return tree_service.build_tree(db, session_id)


@router.get("/{session_id}/conversation-graph", response_model=ConversationGraph)
def conversation_graph(session_id: str, db: Session = Depends(get_db)) -> ConversationGraph:
    return branch_service.build_graph(db, session_id)


@router.post("/{session_id}/branches", response_model=BranchRead, status_code=201)
async def create_branch(
    session_id: str, payload: BranchCreate, db: Session = Depends(get_db)
) -> BranchRead:
    branch = await branch_service.create_branch(db, session_id, payload)
    return BranchRead.model_validate(branch)


@router.get("/{session_id}/coverage", response_model=CoverageMatrix)
def coverage(session_id: str, db: Session = Depends(get_db)) -> CoverageMatrix:
    return coverage_service.build_matrix(db, session_id)
