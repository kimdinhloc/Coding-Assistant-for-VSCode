from __future__ import annotations

import time


class Metrics:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.timers: dict[str, list[float]] = {}

    def inc(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def observe(self, name: str, value: float) -> None:
        self.timers.setdefault(name, []).append(value)

    def snapshot(self) -> dict:
        avg = {k: (sum(v) / len(v) if v else 0.0) for k, v in self.timers.items()}
        return {"counters": self.counters, "avg_ms": avg, "timestamp": int(time.time())}


METRICS = Metrics()
