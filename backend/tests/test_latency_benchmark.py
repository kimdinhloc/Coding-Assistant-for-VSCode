import pytest
fastapi = pytest.importorskip("fastapi")
import time
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import API_KEYS


def test_first_token_latency_budget_dev():
    client = TestClient(app)
    key = next(iter(API_KEYS)) if API_KEYS else 'dev-key'
    payload = {"prefix": "def add(a,b):\n    ", "suffix": "", "language": "python", "user_id": "bench"}

    start = time.time()
    with client.stream('POST', '/v1/completions/stream', json=payload, headers={'x-api-key': key}) as resp:
        assert resp.status_code == 200
        first_token_time = None
        for raw in resp.iter_raw():
            chunk = raw.decode() if isinstance(raw, bytes) else raw
            if 'event: token' in chunk:
                first_token_time = (time.time() - start) * 1000
                break
    assert first_token_time is not None
    assert first_token_time < 1500  # dev budget relaxed; prod target tighter
