
"""
Tests for TITANIUM crypto module (L1 security layer).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium.crypto import (
    csprng_int, csprng_float, csprng_choice,
    csprng_weighted_choice, secure_request_id,
    hmac_sign, hmac_verify,
)

def test_csprng_int_range():
    """CSPRNG int should stay within bounds."""
    for _ in range(1000):
        val = csprng_int(0, 10)
        assert 0 <= val <= 10, f"Out of range: {val}"
    # Edge case
    assert csprng_int(5, 5) == 5

def test_csprng_float_range():
    """CSPRNG float should be in [0, 1)."""
    for _ in range(500):
        val = csprng_float()
        assert 0.0 <= val < 1.0, f"Out of range: {val}"

def test_csprng_choice():
    """CSPRNG choice should pick from list."""
    items = ["a", "b", "c"]
    for _ in range(100):
        pick = csprng_choice(items)
        assert pick in items

def test_csprng_weighted_choice():
    """Weighted choice should respect weights."""
    items = ["heavy", "light"]
    weights = [100.0, 0.001]
    picks = [csprng_weighted_choice(items, weights) for _ in range(200)]
    # "heavy" should dominate
    heavy_count = picks.count("heavy")
    assert heavy_count > 150, f"heavy only picked {heavy_count}/200 times"

def test_secure_request_id():
    """Request IDs should be unique and have correct format."""
    ids = set()
    for _ in range(100):
        rid = secure_request_id()
        assert rid.startswith("T-"), f"Bad prefix: {rid}"
        assert len(rid) > 10
        ids.add(rid)
    assert len(ids) == 100, "Duplicate request IDs detected"

def test_hmac_sign_verify():
    """HMAC sign/verify should work correctly."""
    data = "test message"
    key = "secret_key_123"
    signature = hmac_sign(data, key)
    assert hmac_verify(data, key, signature), "Valid signature rejected"
    assert not hmac_verify(data, "wrong_key", signature), "Wrong key accepted"
    assert not hmac_verify("wrong data", key, signature), "Wrong data accepted"

if __name__ == "__main__":
    test_csprng_int_range()
    test_csprng_float_range()
    test_csprng_choice()
    test_csprng_weighted_choice()
    test_secure_request_id()
    test_hmac_sign_verify()
    print("✅ All crypto tests passed")


