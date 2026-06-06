
"""
Tests for TITANIUM integration helpers (shielded_get/post/request).
"""
import os
import sys
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium.integration import (
    shielded_get, shielded_post, shielded_request,
    get_secure_random,
)


def test_get_secure_random():
    """get_secure_random should return values in [0, 1)."""
    for _ in range(100):
        val = get_secure_random()
        assert 0.0 <= val < 1.0


async def _test_shielded_get():
    """shielded_get should return a ShieldedResponse."""
    # Against a known good URL that doesn't need network
    # (just testing the interface, not actual HTTP)
    resp = await shielded_get("http://127.0.0.1:1/nonexistent", timeout=0.5)
    assert hasattr(resp, 'success')
    assert hasattr(resp, 'status')
    assert hasattr(resp, 'text')
    # Expected to fail since nothing listens on port 1
    assert resp.success is False


async def _test_shielded_post():
    """shielded_post should return a ShieldedResponse."""
    resp = await shielded_post(
        "http://127.0.0.1:1/nonexistent",
        json_data={"test": True},
        timeout=0.5,
    )
    assert hasattr(resp, 'success')
    assert resp.success is False


async def _test_shielded_request():
    """shielded_request should support arbitrary methods."""
    resp = await shielded_request(
        "PUT", "http://127.0.0.1:1/nonexistent",
        timeout=0.5,
    )
    assert hasattr(resp, 'success')
    assert resp.success is False


def test_shielded_get():
    asyncio.run(_test_shielded_get())

def test_shielded_post():
    asyncio.run(_test_shielded_post())

def test_shielded_request():
    asyncio.run(_test_shielded_request())


if __name__ == "__main__":
    test_get_secure_random()
    test_shielded_get()
    test_shielded_post()
    test_shielded_request()
    print("✅ All integration tests passed")


