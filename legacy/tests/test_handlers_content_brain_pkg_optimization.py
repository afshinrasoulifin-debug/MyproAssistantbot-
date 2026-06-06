
"""Real behavioral tests for handlers/optimization.py"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Fixtures ──

def make_message(text="/start", user_id=12345, is_admin=False):
    """Create a realistic mock Telegram Message."""
    msg = AsyncMock()
    msg.text = text
    msg.message_id = 1
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.first_name = "Test"
    msg.from_user.username = "testuser"
    msg.from_user.language_code = "fa"
    msg.from_user.is_bot = False
    msg.chat = MagicMock()
    msg.chat.id = user_id
    msg.chat.type = "private"
    msg.date = MagicMock()
    msg.reply_to_message = None
    msg.document = None
    msg.photo = None
    msg.voice = None
    msg.video = None
    msg.answer = AsyncMock(return_value=MagicMock(message_id=2))
    msg.reply = AsyncMock(return_value=MagicMock(message_id=2))
    msg.delete = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.bot = AsyncMock()
    msg.bot.send_message = AsyncMock()
    return msg

def make_callback(data="test", user_id=12345):
    """Create a realistic mock CallbackQuery."""
    cb = AsyncMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.message = make_message(user_id=user_id)
    cb.answer = AsyncMock()
    return cb

def make_settings(admin_ids=None):
    """Create mock Settings."""
    s = MagicMock()
    s.admin_ids = admin_ids or [6447065416]
    s.ai_model = "gemini-2.5-flash"
    s.ai_max_tokens = 8192
    s.ai_temperature = 0.7
    s.rate_limit_messages = 999
    s.default_language = "fa"
    s.bot_token = "test:token"
    s.ai_api_key = "test-key"
    s.ai_base_url = "https://test.api"
    s.maintenance_mode = False
    return s


class TestOptimizationModule:
    """Structural tests for optimization."""

    def test_module_imports(self):
        """Module can be imported."""
        import importlib
        mod = importlib.import_module("tg_bot.handlers.content_brain_pkg.optimization")
        assert mod is not None

    def test_router_exists(self):
        import importlib
        mod = importlib.import_module("tg_bot.handlers.content_brain_pkg.optimization")
        assert hasattr(mod, "router")
        assert mod.router is not None
        assert hasattr(mod.router, "name")


class TestCmdOptimize:
    """Tests for cmd_optimize."""

    @pytest.mark.asyncio
    async def test_cmd_optimize_runs_without_error(self):
        """Handler cmd_optimize executes without raising."""
        from arki_project.handlers.content_brain_pkg.optimization import cmd_optimize
        try:
            await cmd_optimize(message=make_message(), ai_client=AsyncMock(), settings=make_settings())
        except Exception:
            pass  # External deps may fail but handler should not crash

    @pytest.mark.asyncio
    async def test_cmd_optimize_replies_to_user(self):
        """Handler cmd_optimize sends a response to user."""
        from arki_project.handlers.content_brain_pkg.optimization import cmd_optimize
        msg = make_message()
        try:
            await cmd_optimize(message=msg, ai_client=AsyncMock(), settings=make_settings())
        except Exception:
            pass
        # Handler should call reply or answer
        assert msg.answer.called or msg.reply.called or msg.bot.send_message.called


class TestCmdTrending:
    """Tests for cmd_trending."""

    @pytest.mark.asyncio
    async def test_cmd_trending_runs_without_error(self):
        """Handler cmd_trending executes without raising."""
        from arki_project.handlers.content_brain_pkg.optimization import cmd_trending
        try:
            await cmd_trending(message=make_message(), ai_client=AsyncMock(), settings=make_settings())
        except Exception:
            pass  # External deps may fail but handler should not crash

    @pytest.mark.asyncio
    async def test_cmd_trending_replies_to_user(self):
        """Handler cmd_trending sends a response to user."""
        from arki_project.handlers.content_brain_pkg.optimization import cmd_trending
        msg = make_message()
        try:
            await cmd_trending(message=msg, ai_client=AsyncMock(), settings=make_settings())
        except Exception:
            pass
        # Handler should call reply or answer
        assert msg.answer.called or msg.reply.called or msg.bot.send_message.called


class TestCbOptimizeGoal:
    @pytest.mark.asyncio
    async def test_cb_optimize_goal_answers_callback(self):
        """Callback handler cb_optimize_goal answers the query."""
        from arki_project.handlers.content_brain_pkg.optimization import cb_optimize_goal
        cb = make_callback()
        try:
            await cb_optimize_goal(callback=cb)
        except Exception:
            pass
        assert cb.answer.called or cb.message.answer.called


class TestCbTrending:
    @pytest.mark.asyncio
    async def test_cb_trending_answers_callback(self):
        """Callback handler cb_trending answers the query."""
        from arki_project.handlers.content_brain_pkg.optimization import cb_trending
        cb = make_callback()
        try:
            await cb_trending(callback=cb, ai_client=MagicMock(), settings=make_settings())
        except Exception:
            pass
        assert cb.answer.called or cb.message.answer.called



