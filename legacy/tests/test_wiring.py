
"""Test architecture wiring"""
from core.architecture.transport.bus import EventBus
from core.architecture.monitor.telemetry import TelemetryMonitor

class TestWiring:
    def test_eventbus_and_telemetry_exist(self):
        bus = EventBus()
        tm = TelemetryMonitor()
        assert bus is not None
        assert tm is not None

    def test_telemetry_has_methods(self):
        tm = TelemetryMonitor()
        assert callable(getattr(tm, "record", None))


