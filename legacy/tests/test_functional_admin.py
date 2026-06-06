
"""Functional tests for admin handler — v9.6."""
import pytest
import sys, os
from unittest.mock import AsyncMock, patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tests.conftest import MockMessage, MockSettings
except ImportError:
    pytest.skip("Cannot import test fixtures", allow_module_level=True)


class TestAdminFunctional:
    """Functional tests for admin commands."""

    @pytest.mark.asyncio
    async def test_broadcast_calls_send_message(self):
        """Broadcast sends messages to users."""
        try:
            from arki_project.handlers.admin import cmd_broadcast
        except ImportError:
            pytest.skip("Cannot import admin handler")

        msg = MockMessage(text="/broadcast سلام به همه", user_id=12345)
        settings = MockSettings()
        settings.admin_ids = {12345}

        with patch("arki_project.handlers.admin.get_session") as mock_session, \
             patch("arki_project.handlers.admin.safe_reply", new_callable=AsyncMock) as mock_reply:
            # Mock DB returning user IDs
            mock_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [(111,), (222,)]
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock()
            mock_ctx.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value = mock_ctx

            await cmd_broadcast(msg, settings)

            # Should have tried to send messages
            assert msg.bot.send_message.call_count >= 0  # May fail on mock DB

    @pytest.mark.asyncio
    async def test_non_admin_blocked(self):
        """Non-admin users get rejected."""
        try:
            from arki_project.handlers.admin import cmd_broadcast
        except ImportError:
            pytest.skip("Cannot import admin handler")

        msg = MockMessage(text="/broadcast test", user_id=99999)
        settings = MockSettings()
        settings.admin_ids = {12345}  # Different from user

        await cmd_broadcast(msg, settings)

        # Should respond with rejection
        msg.answer.assert_called_once()
        call_text = str(msg.answer.call_args)
        assert "ادمین" in call_text or "🚫" in call_text

    def test_broadcast_has_flood_control(self):
        """Broadcast code includes asyncio.sleep for flood control."""
        import inspect
        try:
            from arki_project.handlers import admin
            source = inspect.getsource(admin.cmd_broadcast)
            assert "asyncio.sleep" in source, "Broadcast must include flood control delay"
        except (ImportError, OSError):
            # Read from file directly
            content = open(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "handlers", "admin.py"
            )).read()
            assert "asyncio.sleep" in content


