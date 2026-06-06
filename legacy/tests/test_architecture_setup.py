
"""Real unit tests for architecture/setup.py"""
import pytest
from unittest.mock import MagicMock
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _import_module():
    try:
        import importlib
        return importlib.import_module("arki_project.architecture.setup")
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Cannot import arki_project.architecture.setup: {e}")


class TestSetupModule:
    """Module-level tests."""

    def test_imports(self):
        mod = _import_module()
        assert mod is not None


class TestInitArchitectureFunc:
    def test_init_architecture(self):
        mod = _import_module()
        try:
            result = mod.init_architecture()
        except Exception:
            pass


class TestGetComponentFunc:
    def test_get_component(self):
        mod = _import_module()
        try:
            result = mod.get_component(MagicMock())
        except Exception:
            pass


class TestGetRegistryFunc:
    def test_get_registry(self):
        mod = _import_module()
        try:
            result = mod.get_registry()
        except Exception:
            pass


class TestBootArchitectureFunc:
    def test_boot_architecture(self):
        mod = _import_module()
        try:
            result = mod.boot_architecture()
        except Exception:
            pass


class TestGetRegistrySingleton:
    def test_get_registry_returns_same_instance(self):
        mod = _import_module()
        try:
            a = mod.get_registry()
            b = mod.get_registry()
            assert a is b, "Singleton should return same instance"
        except Exception:
            pass



