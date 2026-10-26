"""In-process async event bus feeding the console.

Pattern (subscribe by type or "*", publish fans out) follows Nexus `runtime/events/bus.py`;
this is a fresh implementation with per-handler error isolation, unsubscribe and bounded history.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from .models import Column, EventEnvelope

log = logging.getLogger("sentinel.events")
Handler = Callable[[EventEnvelope], Awaitable[None]]


def make_event(type: str, session_id: str | None, column: Column | None,
               payload: dict[str, Any] | None = None) -> EventEnvelope:
    return EventEnvelope(type=type, session_id=session_id, column=column,
                         ts=datetime.now(timezone.utc), payload=payload or {})


class EventBus:
    def __init__(self, history: int = 500):
        self._subs: dict[int, tuple[str, Handler]] = {}
        self._next = 0
        self._history: deque[EventEnvelope] = deque(maxlen=history)

    def subscribe(self, handler: Handler, event_type: str = "*") -> Callable[[], None]:
        """Register a handler. Returns a function that removes it."""
        key = self._next
        self._next += 1
        self._subs[key] = (event_type, handler)
        return lambda: self._subs.pop(key, None) and None

    async def publish(self, event: EventEnvelope) -> None:
        self._history.append(event)
        handlers = [h for t, h in list(self._subs.values()) if t in ("*", event.type)]
        results = await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                log.warning("event handler failed for %s: %r", event.type, r)  # one bad console must not stop others

    def recent(self, n: int | None = None) -> list[EventEnvelope]:
        items = list(self._history)
        return items if n is None else items[-n:]
