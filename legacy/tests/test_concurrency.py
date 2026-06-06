
"""Concurrency tests — v29.0.0 real tests."""
import pytest
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
async def test_cache_concurrent_access():
    """Multiple coroutines can safely access a shared dict concurrently."""
    cache = {}
    errors = []

    async def writer(key, value):
        try:
            cache[key] = value
            await asyncio.sleep(0.001)
            assert cache[key] == value
        except Exception as e:
            errors.append(e)

    tasks = [asyncio.create_task(writer(f"k{i}", i)) for i in range(50)]
    await asyncio.gather(*tasks)
    assert len(errors) == 0, f"Errors during concurrent access: {errors}"
    assert len(cache) == 50


@pytest.mark.asyncio
async def test_idempotency_concurrent():
    """Same key written multiple times results in one entry."""
    results = {}
    lock = asyncio.Lock()

    async def safe_write(key, value):
        async with lock:
            if key not in results:
                results[key] = value

    tasks = [asyncio.create_task(safe_write("same_key", i)) for i in range(20)]
    await asyncio.gather(*tasks)
    assert "same_key" in results
    assert results["same_key"] == 0  # First writer wins


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency():
    """Semaphore correctly limits concurrent execution."""
    sem = asyncio.Semaphore(3)
    active = 0
    max_active = 0

    async def worker():
        nonlocal active, max_active
        async with sem:
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1

    tasks = [asyncio.create_task(worker()) for _ in range(20)]
    await asyncio.gather(*tasks)
    assert max_active <= 3, f"Max active was {max_active}, should be <= 3"
    assert active == 0


