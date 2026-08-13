"""WebSocket streaming of domain events for a session.

Clients connect to ``/api/v1/sessions/{session_id}/stream`` and receive JSON
event frames for: new transcript segments, candidate artifacts, evidence links,
discovery-tree changes, conversation-branch changes, and recommended questions.

The initial implementation is fed by mock/synchronous events published on the
in-process bus. The frame contract is transport-agnostic, so a real-time STT
pipeline can publish the same events without any client change.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...events import get_event_bus
from ...logging import get_logger

router = APIRouter(tags=["stream"])
logger = get_logger(__name__)


@router.websocket("/sessions/{session_id}/stream")
async def stream_events(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    bus = get_event_bus()

    async def _pump() -> None:
        async for event in bus.stream(session_id):
            await websocket.send_json(event.to_wire())

    pump_task = asyncio.create_task(_pump())
    try:
        # Keep the socket open; ignore inbound messages (client is a consumer).
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("stream.disconnected", session_id=session_id)
    finally:
        pump_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump_task
