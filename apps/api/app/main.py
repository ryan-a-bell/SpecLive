"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1 import api_router
from .config import get_settings
from .domain.lifecycle import InvalidTransition
from .logging import configure_logging, get_logger
from .services.errors import NotFoundError, ValidationError

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Requirements Discovery Copilot API",
        version="0.1.0",
        description=(
            "Derives customer needs, requirements, constraints, assumptions, risks, "
            "decisions and open questions from a live discovery conversation, with "
            "evidence-first traceability and human validation before baselining."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(InvalidTransition)
    async def _bad_transition(_: Request, exc: InvalidTransition) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # For the SQLite fallback (tests / keyless local runs) create tables if the
        # migration path was not used. Postgres deployments run Alembic instead.
        if settings.database_url.startswith("sqlite"):
            from .database import create_all

            create_all()
        logger.info("api.startup", environment=settings.environment)

    return app


app = create_app()
