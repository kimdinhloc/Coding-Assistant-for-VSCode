from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass(order=True)
class QueueItem:
    priority: int
    request_id: str = field(compare=False)


class RequestQueue:
    def __init__(self, max_size: int = 2048) -> None:
        self._queue: asyncio.PriorityQueue[QueueItem] = asyncio.PriorityQueue(maxsize=max_size)

    async def put(self, request_id: str, priority: int = 10) -> None:
        await self._queue.put(QueueItem(priority=priority, request_id=request_id))

    async def get(self) -> QueueItem:
        return await self._queue.get()

    def size(self) -> int:
        return self._queue.qsize()


REQUEST_QUEUE = RequestQueue()
