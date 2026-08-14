"""Version 1 API routers."""

from fastapi import APIRouter

from . import artifacts, scripts, sessions, stream

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(sessions.router)
api_router.include_router(artifacts.router)
api_router.include_router(scripts.router)
api_router.include_router(stream.router)

__all__ = ["api_router"]
