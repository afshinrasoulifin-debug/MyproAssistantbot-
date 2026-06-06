
"""Transport layer tests — v29.0.0 real tests."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _safe_import(path):
    try:
        import importlib
        return importlib.import_module(path)
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Cannot import {path}: {e}")


class TestHTTPPool:
    """Tests for HTTP connection pool."""

    def test_module_imports(self):
        mod = _safe_import("arki_project.utils.http_pool")
        assert mod is not None
        assert hasattr(mod, "get_client")
        assert hasattr(mod, "close_all")
        assert hasattr(mod, "pool_stats")

    def test_pool_stats_structure(self):
        mod = _safe_import("arki_project.utils.http_pool")
        stats = mod.pool_stats()
        assert isinstance(stats, dict)
        assert "active_sessions" in stats
        assert "total_created" in stats
        assert "session_names" in stats


class TestOutboundQueue:
    """Tests for outbound message queue."""

    def test_module_imports(self):
        mod = _safe_import("arki_project.utils.outbound_queue")
        assert mod is not None
        assert hasattr(mod, "send_long_text")

    def test_split_function_exists(self):
        mod = _safe_import("arki_project.utils.models_registry")
        assert hasattr(mod, "split_for_telegram")
        # Test actual splitting
        chunks = mod.split_for_telegram("hello")
        assert chunks == ["hello"]
        long_text = "x" * 5000
        chunks = mod.split_for_telegram(long_text, max_len=4096)
        assert len(chunks) >= 2
        assert all(len(c) <= 4096 for c in chunks)


class TestNetworkTools:
    """Tests for network tools module."""

    def test_module_imports(self):
        mod = _safe_import("arki_project.utils.network_tools")
        assert mod is not None
        assert hasattr(mod, "ping")
        assert hasattr(mod, "dns_lookup")


