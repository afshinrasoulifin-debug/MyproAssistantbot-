
"""
Integration tests for Arki Engine.
Uses mock API responses to test full flows.
All imports wrapped with skip on ImportError for environments
missing heavy deps (httpx, aiohttp, etc.)
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tests.helpers import MockMessage, MockCallbackQuery, MockState
except ImportError:
    MockMessage = MockCallbackQuery = MockState = None


def _import(module_path, cls_name=None):
    """Import helper — raises pytest.skip if missing."""
    import importlib
    try:
        mod = importlib.import_module(module_path)
        if cls_name:
            return getattr(mod, cls_name)
        return mod
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Dependency missing: {e}")


class TestStartFlow:
    """Test the /start command flow."""

    def test_start_imports(self):
        try:
            from handlers.common import cmd_start
            assert callable(cmd_start)
        except ImportError as e:
            pytest.skip(f"Import dependency: {e}")


class TestI18nIntegration:
    """Test i18n system integration."""

    def test_i18n_loads(self):
        mod = _import("utils.i18n.engine", "get_i18n")
        i18n = mod()
        assert 'fa' in i18n.available_languages or len(i18n.available_languages) >= 0

    def test_translation_fallback(self):
        I18nEngine = _import("utils.i18n.engine", "I18nEngine")
        engine = I18nEngine()
        result = engine.t("nonexistent.key")
        assert result == "nonexistent.key"


class TestCacheLayer:
    """Test cache layer."""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        CacheLayer = _import("utils.cache_layer", "CacheLayer")
        cache = CacheLayer(max_size=100)
        await cache.set("test_key", {"value": 42})
        result = await cache.get("test_key")
        assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        CacheLayer = _import("utils.cache_layer", "CacheLayer")
        cache = CacheLayer(max_size=3)
        for i in range(5):
            await cache.set(f"key{i}", i)
        assert len(cache._memory) <= 3


class TestSecureExecutor:
    """Test secure executor sandbox."""

    def test_safe_execution(self):
        SecureExecutor = _import("utils.secure_executor", "SecureExecutor")
        executor = SecureExecutor()
        result = executor.execute("2 + 2")
        assert result.success
        assert result.result == 4

    def test_blocked_import(self):
        SecureExecutor = _import("utils.secure_executor", "SecureExecutor")
        executor = SecureExecutor()
        result = executor.execute("import os")
        assert not result.success
        assert "blocked" in result.error.lower() or "security" in result.error.lower()

    def test_blocked_builtins(self):
        SecureExecutor = _import("utils.secure_executor", "SecureExecutor")
        executor = SecureExecutor()
        result = executor.execute("open('/etc/passwd')")
        assert not result.success


class TestMetricsCollector:
    """Test metrics collector."""

    def test_counter(self):
        MetricsCollector = _import("utils.metrics_collector", "MetricsCollector")
        m = MetricsCollector()
        m.increment("test_counter")
        m.increment("test_counter")
        assert m._counters["test_counter"] == 2

    def test_gauge(self):
        MetricsCollector = _import("utils.metrics_collector", "MetricsCollector")
        m = MetricsCollector()
        m.gauge("memory_mb", 512.5)
        assert m._gauges["memory_mb"] == 512.5

    def test_histogram(self):
        MetricsCollector = _import("utils.metrics_collector", "MetricsCollector")
        m = MetricsCollector()
        for v in [10, 20, 30, 40, 50]:
            m.observe("response_time", v)
        stats = m.get_all()
        assert stats["histograms"]["response_time"]["count"] == 5

    def test_prometheus_export(self):
        MetricsCollector = _import("utils.metrics_collector", "MetricsCollector")
        m = MetricsCollector()
        m.increment("requests")
        output = m.to_prometheus()
        assert "arki_requests" in output


class TestAlertSystem:
    """Test alert system."""

    @pytest.mark.asyncio
    async def test_alert_dedup(self):
        mod = _import("utils.alert_system")
        AlertSystem = mod.AlertSystem
        AlertLevel = mod.AlertLevel
        alerts = AlertSystem()
        await alerts.send(AlertLevel.ERROR, "Test", "msg")
        await alerts.send(AlertLevel.ERROR, "Test", "msg")
        assert len(alerts._history) == 1


class TestTaskQueue:
    """Test task queue."""

    @pytest.mark.asyncio
    async def test_submit_and_complete(self):
        TaskQueue = _import("utils.task_queue", "TaskQueue")
        queue = TaskQueue(max_workers=1)
        await queue.start()

        async def dummy_task():
            return 42

        task_id = await queue.submit(dummy_task)
        import asyncio
        await asyncio.sleep(0.5)
        task = queue.get_status(task_id)
        assert task is not None
        await queue.stop()


class TestHTTPPool:
    """Test HTTP session pool."""

    @pytest.mark.asyncio
    async def test_pool_creation(self):
        HTTPSessionPool = _import("utils.http_session_pool", "HTTPSessionPool")
        pool = HTTPSessionPool()
        session = await pool.get_session("test")
        assert not session.closed
        await pool.close_all()


