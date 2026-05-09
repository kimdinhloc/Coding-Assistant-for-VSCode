from __future__ import annotations

import json
import time


def log_event(event: str, **fields):
    payload = {"event": event, "ts": time.time(), **fields}
    print(json.dumps(payload, ensure_ascii=False))
