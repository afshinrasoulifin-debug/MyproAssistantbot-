
"""
Tests for TITANIUM header entropy (L1 security layer).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium.header_entropy import build_decoy_headers

def test_always_has_accept_language():
    """Every header set must include Accept-Language."""
    for _ in range(100):
        headers = build_decoy_headers()
        assert "Accept-Language" in headers, "Missing Accept-Language"

def test_always_has_accept_encoding():
    """Every header set must include Accept-Encoding."""
    for _ in range(100):
        headers = build_decoy_headers()
        assert "Accept-Encoding" in headers, "Missing Accept-Encoding"

def test_always_has_connection():
    """Every header set must include Connection."""
    for _ in range(100):
        headers = build_decoy_headers()
        assert "Connection" in headers, "Missing Connection"

def test_entropy_varies():
    """Headers should vary between calls."""
    samples = [str(build_decoy_headers()) for _ in range(50)]
    unique = len(set(samples))
    assert unique > 30, f"Low entropy: only {unique}/50 unique header sets"

def test_user_agent_rotation():
    """User-Agent should rotate across calls."""
    uas = set()
    for _ in range(200):
        h = build_decoy_headers()
        if "User-Agent" in h:
            uas.add(h["User-Agent"])
    assert len(uas) > 5, f"Low UA rotation: only {len(uas)} unique UAs"

def test_sec_ch_ua_present():
    """Sec-Ch-Ua should appear in most requests."""
    count = 0
    for _ in range(200):
        h = build_decoy_headers()
        if "Sec-Ch-Ua" in h:
            count += 1
    assert count > 100, f"Sec-Ch-Ua only in {count}/200 requests"

def test_no_invalid_headers():
    """All header values should be non-empty strings."""
    for _ in range(100):
        for key, val in build_decoy_headers().items():
            assert isinstance(key, str) and len(key) > 0
            assert isinstance(val, str) and len(val) > 0

if __name__ == "__main__":
    test_always_has_accept_language()
    test_always_has_accept_encoding()
    test_always_has_connection()
    test_entropy_varies()
    test_user_agent_rotation()
    test_sec_ch_ua_present()
    test_no_invalid_headers()
    print("✅ All header entropy tests passed")


