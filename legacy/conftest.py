
"""
Root conftest.py — shared test fixtures for Arki Engine.
═══════════════════════════════════════════════════════════
Sets up arki_project module alias so all imports work without pip install -e.
"""
import asyncio
import os
import sys
import types

# ── arki_project resolution ─────────────────────────────────
# The project uses `from arki_project.xxx import ...` everywhere.
# Instead of requiring `pip install -e .`, we create a virtual
# module that maps arki_project.* to the project root.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if "arki_project" not in sys.modules:
    _arki_mod = types.ModuleType("arki_project")
    _arki_mod.__path__ = [project_root]
    _arki_mod.__file__ = os.path.join(project_root, "__init__.py")
    sys.modules["arki_project"] = _arki_mod

# ── Test environment variables ──────────────────────────────
os.environ.setdefault("BOT_TOKEN", "test:token")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings():
    """Provide test settings."""
    from config import load_settings
    return load_settings()


@pytest.fixture
async def db_session():
    """Provide an in-memory database session for tests."""
    from database.connection import init_db, close_db, get_session
    await init_db()
    async with get_session() as session:
        yield session
    await close_db()


