from __future__ import annotations

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import DomainError
from app.events import get_event_bus
from app.logging import configure_logging, get_logger
from app.routers import analysis, artifacts, scripts, sessions, transcript, views
from app.streaming import manager, register

configure_logging()
logger = get_logger("app")

OPENAPI_TAGS = [
    {"name": "sessions", "description": "Create and manage discovery sessions."},
    {"name": "transcript", "description": "Stream and read transcript segments."},
    {"name": "artifacts", "description": "Discovery artifacts, evidence, and lifecycle actions."},
    {"name": "views", "description": "Discovery tree, conversation graph, coverage matrix."},
    {"name": "scripts", "description": "Discovery script catalog and session script state."},
    {"name": "analysis", "description": "Derivation and export."},
]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "API for the Requirements Discovery Copilot. Derives customer needs, "
            "requirements, constraints, risks, and follow-up questions from a live "
            "discovery conversation, with full evidence traceability."
        ),
        openapi_tags=OPENAPI_TAGS,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register(get_event_bus())

    for module in (sessions, transcript, views, scripts, analysis):
        app.include_router(module.router)
    app.include_router(artifacts.router)
    app.include_router(artifacts.session_router)
    app.include_router(scripts.session_router)

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/api/v1/sessions/{session_id}/stream")
    async def stream(websocket: WebSocket, session_id: str) -> None:
        await manager.connect(session_id, websocket)
        try:
            while True:
                # Clients are receive-only in this increment; keep the socket
                # open and drain any pings.
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(session_id, websocket)

    return app


app = create_app()
