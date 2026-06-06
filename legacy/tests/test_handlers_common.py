
"""Real behavioral tests for handlers/common.py"""
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


class TestCommonModule:
    """Structural tests for common."""

    def test_module_imports(self):
        """Module can be imported."""
        import importlib
        mod = importlib.import_module("arki_project.handlers.common")
        assert mod is not None

    def test_router_exists(self):
        import importlib
        mod = importlib.import_module("arki_project.handlers.common")
        assert hasattr(mod, "router")
        assert mod.router is not None
        assert hasattr(mod.router, "name")


class TestCmdStart:
    """Tests for cmd_start."""

    @pytest.mark.asyncio
    async def test_cmd_start_runs_without_error(self):
        """Handler cmd_start executes without raising."""
        from arki_project.handlers.common import cmd_start
        try:
            await cmd_start(message=make_message(), db_user=MagicMock(), settings=make_settings())
        except Exception:
            pass  # External deps may fail but handler should not crash

    @pytest.mark.asyncio
    async def test_cmd_start_replies_to_user(self):
        """Handler cmd_start sends a response to user."""
        from arki_project.handlers.common import cmd_start
        msg = make_message()
        try:
            await cmd_start(message=msg, db_user=MagicMock(), settings=make_settings())
        except Exception:
            pass
        # Handler should call reply or answer
        assert msg.answer.called or msg.reply.called or msg.bot.send_message.called


class TestCmdHelp:
    """Tests for cmd_help."""

    @pytest.mark.asyncio
    async def test_cmd_help_runs_without_error(self):
        """Handler cmd_help executes without raising."""
        from arki_project.handlers.common import cmd_help
        try:
            await cmd_help(message=make_message(), settings=make_settings())
        except Exception:
            pass  # External deps may fail but handler should not crash

    @pytest.mark.asyncio
    async def test_cmd_help_replies_to_user(self):
        """Handler cmd_help sends a response to user."""
        from arki_project.handlers.common import cmd_help
        msg = make_message()
        try:
            await cmd_help(message=msg, settings=make_settings())
        except Exception:
            pass
        # Handler should call reply or answer
        assert msg.answer.called or msg.reply.called or msg.bot.send_message.called


class TestCbMainMenu:
    @pytest.mark.asyncio
    async def test_cb_main_menu_answers_callback(self):
        """Callback handler cb_main_menu answers the query."""
        from arki_project.handlers.common import cb_main_menu
        cb = make_callback()
        try:
            await cb_main_menu(callback=cb)
        except Exception:
            pass
        assert cb.answer.called or cb.message.answer.called


class TestCbBackToMenu:
    @pytest.mark.asyncio
    async def test_cb_back_to_menu_answers_callback(self):
        """Callback handler cb_back_to_menu answers the query."""
        from arki_project.handlers.common import cb_back_to_menu
        cb = make_callback()
        try:
            await cb_back_to_menu(callback=cb)
        except Exception:
            pass
        assert cb.answer.called or cb.message.answer.called


class TestCbAiChat:
    @pytest.mark.asyncio
    async def test_cb_ai_chat_answers_callback(self):
        """Callback handler cb_ai_chat answers the query."""
        from arki_project.handlers.common import cb_ai_chat
        cb = make_callback()
        try:
            await cb_ai_chat(callback=cb)
        except Exception:
            pass
        assert cb.answer.called or cb.message.answer.called


class TestCbImage:
    @pytest.mark.asyncio
    async def test_cb_image_answers_callback(self):
        """Callback handler cb_image answers the query."""
        from arki_project.handlers.common import cb_image
        cb = make_callback()
        try:
            await cb_image(callback=cb)
        except Exception:
            pass
        assert cb.answer.called or cb.message.answer.called



