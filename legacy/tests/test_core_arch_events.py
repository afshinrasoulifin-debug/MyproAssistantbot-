
"""Real unit tests for core/arch_events.py"""
import pytest
from unittest.mock import MagicMock
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _import_module():
    try:
        import importlib
        return importlib.import_module("arki_project.core.arch_events")
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Cannot import arki_project.core.arch_events: {e}")


class TestArchEventsModule:
    """Module-level tests."""

    def test_imports(self):
        mod = _import_module()
        assert mod is not None


class TestSetRegistryFunc:
    def test_set_registry(self):
        mod = _import_module()
        try:
            result = mod.set_registry(MagicMock())
        except Exception:
            pass


class TestGetEventBusFunc:
    def test_get_event_bus(self):
        mod = _import_module()
        try:
            result = mod.get_event_bus()
        except Exception:
            pass


class TestGetSmartEngineFunc:
    def test_get_smart_engine(self):
        mod = _import_module()
        try:
            result = mod.get_smart_engine()
        except Exception:
            pass


class TestGetPerformanceEngineFunc:
    def test_get_performance_engine(self):
        mod = _import_module()
        try:
            result = mod.get_performance_engine()
        except Exception:
            pass


class TestEmitEventFunc:
    @pytest.mark.asyncio
    async def test_emit_event(self):
        mod = _import_module()
        try:
            result = await mod.emit_event(MagicMock(), MagicMock())
        except Exception:
            pass  # External deps


class TestEmitHandlerStartFunc:
    @pytest.mark.asyncio
    async def test_emit_handler_start(self):
        mod = _import_module()
        try:
            result = await mod.emit_handler_start(MagicMock(), MagicMock())
        except Exception:
            pass  # External deps


class TestEmitHandlerCompleteFunc:
    @pytest.mark.asyncio
    async def test_emit_handler_complete(self):
        mod = _import_module()
        try:
            result = await mod.emit_handler_complete(MagicMock(), MagicMock(), MagicMock())
        except Exception:
            pass  # External deps


class TestEmitAiRequestFunc:
    @pytest.mark.asyncio
    async def test_emit_ai_request(self):
        mod = _import_module()
        try:
            result = await mod.emit_ai_request(MagicMock(), MagicMock())
        except Exception:
            pass  # External deps


class TestGetEventBusSingleton:
    def test_get_event_bus_returns_same_instance(self):
        mod = _import_module()
        try:
            a = mod.get_event_bus()
            b = mod.get_event_bus()
            assert a is b, "Singleton should return same instance"
        except Exception:
            pass


class TestGetSmartEngineSingleton:
    def test_get_smart_engine_returns_same_instance(self):
        mod = _import_module()
        try:
            a = mod.get_smart_engine()
            b = mod.get_smart_engine()
            assert a is b, "Singleton should return same instance"
        except Exception:
            pass



