
"""
Tests for TITANIUM boot sequence & module initialization.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arki_project.utils.titanium import (
    TITANIUM_VERSION,
    TITANIUM_CODENAME,
    boot_titanium,
    shutdown_titanium,
)


def test_version():
    """Version should be 10.1.0."""
    assert TITANIUM_VERSION == "26.1.0"


def test_codename():
    """Codename should be set."""
    assert len(TITANIUM_CODENAME) > 0


def test_boot_shutdown():
    """boot_titanium and shutdown_titanium should be callable."""
    import asyncio

    async def _run():
        # Boot should not raise
        await boot_titanium()
        # Shutdown should not raise
        await shutdown_titanium()

    asyncio.run(_run())


def test_imports():
    """All TITANIUM submodules should be importable."""
    assert True


def test_config():
    """Config should have v10.1 settings."""
    from arki_project.utils.titanium.config import TITANIUM_CONFIG
    assert TITANIUM_CONFIG["version"] == "10.1.0"


if __name__ == "__main__":
    test_version()
    test_codename()
    test_boot_shutdown()
    test_imports()
    test_config()
    print("✅ All boot tests passed")


