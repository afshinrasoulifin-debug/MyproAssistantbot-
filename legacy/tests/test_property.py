
"""Property-based tests using Hypothesis."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hypothesis import given, strategies as st, settings 
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Dummy decorators
    def given(*a, **kw):
        def dec(f): return pytest.mark.skip("hypothesis not installed")(f)
        return dec
    class st:
        @staticmethod
        def text(**kw): return None
        @staticmethod
        def integers(**kw): return None
        @staticmethod
        def floats(**kw): return None


@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
class TestPipelineProperties:
    @given(st.text(min_size=0, max_size=10000))
    def test_classifier_never_crashes(self, text):
        from core.pipeline import TaskClassifier
        c = TaskClassifier()
        result = c.classify(text)
        assert result is not None

    @given(st.text(min_size=1, max_size=100))
    def test_classifier_returns_valid_category(self, text):
        from core.pipeline import TaskClassifier
        c = TaskClassifier()
        result = c.classify(text)
        assert hasattr(result, 'value') or isinstance(result, str)


@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
class TestCacheProperties:
    @given(st.text(min_size=1, max_size=100), st.integers(min_value=0, max_value=1000))
    @pytest.mark.asyncio
    async def test_cache_set_get_roundtrip(self, key, value):
        from orchestration.cache_layer import CacheLayer
        cache = CacheLayer(max_size=100)
        await cache.set(key, value)
        result = await cache.get(key)
        assert result == value


@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
class TestVectorStoreProperties:
    @given(st.text(min_size=5, max_size=500))
    def test_vector_store_add_search(self, text):
        from utils.vector_store import VectorStore
        store = VectorStore()
        doc_id = store.add(text)
        assert doc_id
        results = store.search(text, top_k=1)
        assert len(results) >= 1


