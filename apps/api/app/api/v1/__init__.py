"""Version 1 API routers."""

from fastapi import APIRouter

from . import (
    artifacts,
    audio,
    meta,
    scripts,
    sessions,
    storage,
    stream,
    transcribe,
    workspaces,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(sessions.router)
api_router.include_router(workspaces.router)
api_router.include_router(artifacts.router)
api_router.include_router(scripts.router)
api_router.include_router(stream.router)
api_router.include_router(audio.router)
api_router.include_router(transcribe.router)
api_router.include_router(storage.router)
api_router.include_router(meta.router)

__all__ = ["api_router"]
