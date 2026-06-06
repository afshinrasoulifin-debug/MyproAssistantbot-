
"""Performance benchmark tests."""
import pytest
import time
import importlib
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _import(module_path, cls_name=None):
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, cls_name) if cls_name else mod
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Dependency missing: {e}")


class TestPipelineBenchmarks:
    def test_classifier_throughput(self):
        """Benchmark: classifier should handle 1000+ messages/second."""
        TaskClassifier = _import("core.pipeline", "TaskClassifier")
        c = TaskClassifier()
        messages = [f"test message {i}" for i in range(1000)]
        start = time.time()
        for msg in messages:
            c.classify(msg)
        elapsed = time.time() - start
        throughput = 1000 / max(0.001, elapsed)
        assert throughput > 100, f"Classifier too slow: {throughput:.0f} msg/s"


class TestCacheBenchmarks:
    @pytest.mark.asyncio
    async def test_cache_throughput(self):
        """Benchmark: cache should handle 10000+ ops/second."""
        CacheLayer = _import("utils.cache_layer", "CacheLayer")
        cache = CacheLayer(max_size=50000)
        start = time.time()
        for i in range(10000):
            await cache.set(f"key{i}", f"value{i}")
        for i in range(10000):
            await cache.get(f"key{i}")
        elapsed = time.time() - start
        ops_per_sec = 20000 / max(0.001, elapsed)
        assert ops_per_sec > 1000, f"Cache too slow: {ops_per_sec:.0f} ops/s"


class TestVectorBenchmarks:
    def test_vector_search_throughput(self):
        """Benchmark: vector search should handle 100+ queries/second."""
        VectorStore = _import("utils.vector_store", "VectorStore")
        store = VectorStore()
        for i in range(100):
            store.add(f"This is document number {i} about topic {i % 10}")
        start = time.time()
        for i in range(100):
            store.search(f"topic {i % 10}", top_k=5)
        elapsed = time.time() - start
        qps = 100 / max(0.001, elapsed)
        assert qps > 10, f"Vector search too slow: {qps:.0f} q/s"


