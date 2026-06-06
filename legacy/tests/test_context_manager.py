
"""Tests for context window management."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTokenEstimation:
    def test_empty_text(self):
        from arki_project.utils.context_manager import estimate_tokens
        assert estimate_tokens("") == 0

    def test_english_text(self):
        from arki_project.utils.context_manager import estimate_tokens
        tokens = estimate_tokens("Hello world this is a test")
        assert 5 <= tokens <= 10

    def test_farsi_text(self):
        from arki_project.utils.context_manager import estimate_tokens
        tokens = estimate_tokens("سلام دنیا این یک تست است")
        assert tokens > 0


class TestContextWindow:
    def test_fit_messages_within_limit(self):
        from arki_project.utils.context_manager import ContextWindowManager
        cm = ContextWindowManager(model="gemini-2.5-flash")
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        fitted = cm.fit_messages(messages)
        assert len(fitted) == 10

    def test_truncates_long_history(self):
        from arki_project.utils.context_manager import ContextWindowManager
        cm = ContextWindowManager(model="qwen-qwq-32b", max_response_tokens=16000)
        messages = [{"role": "user", "content": "x" * 1000} for _ in range(200)]
        fitted = cm.fit_messages(messages)
        assert len(fitted) < 200

    def test_compress_history(self):
        from arki_project.utils.context_manager import ContextWindowManager
        cm = ContextWindowManager()
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
        compressed = cm.compress_history(messages, keep_recent=10)
        assert len(compressed) == 11  # 1 summary + 10 recent
        assert compressed[0]["role"] == "system"


