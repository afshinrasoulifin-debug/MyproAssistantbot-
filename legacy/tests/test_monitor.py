
"""
Test architecture.monitor — Telemetry, Health, Console
"""
import asyncio
from core.architecture.monitor.telemetry import TelemetryMonitor, DiagnosticsMonitor
from core.architecture.monitor.health import HealthMonitor, Watcher, Observer
from core.architecture.monitor.console import RuntimeConsole


class TestTelemetryMonitor:
    def test_record_and_aggregate(self):
        tm = TelemetryMonitor()
        tm.record("api.latency", 0.5)
        tm.record("api.latency", 1.2)
        tm.record("api.latency", 0.8)
        agg = tm.aggregate("api.latency")
        assert agg["count"] == 3
        assert 0.5 <= agg["mean"] <= 1.2
        assert agg["min"] == 0.5
        assert agg["max"] == 1.2

    def test_increment_counter(self):
        tm = TelemetryMonitor()
        tm.increment("requests")
        tm.increment("requests")
        tm.increment("requests")
        assert tm.get_counter("requests") == 3

    def test_gauge(self):
        tm = TelemetryMonitor()
        tm.gauge("memory_mb", 128.5)
        assert tm.get_gauge("memory_mb") == 128.5

    def test_report_structure(self):
        tm = TelemetryMonitor()
        tm.increment("test_counter")
        tm.gauge("test_gauge", 1.0)
        tm.record("test_metric", 0.5)
        report = tm.report()
        assert "counters" in report
        assert "gauges" in report
        assert "metrics" in report

    def test_reset(self):
        tm = TelemetryMonitor()
        tm.increment("x")
        tm.gauge("y", 1)
        tm.record("z", 0.5)
        tm.reset()
        assert tm.get_counter("x") == 0
        assert tm.get_gauge("y") is None


class TestDiagnosticsMonitor:
    def test_trace(self):
        dm = DiagnosticsMonitor()
        dm.trace("ai_request", duration_s=1.5, success=True, model="gemini")
        traces = dm.recent_traces()
        assert len(traces) == 1
        assert traces[0]["operation"] == "ai_request"
        assert traces[0]["duration_s"] == 1.5

    def test_trace_errors_counted(self):
        dm = DiagnosticsMonitor()
        dm.trace("api_call", duration_s=0.1, success=False)
        dm.trace("api_call", duration_s=0.2, success=True)
        report = dm.diagnostic_report()
        assert report["traces"] == 2
        errors = report["recent_errors"]
        assert len(errors) == 1

    def test_alert_threshold(self):
        dm = DiagnosticsMonitor()
        dm.set_alert_threshold("trace.slow_op", 1.0)
        for _ in range(5):
            dm.trace("slow_op", duration_s=2.0)
        alerts = dm.check_alerts()
        assert len(alerts) >= 1


class TestHealthMonitor:
    def test_register_healthy(self):
        hm = HealthMonitor()
        hm.register("db", lambda: True)
        result = asyncio.get_event_loop().run_until_complete(hm.check_all())
        assert result["db"] == "healthy"

    def test_register_unhealthy(self):
        hm = HealthMonitor()
        def failing_check():
            raise RuntimeError("DB down!")
        hm.register("db", failing_check)
        result = asyncio.get_event_loop().run_until_complete(hm.check_all())
        assert result["db"] == "unhealthy"

    def test_is_healthy(self):
        hm = HealthMonitor()
        hm.register("check1", lambda: True)
        asyncio.get_event_loop().run_until_complete(hm.check_all())
        assert hm.is_healthy()

    def test_on_unhealthy_callback(self):
        hm = HealthMonitor()
        alerts = []
        hm.on_unhealthy(lambda name, err: alerts.append(name))
        hm.register("bad", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        asyncio.get_event_loop().run_until_complete(hm.check_all())
        assert "bad" in alerts


class TestWatcher:
    def test_watch_and_update(self):
        w = Watcher()
        w.watch("counter", 0)
        assert w.get("counter") == 0
        changed = w.update("counter", 5)
        assert changed is True
        assert w.get("counter") == 5

    def test_no_change(self):
        w = Watcher()
        w.watch("val", 10)
        changed = w.update("val", 10)
        assert changed is False

    def test_on_change_callback(self):
        w = Watcher()
        changes = []
        w.watch("x", 0)
        w.on_change("x", lambda k, old, new: changes.append((old, new)))
        w.update("x", 1)
        w.update("x", 2)
        assert changes == [(0, 1), (1, 2)]


class TestObserver:
    def test_subscribe_notify(self):
        obs = Observer()
        received = []
        obs.subscribe("evt", lambda e, d: received.append(d))
        asyncio.get_event_loop().run_until_complete(obs.notify("evt", "data1"))
        assert received == ["data1"]

    def test_unsubscribe(self):
        obs = Observer()
        received = []
        handler = lambda e, d: received.append(d)
        obs.subscribe("evt", handler)
        obs.unsubscribe("evt", handler)
        asyncio.get_event_loop().run_until_complete(obs.notify("evt", "data"))
        assert received == []


class TestRuntimeConsole:
    def test_register_command(self):
        console = RuntimeConsole()
        console.register_command("hello", lambda: "world")
        result = asyncio.get_event_loop().run_until_complete(console.execute("hello"))
        assert result == "world"

    def test_unknown_command(self):
        console = RuntimeConsole()
        result = asyncio.get_event_loop().run_until_complete(console.execute("xyz"))
        assert "Unknown" in result

    def test_history(self):
        console = RuntimeConsole()
        console.register_command("test", lambda: "ok")
        asyncio.get_event_loop().run_until_complete(console.execute("test"))
        assert len(console.history) == 1


