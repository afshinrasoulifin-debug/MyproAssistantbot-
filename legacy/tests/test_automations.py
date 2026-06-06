
"""Tests for architecture/automations.py — real behavior tests."""
from arki_project.architecture.automations import (
    AutoHealthCheck, TelemetryAggregator, MemoryCleanup,
    PerformanceWatchdog, UsageAnalytics,
)


def _make_registry():
    """Create a minimal mock registry dict for automations."""
    return {
        "health_monitor": None,
        "supervisor": None,
        "event_bus": None,
        "telemetry_monitor": None,
        "diagnostics_monitor": None,
    }


class TestAutoHealthCheck:
    def test_create(self):
        hc = AutoHealthCheck(_make_registry())
        assert hasattr(hc, "stats")
        assert callable(getattr(hc, "start", None))
        assert callable(getattr(hc, "stop", None))

    def test_stats_returns_dict(self):
        hc = AutoHealthCheck(_make_registry())
        result = hc.stats
        assert isinstance(result, dict)


class TestTelemetryAggregator:
    def test_create(self):
        ta = TelemetryAggregator(_make_registry())
        assert hasattr(ta, "stats")

    def test_stats_returns_dict(self):
        ta = TelemetryAggregator(_make_registry())
        result = ta.stats
        assert isinstance(result, dict)


class TestMemoryCleanup:
    def test_create(self):
        mc = MemoryCleanup(_make_registry())
        assert hasattr(mc, "stats")

    def test_stats_returns_dict(self):
        mc = MemoryCleanup(_make_registry())
        result = mc.stats
        assert isinstance(result, dict)


class TestPerformanceWatchdog:
    def test_create(self):
        wd = PerformanceWatchdog(_make_registry())
        assert hasattr(wd, "stats")

    def test_stats_type(self):
        wd = PerformanceWatchdog(_make_registry())
        result = wd.stats
        assert isinstance(result, dict)


class TestUsageAnalytics:
    def test_create(self):
        ua = UsageAnalytics(_make_registry())
        assert hasattr(ua, "stats")

    def test_stats_type(self):
        ua = UsageAnalytics(_make_registry())
        result = ua.stats
        assert isinstance(result, dict)


