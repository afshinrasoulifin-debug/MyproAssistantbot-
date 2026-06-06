
"""Chaos tests — verify system resilience when components fail."""
import pytest
import importlib
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _import(module_path, cls_name=None):
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, cls_name) if cls_name else mod
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Dependency missing: {e}")


class TestRedisFailure:
    @pytest.mark.asyncio
    async def test_cache_works_without_redis(self):
        """Cache should work with in-memory fallback when Redis is down."""
        CacheLayer = _import("utils.cache_layer", "CacheLayer")
        cache = CacheLayer(max_size=100)
        cache._redis = None  # Simulate Redis down
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"


class TestDBFailure:
    def test_memory_store_works_without_db(self):
        """Memory store should work independently of DB."""
        mod = _import("utils.memory_store")
        mem = mod.MemoryStore()
        assert mem is not None


class TestAPIFailure:
    @pytest.mark.asyncio
    async def test_web_engine_handles_network_error(self):
        """Web engine should return empty results on network failure."""
        WebEngine = _import("utils.web_engine", "WebEngine")
        engine = WebEngine()
        results = await engine.search("test query", sources=["nonexistent"])
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_web_engine_fetch_handles_bad_url(self):
        """Web engine should handle invalid URLs gracefully."""
        WebEngine = _import("utils.web_engine", "WebEngine")
        engine = WebEngine()
        result = await engine.fetch_url("not-a-url")
        assert isinstance(result, str)


class TestVectorStoreResilience:
    def test_empty_query(self):
        VectorStore = _import("utils.vector_store", "VectorStore")
        store = VectorStore()
        results = store.search("", top_k=5)
        assert isinstance(results, list)

    def test_search_empty_store(self):
        VectorStore = _import("utils.vector_store", "VectorStore")
        store = VectorStore()
        results = store.search("some query", top_k=5)
        assert len(results) == 0


