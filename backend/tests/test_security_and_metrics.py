from app.core.auth import validate_api_key
from app.core.rate_limit import TokenBucket
from app.observability.metrics import Metrics


def test_api_key_and_rate_limit_primitives():
    assert validate_api_key("dev-key") is True
    bucket = TokenBucket(capacity=1, refill_per_sec=0)
    assert bucket.allow() is True
    assert bucket.allow() is False


def test_metrics_snapshot():
    m = Metrics()
    m.inc("requests")
    m.observe("latency", 10)
    snap = m.snapshot()
    assert snap["counters"]["requests"] == 1
    assert snap["avg_ms"]["latency"] == 10
