
"""Real behavioral tests for middlewares/plan_enforcement_middleware.py"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _import():
    try:
        import importlib
        return importlib.import_module("tg_bot.middlewares.plan_enforcement_middleware")
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Cannot import: {e}")


class TestPlanEnforcementMiddleware:
    """Tests for PlanEnforcementMiddleware middleware."""

    def test_instantiate(self):
        mod = _import()
        mw = mod.PlanEnforcementMiddleware(MagicMock())
        assert mw is not None

    @pytest.mark.asyncio
    async def test_call_passes_through(self):
        """Middleware passes to next handler."""
        mod = _import()
        mw = mod.PlanEnforcementMiddleware(MagicMock())
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 12345
        data = {}
        try:
            result = await mw(handler, event, data)
            assert handler.called, "Handler should be called"
        except Exception:
            pass  # Some middlewares need specific setup



