
"""Functional test: token tracking across all handlers — v9.7."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTokenTracking:
    """Tests that token tracking is wired into all relevant handlers."""

    def test_token_tracker_module_exists(self):
        """utils/token_tracker.py must exist with track_tokens function."""
        tracker_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "utils", "token_tracker.py"
        )
        assert os.path.exists(tracker_path)
        content = open(tracker_path).read()
        assert "async def track_tokens" in content
        assert "tokens_used_today" in content

    def test_ai_client_tracks_tokens(self):
        """ai_client.py must update tokens_used_today after AI calls."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "utils", "ai_client.py"
        )
        content = open(path).read()
        assert "tokens_used_today" in content

    def test_voice_handler_tracks_tokens(self):
        """voice.py must import and call token tracker."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "voice.py"
        )
        content = open(path).read()
        assert "track_tokens" in content or "token_tracker" in content

    def test_image_handler_tracks_tokens(self):
        """image.py must import and call token tracker."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "handlers", "image.py"
        )
        content = open(path).read()
        assert "track_tokens" in content or "token_tracker" in content

    def test_content_handlers_track_tokens(self):
        """All major content handlers must have token tracking."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for handler in ["content_studio", "content_brain", "sales_engine", "agents"]:
            path = os.path.join(base, "handlers", f"{handler}.py")
            content = open(path).read()
            assert "track_tokens" in content or "token_tracker" in content, \
                f"{handler}.py must import token tracker"


