
"""
Tests for TITANIUM ShieldedClient (L1-L7 security).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium.shielded_client import (
    ShieldedClientPool, ShieldedResponse,
    CircuitBreaker, RequestDeduplicator,
    get_shielded_pool,
)


def test_circuit_breaker_initial():
    """Circuit breaker starts closed."""
    cb = CircuitBreaker(failure_threshold=3)
    assert not cb.is_open("test.com")

def test_circuit_breaker_opens():
    """Circuit breaker opens after N failures."""
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=10.0)
    for _ in range(3):
        cb.record_failure("bad.com")
    assert cb.is_open("bad.com"), "Circuit should be open"
    # Other hosts should be fine
    assert not cb.is_open("good.com")

def test_circuit_breaker_success_resets():
    """Success resets failure count."""
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure("test.com")
    cb.record_failure("test.com")
    cb.record_success("test.com")
    cb.record_failure("test.com")
    assert not cb.is_open("test.com"), "Should not open — success reset count"

def test_deduplicator():
    """Deduplicator should detect duplicate requests."""
    dd = RequestDeduplicator(window_ms=1000)
    # First request: no pending
    assert dd.get_pending("GET", "http://x.com/a", None) is None
    # Set pending
    fut = dd.set_pending("GET", "http://x.com/a", None)
    assert fut is not None
    # Second identical request: should find pending
    assert dd.get_pending("GET", "http://x.com/a", None) is not None
    # Different URL: no pending
    assert dd.get_pending("GET", "http://x.com/b", None) is None

def test_shielded_response():
    """ShieldedResponse should parse JSON correctly."""
    resp = ShieldedResponse(status=200, text='{"key": "value"}', success=True)
    assert resp.json() == {"key": "value"}
    assert resp.success is True

def test_shielded_response_invalid_json():
    """ShieldedResponse.json() should return {} on invalid JSON."""
    resp = ShieldedResponse(status=200, text='not json', success=True)
    assert resp.json() == {}

def test_pool_singleton():
    """get_shielded_pool should return same instance."""
    pool1 = get_shielded_pool(200)
    pool2 = get_shielded_pool(200)
    assert pool1 is pool2

def test_pool_stats():
    """Pool stats should have required fields."""
    pool = get_shielded_pool()
    stats = pool.stats
    assert "requests" in stats
    assert "errors" in stats
    assert "max_connections" in stats
    assert stats["max_connections"] == 200

def test_pool_fingerprint_rotation():
    """Fingerprints should rotate."""
    pool = ShieldedClientPool()
    fps = set()
    for _ in range(100):
        fps.add(pool._pick_fingerprint())
    assert len(fps) > 2, f"Low fingerprint rotation: {fps}"

if __name__ == "__main__":
    test_circuit_breaker_initial()
    test_circuit_breaker_opens()
    test_circuit_breaker_success_resets()
    test_deduplicator()
    test_shielded_response()
    test_shielded_response_invalid_json()
    test_pool_singleton()
    test_pool_stats()
    test_pool_fingerprint_rotation()
    print("✅ All shielded client tests passed")


