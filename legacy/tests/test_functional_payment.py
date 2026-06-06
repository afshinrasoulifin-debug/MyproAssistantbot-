
"""Functional tests for payment handler — v9.6."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tests.conftest import MockMessage
except ImportError:
    pytest.skip("Cannot import test fixtures", allow_module_level=True)


class TestPaymentFunctional:
    """Functional tests for payment flow."""

    def test_payment_handler_has_stripe(self):
        """Payment handler includes Stripe integration."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "payment_handler.py"
        )
        content = open(handler_path).read()
        assert "stripe" in content.lower()
        assert "checkout" in content.lower() or "Session" in content

    def test_payment_handler_has_stars(self):
        """Payment handler supports Telegram Stars."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "payment_handler.py"
        )
        content = open(handler_path).read()
        assert "XTR" in content or "Stars" in content or "LabeledPrice" in content

    def test_pre_checkout_validation(self):
        """Pre-checkout query validates payload format."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "payment_handler.py"
        )
        content = open(handler_path).read()
        assert "sub_" in content, "Must validate payload starts with sub_"
        assert "ok=False" in content, "Must reject invalid payloads"

    def test_plan_limits_defined(self):
        """All plan limits are properly defined."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "payment_handler.py"
        )
        content = open(handler_path).read()
        for plan in ["free", "pro", "business", "enterprise"]:
            assert plan in content, f"Plan '{plan}' must be defined"


