
"""
tests/test_metrics_real.py — Metrics Exporter Tests
═══════════════════════════════════════════════════
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.metrics_exporter import (
    record_request, record_message, record_error,
    set_active_users, set_circuit_state, set_build_info,
    generate_metrics,
)

import pytest


class TestMetricsRecording:
    """Test metric recording functions."""

    def test_record_request(self):
        record_request("gemini", "gemini-2.5-pro", "success", 1.5, tokens=1000)
        # No crash = success (stores internally)

    def test_record_message(self):
        record_message("text")
        record_message("photo")
        record_message("command")

    def test_record_error(self):
        record_error("timeout", "openrouter")
        record_error("rate_limit", "gemini")

    def test_set_active_users(self):
        set_active_users(42)

    def test_set_circuit_state(self):
        set_circuit_state("gemini", 0)
        set_circuit_state("groq", 2)

    def test_set_build_info(self):
        set_build_info("17.3.0", "production", "3.12.0")


class TestMetricsExport:
    """Test Prometheus export format."""

    def test_generate_metrics_returns_text(self):
        record_request("test", "model", "ok", 0.5)
        text, content_type = generate_metrics()
        assert isinstance(text, str)
        assert len(text) > 0
        assert "text/" in content_type

    def test_metrics_contain_known_metric(self):
        record_request("test_export", "test_model", "success", 0.1)
        text, _ = generate_metrics()
        assert "arki" in text.lower() or "request" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


