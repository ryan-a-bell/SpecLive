"""Version 1 API routers."""

from fastapi import APIRouter

from . import artifacts, audio, scripts, sessions, stream, transcribe

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(sessions.router)
api_router.include_router(artifacts.router)
api_router.include_router(scripts.router)
api_router.include_router(stream.router)
api_router.include_router(audio.router)
api_router.include_router(transcribe.router)

__all__ = ["api_router"]
