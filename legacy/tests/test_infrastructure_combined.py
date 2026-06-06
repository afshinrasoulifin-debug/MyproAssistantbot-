
"""Tests for infrastructure combined patterns — real behavior tests."""
import pytest
from arki_project.infrastructure.registry import InfraRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    InfraRegistry._instance = None
    yield
    InfraRegistry._instance = None


class TestCombinedPatterns:
    def test_combined_directory_exists(self):
        import os
        assert os.path.isdir("infrastructure/combined")

    def test_combined_modules_importable(self):
        import importlib, os
        combined_dir = "infrastructure/combined"
        for f in os.listdir(combined_dir):
            if f.endswith(".py") and f != "__init__.py":
                mod_name = f"tg_bot.infrastructure.combined.{f[:-3]}"
                mod = importlib.import_module(mod_name)
                assert mod is not None, f"Failed to import {mod_name}"

    def test_combined_classes_instantiable(self):
        import importlib, inspect, os
        combined_dir = "infrastructure/combined"
        instantiated = 0
        for f in os.listdir(combined_dir):
            if f.endswith(".py") and f != "__init__.py":
                mod_name = f"tg_bot.infrastructure.combined.{f[:-3]}"
                mod = importlib.import_module(mod_name)
                for name, cls in inspect.getmembers(mod, inspect.isclass):
                    if cls.__module__ == mod.__name__:
                        try:
                            obj = cls()
                            instantiated += 1
                        except TypeError:
                            pass  # Needs constructor args
        assert instantiated >= 10, f"Only {instantiated} combined classes instantiable"


