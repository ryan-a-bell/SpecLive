"""EventBus interface and an in-memory implementation.

The interface is intentionally minimal so a Redis/queue-backed implementation
can be dropped in without touching services. `subscribe` yields events for a
single session, which the websocket layer consumes.
"""

from __future__ import annotations

import abc
import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Callable

from ..domain.events import DomainEvent
from ..logging import get_logger

logger = get_logger(__name__)

Handler = Callable[[DomainEvent], None]


class EventBus(abc.ABC):
    """Publish/subscribe contract for domain events.

    ``publish`` is synchronous so services (which run in a synchronous request
    handler / DB transaction) can emit without ``await``. A future queue-backed
    implementation may enqueue synchronously and deliver asynchronously; the
    contract does not change.
    """

    @abc.abstractmethod
    def publish(self, event: DomainEvent) -> None: ...

    @abc.abstractmethod
    def subscribe_sync(self, handler: Handler) -> Callable[[], None]:
        """Register a synchronous handler. Returns an unsubscribe callable."""

    @abc.abstractmethod
    def stream(self, session_id: str) -> AsyncIterator[DomainEvent]:
        """Async iterator of events for a single session (for websockets)."""


class InMemoryEventBus(EventBus):
    """Process-local bus. Synchronous handlers fire inline; async subscribers
    receive events through per-subscriber queues."""

    def __init__(self) -> None:
        self._handlers: list[Handler] = []
        self._queues: dict[str, list[asyncio.Queue[DomainEvent]]] = defaultdict(list)
        self._history: dict[str, list[DomainEvent]] = defaultdict(list)

    def publish(self, event: DomainEvent) -> None:
        logger.info("event.published", type=event.type.value, session_id=event.session_id)
        self._history[event.session_id].append(event)
        for handler in list(self._handlers):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - a bad handler must not break publish
                logger.exception("event.handler_failed", type=event.type.value)
        for queue in list(self._queues.get(event.session_id, [])):
            queue.put_nowait(event)

    def subscribe_sync(self, handler: Handler) -> Callable[[], None]:
        self._handlers.append(handler)

        def _unsub() -> None:
            if handler in self._handlers:
                self._handlers.remove(handler)

        return _unsub

    async def stream(self, session_id: str) -> AsyncIterator[DomainEvent]:
        queue: asyncio.Queue[DomainEvent] = asyncio.Queue()
        self._queues[session_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._queues[session_id].remove(queue)

    def history(self, session_id: str) -> list[DomainEvent]:
        """Events already published for a session (used by tests and replay)."""

        return list(self._history.get(session_id, []))


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the process-wide event bus.

    Selection is by configuration; only the in-memory implementation ships in
    this increment. A Redis implementation would be constructed here when
    ``settings.event_bus == "redis"``.
    """

    global _bus
    if _bus is None:
        _bus = InMemoryEventBus()
    return _bus
