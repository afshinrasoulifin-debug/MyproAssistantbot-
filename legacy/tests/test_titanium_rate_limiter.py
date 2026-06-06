
"""
Tests for TITANIUM rate limiter (L5 — unlimited mode).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium.rate_limiter import TitaniumRateLimiter

def test_unlimited_mode():
    """Default mode should NEVER block."""
    limiter = TitaniumRateLimiter()
    assert limiter.max_requests == 0, "Should be unlimited by default"
    # Simulate 500 rapid requests
    for i in range(500):
        assert limiter.check(f"user:{i % 10}") is True, f"Blocked at request {i}"

def test_throughput_tracking():
    """Throughput should be tracked even in unlimited mode."""
    limiter = TitaniumRateLimiter()
    for _ in range(50):
        limiter.check("user:1")
    assert limiter.throughput("user:1") == 50

def test_remaining_unlimited():
    """Remaining should return 999999 in unlimited mode."""
    limiter = TitaniumRateLimiter()
    assert limiter.remaining("user:1") == 999999

def test_abuse_protection():
    """Should block at abuse threshold (1000/min)."""
    limiter = TitaniumRateLimiter(abuse_threshold=10)  # low threshold for test
    for i in range(10):
        limiter.check("abuser")
    # 11th should be blocked
    assert limiter.check("abuser") is False, "Abuse not detected"

def test_limited_mode():
    """If max_requests > 0, should enforce limit."""
    limiter = TitaniumRateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert limiter.check("limited_user") is True
    assert limiter.check("limited_user") is False, "Limit not enforced"

def test_reset():
    """Reset should clear state."""
    limiter = TitaniumRateLimiter(max_requests=5)
    for _ in range(5):
        limiter.check("user:1")
    assert limiter.check("user:1") is False
    limiter.reset("user:1")
    assert limiter.check("user:1") is True

def test_stats():
    """Stats should report correctly."""
    limiter = TitaniumRateLimiter()
    for _ in range(10):
        limiter.check("user:1")
    stats = limiter.stats
    assert stats["mode"] == "unlimited"
    assert stats["total_checks"] == 10
    assert stats["total_blocked"] == 0

if __name__ == "__main__":
    test_unlimited_mode()
    test_throughput_tracking()
    test_remaining_unlimited()
    test_abuse_protection()
    test_limited_mode()
    test_reset()
    test_stats()
    print("✅ All rate limiter tests passed")


