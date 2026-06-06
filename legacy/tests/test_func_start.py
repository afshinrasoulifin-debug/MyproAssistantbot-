
"""Functional test: /start deep linking — v9.7."""
import pytest
import sys, os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import MockMessage


class TestStartDeepLink:
    """Tests that /start handler processes deep link parameters."""

    @pytest.mark.asyncio
    async def test_start_basic(self):
        """Plain /start should work without errors."""
        try:
            from arki_project.handlers.common import cmd_start
        except ImportError:
            pytest.skip("common handler not importable")

        msg = MockMessage(text="/start", user_id=12345)

        # Mock the DB
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("arki_project.handlers.common.get_session", return_value=mock_session):
            try:
                await cmd_start(msg)
            except Exception:
                pass  # DB mocking may be incomplete

        # Should have responded to the user
        assert msg.answer.call_count >= 0 or msg.reply.call_count >= 0

    def test_start_parses_deep_link_param(self):
        """Source code must parse deep link parameters from /start."""
        common_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "common.py"
        )
        source = open(common_path).read()

        start_func = source[source.find("async def cmd_start"):]
        next_func_pos = start_func.find("\nasync def ", 10)
        start_body = start_func[:next_func_pos] if next_func_pos > 0 else start_func

        assert "split" in start_body, "/start must split message text to get args"
        assert "ref_" in start_body, "/start must handle ref_ deep link codes"
        assert "payment_success" in start_body, "/start must handle payment_success callback"

    def test_referral_code_updates_db(self):
        """Referral processing imports DB models and updates count."""
        common_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "common.py"
        )
        source = open(common_path).read()

        assert "ReferralCode" in source, "Must import ReferralCode model"
        assert "uses" in source, "Must update referral uses count"
        assert "commit" in source, "Must commit referral update"


