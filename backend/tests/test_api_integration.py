import pytest
fastapi = pytest.importorskip("fastapi")
import asyncio
import json

from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import API_KEYS


def _headers():
    key = next(iter(API_KEYS)) if API_KEYS else "dev-key"
    return {"x-api-key": key}


def test_health_and_metrics_endpoints():
    client = TestClient(app)
    assert client.get('/healthz').status_code == 200
    m = client.get('/metrics')
    assert m.status_code == 200
    assert 'counters' in m.json()


def test_stream_endpoint_sse_contract():
    client = TestClient(app)
    payload = {"prefix": "def a():\n    ", "suffix": "\n", "language": "python", "user_id": "u1"}
    with client.stream('POST', '/v1/completions/stream', json=payload, headers=_headers()) as resp:
        assert resp.status_code == 200
        body = ''.join([chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in resp.iter_raw()])
    assert 'event: token' in body
    assert 'event: done' in body


def test_rate_limit_path():
    client = TestClient(app)
    payload = {"prefix": "x", "suffix": "", "language": "python", "user_id": "flood", "tenant_id": "t1"}
    status_codes = []
    for _ in range(70):
        r = client.post('/v1/completions/stream', json=payload, headers=_headers())
        status_codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in status_codes
