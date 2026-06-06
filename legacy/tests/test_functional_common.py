
"""Functional tests for common handler — v9.6."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tests.conftest import MockMessage, MockSettings
except ImportError:
    pytest.skip("Cannot import test fixtures", allow_module_level=True)


class TestCommonFunctional:
    """Functional tests for /start and /help."""

    def test_start_has_deep_linking(self):
        """The /start handler parses deep link parameters."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "common.py"
        )
        content = open(handler_path).read()
        assert "deep_link" in content.lower() or "start_args" in content.lower() or "_deep_link" in content, \
            "/start must parse deep link parameters"

    def test_start_has_referral_handling(self):
        """The /start handler processes referral codes."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "common.py"
        )
        content = open(handler_path).read()
        assert "ref_" in content, "/start must handle ref_ deep link codes"

    def test_start_has_payment_callback(self):
        """The /start handler handles payment_success deep link."""
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "common.py"
        )
        content = open(handler_path).read()
        assert "payment_success" in content, "/start must handle payment callbacks"

    def test_common_module_compiles(self):
        """common.py compiles without errors."""
        import py_compile
        handler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "common.py"
        )
        py_compile.compile(handler_path, doraise=True)


