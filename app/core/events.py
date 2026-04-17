import asyncio
from typing import AsyncGenerator


class EventBroadcaster:
    """In-process pub/sub for Server-Sent Events.

    Publishers call publish() with a structured payload. Each subscriber gets
    its own asyncio.Queue; subscribe() yields payload dicts for the caller to
    format into SSE frames. Rendering is deliberately left out of this module
    so domain code can stay presentation-agnostic.
    """

    def __init__(self, queue_maxsize: int = 100) -> None:
        self._subscribers: list[asyncio.Queue] = []
        self._queue_maxsize = queue_maxsize

    def publish(self, event_type: str, data: dict) -> None:
        payload = {"event": event_type, "data": data}
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._queue_maxsize)
        self._subscribers.append(q)
        try:
            yield {"event": "ready", "data": {}}
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield payload
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": None}
        finally:
            if q in self._subscribers:
                self._subscribers.remove(q)


broadcaster = EventBroadcaster()
