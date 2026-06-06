
"""Functional test: Prometheus metrics — v9.7."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPrometheusMetrics:
    """Tests that Prometheus metrics are properly wired."""

    def test_push_function_exists(self):
        """push_prometheus_metrics() must exist in ai_cost_tracker."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "utils", "ai_cost_tracker.py"
        )
        content = open(path).read()
        assert "def push_prometheus_metrics" in content
        assert "Counter" in content
        assert "Histogram" in content

    def test_push_called_in_ai_client(self):
        """ai_client.py must CALL push_prometheus_metrics after API calls."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "utils", "ai_client.py"
        )
        content = open(path).read()
        assert "push_prom" in content or "push_prometheus" in content, \
            "ai_client.py must call push_prometheus_metrics"

        # Find the ask() method and verify push is AFTER the API call
        ask_start = content.find("async def ask(")
        ask_end = content.find("async def ask_raw")
        ask_body = content[ask_start:ask_end] if ask_end > ask_start else content[ask_start:]

        assert "_push_prom" in ask_body, \
            "push_prometheus must be called inside ask() method"

    def test_prometheus_in_requirements(self):
        """prometheus-client must be in requirements.txt."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        content = open(path).read()
        assert "prometheus" in content.lower()


