
"""Tests for query cache."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQueryCache:
    @pytest.mark.asyncio
    async def test_get_or_fetch(self):
        from arki_project.utils.query_cache import QueryCache
        cache = QueryCache()
        called = [0]
        async def fetcher():
            called[0] += 1
            return "result"
        r1 = await cache.get_or_fetch("key1", fetcher)
        assert r1 == "result"
        assert called[0] == 1
        r2 = await cache.get_or_fetch("key1", fetcher)
        assert r2 == "result"
        assert called[0] == 1  # Not called again

    def test_invalidate(self):
        from arki_project.utils.query_cache import QueryCache
        cache = QueryCache()
        cache._cache["test"] = ("value", 9999999999)
        cache.invalidate("test")
        assert "test" not in cache._cache

    def test_stats(self):
        from arki_project.utils.query_cache import QueryCache
        cache = QueryCache()
        stats = cache.stats
        assert "size" in stats
        assert "hit_rate" in stats


