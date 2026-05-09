from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass(slots=True)
class RequestMeta:
    request_id: str
    created_at: float
    user_id: str


class RequestLifecycleManager:
    def __init__(self) -> None:
        self._active: dict[str, RequestMeta] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def begin(self, request_id: str, user_id: str) -> None:
        self._active[request_id] = RequestMeta(request_id=request_id, created_at=time.time(), user_id=user_id)
        self._cancel_events[request_id] = asyncio.Event()

    def cancel(self, request_id: str) -> None:
        event = self._cancel_events.get(request_id)
        if event:
            event.set()

    def is_cancelled(self, request_id: str) -> bool:
        event = self._cancel_events.get(request_id)
        return bool(event and event.is_set())

    def end(self, request_id: str) -> None:
        self._active.pop(request_id, None)
        self._cancel_events.pop(request_id, None)


LIFECYCLE = RequestLifecycleManager()
