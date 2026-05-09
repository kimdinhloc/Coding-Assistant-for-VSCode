from __future__ import annotations

import time


class TokenBucket:
    def __init__(self, capacity: int, refill_per_sec: float) -> None:
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.tokens = float(capacity)
        self.updated_at = time.time()

    def allow(self, cost: int = 1) -> bool:
        now = time.time()
        delta = now - self.updated_at
        self.updated_at = now
        self.tokens = min(float(self.capacity), self.tokens + delta * self.refill_per_sec)
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, user_id: str, cost: int = 1) -> bool:
        bucket = self._buckets.get(user_id)
        if bucket is None:
            bucket = TokenBucket(capacity=60, refill_per_sec=1.0)
            self._buckets[user_id] = bucket
        return bucket.allow(cost)


RATE_LIMITER = RateLimiter()
