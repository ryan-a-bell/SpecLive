"""FastAPI dependencies that assemble services from the request-scoped session.

This is the composition root for the transport layer: it wires the repository,
event bus, and providers into each service. Nothing here contains business logic.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..events import EventBus, get_event_bus
from ..providers import get_llm_provider
from ..repositories import SqlAlchemySessionRepository
from ..services.analysis_service import AnalysisService
from ..services.artifact_service import ArtifactService
from ..services.branch_service import BranchService
from ..services.context_strategy import get_context_strategy
from ..services.conversation_graph_service import ConversationGraphService
from ..services.coverage_service import CoverageService
from ..services.export_service import ExportService
from ..services.recommendation_service import RecommendationService
from ..services.script_service import ScriptService
from ..services.session_service import SessionService
from ..services.storage_service import ConversationStorageService
from ..services.transcript_service import TranscriptService
from ..services.tree_service import TreeService
from ..services.workspace_service import WorkspaceService
from ..storage import get_content_store


@dataclass
class Services:
    sessions: SessionService
    transcript: TranscriptService
    artifacts: ArtifactService
    analysis: AnalysisService
    tree: TreeService
    branches: BranchService
    conversation_graph: ConversationGraphService
    scripts: ScriptService
    coverage: CoverageService
    recommendations: RecommendationService
    export: ExportService
    workspaces: WorkspaceService
    storage: ConversationStorageService


def get_services(db: Session = Depends(get_db)) -> Iterator[Services]:
    bus: EventBus = get_event_bus()
    repo = SqlAlchemySessionRepository(db)
    llm = get_llm_provider()
    artifacts = ArtifactService(repo, bus)
    settings = get_settings()
    context_strategy = get_context_strategy(
        settings.analysis_context_mode, window_seconds=settings.analysis_window_seconds
    )
    branches = BranchService(repo, bus)
    export = ExportService(repo)
    yield Services(
        sessions=SessionService(repo, bus),
        transcript=TranscriptService(repo, bus),
        artifacts=artifacts,
        analysis=AnalysisService(repo, artifacts, llm, context_strategy=context_strategy),
        tree=TreeService(repo),
        branches=branches,
        conversation_graph=ConversationGraphService(repo, branches),
        scripts=ScriptService(repo, bus),
        coverage=CoverageService(repo, bus),
        recommendations=RecommendationService(repo, llm),
        export=export,
        workspaces=WorkspaceService(repo, export),
        storage=ConversationStorageService(repo, export, get_content_store(), settings),
    )
