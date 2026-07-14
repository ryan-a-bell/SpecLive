"""WebSocket connection manager bridged to the internal event bus.

Every domain event for a session is fanned out to that session's connected
clients as JSON. This is the real-time channel behind the live transcript,
tree updates, evidence links, branch changes, and recommended questions.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket

from app.events import DomainEvent, EventBus
from app.logging import get_logger

logger = get_logger("streaming")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[session_id].add(ws)
        logger.info("ws.connected", session_id=session_id)

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        self._connections[session_id].discard(ws)
        logger.info("ws.disconnected", session_id=session_id)

    async def broadcast(self, event: DomainEvent) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(event.session_id, set())):
            try:
                await ws.send_json(event.to_dict())
            except Exception:  # noqa: BLE001 - drop broken sockets
                dead.append(ws)
        for ws in dead:
            self.disconnect(event.session_id, ws)


manager = ConnectionManager()


def register(bus: EventBus) -> None:
    """Wire the manager into the bus so every event reaches WS clients."""
    bus.subscribe_all(manager.broadcast)
