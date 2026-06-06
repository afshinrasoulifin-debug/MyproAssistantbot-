
"""
Run architecture tests without pytest — matching REAL component APIs.
EventBus.publish is async, handlers receive BusMessage objects.
"""
import sys
import traceback
import asyncio


import logging
logger = logging.getLogger(__name__)
sys.path.insert(0, "/work/temp/arki_project")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def run_test(name, func):
    try:
        result = func()
        if asyncio.iscoroutine(result):
            loop.run_until_complete(result)
        logger.info(f"  ✅ {name}")
        return True
    except Exception as e:
        logger.info(f"  ❌ {name}: {e}")
        traceback.print_exc()
        return False

total = 0
passed = 0
failed = 0

# ═══ Core Tests ═══
logger.info("\n── architecture.core ──")

def test_config():
    from core.architecture.core.config import AdvancedConfig
    c = AdvancedConfig()
    c.define("k", "v")
    assert c.get("k") == "v"
    assert c.get("nope", "d") == "d"
total += 1; r = run_test("AdvancedConfig define/get", test_config); passed += r; failed += (not r)

def test_feature_flags():
    from core.architecture.core.config import FeatureFlags
    f = FeatureFlags()
    f.register("x", enabled=True)
    assert f.is_enabled("x") is True
    f.register("y", enabled=False)
    assert f.is_enabled("y") is False
    assert f.is_enabled("nope") is False
total += 1; r = run_test("FeatureFlags enable/disable", test_feature_flags); passed += r; failed += (not r)

def test_hooks():
    from core.architecture.core.hooks import RuntimeHooks
    h = RuntimeHooks()
    results = []
    h.register("ev", lambda event, ctx: results.append(1), name="hook1")
    async def run():
        await h.trigger("ev")
    loop.run_until_complete(run())
    assert 1 in results
    return  # don't re-run as coroutine
total += 1; r = run_test("RuntimeHooks trigger", test_hooks); passed += r; failed += (not r)

# ═══ Transport Tests ═══
logger.info("\n── architecture.transport ──")

def test_eventbus_pubsub():
    from core.architecture.transport.bus import EventBus
    bus = EventBus()
    received = []
    bus.subscribe("test.event", lambda msg: received.append(msg.payload))
    async def run():
        await bus.publish("test.event", {"key": "value"})
    loop.run_until_complete(run())
    assert len(received) == 1
    assert received[0]["key"] == "value"
total += 1; r = run_test("EventBus pub/sub", test_eventbus_pubsub); passed += r; failed += (not r)

def test_eventbus_multi():
    from core.architecture.transport.bus import EventBus
    bus = EventBus()
    results = []
    bus.subscribe("evt", lambda msg: results.append("A"))
    bus.subscribe("evt", lambda msg: results.append("B"))
    loop.run_until_complete(bus.publish("evt", {}))
    assert results == ["A", "B"]
total += 1; r = run_test("EventBus multi-sub", test_eventbus_multi); passed += r; failed += (not r)

def test_eventbus_no_crosstalk():
    from core.architecture.transport.bus import EventBus
    bus = EventBus()
    results = []
    bus.subscribe("evt1", lambda msg: results.append("1"))
    bus.subscribe("evt2", lambda msg: results.append("2"))
    loop.run_until_complete(bus.publish("evt1", {}))
    assert results == ["1"]
total += 1; r = run_test("EventBus no crosstalk", test_eventbus_no_crosstalk); passed += r; failed += (not r)

def test_eventbus_unsubscribe():
    from core.architecture.transport.bus import EventBus
    bus = EventBus()
    results = []
    handler = lambda msg: results.append("x")
    bus.subscribe("evt", handler)
    bus.unsubscribe("evt", handler)
    loop.run_until_complete(bus.publish("evt", {}))
    assert results == []
total += 1; r = run_test("EventBus unsubscribe", test_eventbus_unsubscribe); passed += r; failed += (not r)

def test_eventbus_stats():
    from core.architecture.transport.bus import EventBus
    bus = EventBus()
    bus.subscribe("evt", lambda msg: None)
    loop.run_until_complete(bus.publish("evt", {}))
    loop.run_until_complete(bus.publish("evt", {}))
    assert bus.stats["total_messages"] == 2
total += 1; r = run_test("EventBus stats count", test_eventbus_stats); passed += r; failed += (not r)

def test_task_router():
    from core.architecture.transport.router import TaskRouter
    router = TaskRouter()
    results = []
    router.route("send_email", lambda data: results.append(data))
    handler = router.resolve("send_email")
    assert handler is not None
total += 1; r = run_test("TaskRouter route/resolve", test_task_router); passed += r; failed += (not r)

def test_dispatcher():
    from core.architecture.transport.dispatcher import Dispatcher
    disp = Dispatcher()
    results = []
    disp.register("action1", lambda d: results.append(d))
    loop.run_until_complete(disp.dispatch("action1", {"data": 123}))
    assert len(results) == 1
total += 1; r = run_test("Dispatcher dispatch", test_dispatcher); passed += r; failed += (not r)

def test_secure_channel():
    from core.architecture.transport.channel import SecureChannel
    ch = SecureChannel()
    ch.create_channel("test")
    msg = ch.send("test", "hello", "sender1")
    assert msg.content is not None  # content is encrypted or stored
total += 1; r = run_test("SecureChannel send", test_secure_channel); passed += r; failed += (not r)

# ═══ Engine Tests ═══
logger.info("\n── architecture.engine ──")

def test_workflow_engine():
    from core.architecture.engine.workflow import WorkflowEngine
    engine = WorkflowEngine()
    run = engine.create()
    engine.add_step(run, "step1", lambda ctx: "done1")
    engine.add_step(run, "step2", lambda ctx: "done2")
    assert len(run.steps) == 2
total += 1; r = run_test("WorkflowEngine create+add_step", test_workflow_engine); passed += r; failed += (not r)

def test_workflow_execute():
    from core.architecture.engine.workflow import WorkflowEngine
    engine = WorkflowEngine()
    run = engine.create()
    engine.add_step(run, "double", lambda ctx: ctx.update({"val": 2}))
    result = loop.run_until_complete(engine.execute(run))
    assert result.workflow_id is not None
total += 1; r = run_test("WorkflowEngine execute", test_workflow_execute); passed += r; failed += (not r)

def test_execution_engine():
    from core.architecture.engine.execution import ExecutionEngine
    engine = ExecutionEngine()
    result = loop.run_until_complete(engine.execute(lambda: 42, name="test"))
    assert result.result == 42
    assert result.success is True
total += 1; r = run_test("ExecutionEngine execute fn", test_execution_engine); passed += r; failed += (not r)

def test_smart_engine():
    from core.architecture.engine.smart import SmartEngine
    engine = SmartEngine()
    engine.register_strategy("quick_response", lambda ctx: "result_ok")
    result = engine.execute_smart(1, {"type": "simple"})
    assert result == "result_ok"
total += 1; r = run_test("SmartEngine strategy", test_smart_engine); passed += r; failed += (not r)

# ═══ Monitor Tests ═══
logger.info("\n── architecture.monitor ──")

def test_telemetry_record():
    from core.architecture.monitor.telemetry import TelemetryMonitor
    tm = TelemetryMonitor()
    tm.record("api.latency", 0.5)
    tm.record("api.latency", 1.2)
    tm.record("api.latency", 0.8)
    agg = tm.aggregate("api.latency")
    assert agg["count"] == 3
    assert 0.5 <= agg["mean"] <= 1.2
    assert agg["min"] == 0.5
    assert agg["max"] == 1.2
total += 1; r = run_test("TelemetryMonitor record+aggregate", test_telemetry_record); passed += r; failed += (not r)

def test_telemetry_counter():
    from core.architecture.monitor.telemetry import TelemetryMonitor
    tm = TelemetryMonitor()
    tm.increment("requests")
    tm.increment("requests")
    tm.increment("requests")
    assert tm.get_counter("requests") == 3
total += 1; r = run_test("TelemetryMonitor counter", test_telemetry_counter); passed += r; failed += (not r)

def test_telemetry_gauge():
    from core.architecture.monitor.telemetry import TelemetryMonitor
    tm = TelemetryMonitor()
    tm.gauge("memory_mb", 128.5)
    assert tm.get_gauge("memory_mb") == 128.5
total += 1; r = run_test("TelemetryMonitor gauge", test_telemetry_gauge); passed += r; failed += (not r)

def test_telemetry_report():
    from core.architecture.monitor.telemetry import TelemetryMonitor
    tm = TelemetryMonitor()
    tm.increment("test_counter")
    tm.gauge("test_gauge", 1.0)
    tm.record("test_metric", 0.5)
    report = tm.report()
    assert "counters" in report
    assert "gauges" in report
    assert "metrics" in report
total += 1; r = run_test("TelemetryMonitor report structure", test_telemetry_report); passed += r; failed += (not r)

def test_telemetry_reset():
    from core.architecture.monitor.telemetry import TelemetryMonitor
    tm = TelemetryMonitor()
    tm.increment("x")
    tm.gauge("y", 1)
    tm.record("z", 0.5)
    tm.reset()
    assert tm.get_counter("x") == 0
    assert tm.get_gauge("y") is None
total += 1; r = run_test("TelemetryMonitor reset", test_telemetry_reset); passed += r; failed += (not r)

def test_diagnostics_trace():
    from core.architecture.monitor.telemetry import DiagnosticsMonitor
    dm = DiagnosticsMonitor()
    dm.trace("ai_request", duration_s=1.5, success=True, model="gemini")
    traces = dm.recent_traces()
    assert len(traces) == 1
    assert traces[0]["operation"] == "ai_request"
total += 1; r = run_test("DiagnosticsMonitor trace", test_diagnostics_trace); passed += r; failed += (not r)

def test_diagnostics_errors():
    from core.architecture.monitor.telemetry import DiagnosticsMonitor
    dm = DiagnosticsMonitor()
    dm.trace("api_call", duration_s=0.1, success=False)
    dm.trace("api_call", duration_s=0.2, success=True)
    report = dm.diagnostic_report()
    assert report["traces"] == 2
    errors = report["recent_errors"]
    assert len(errors) == 1
total += 1; r = run_test("DiagnosticsMonitor error tracking", test_diagnostics_errors); passed += r; failed += (not r)

def test_health_monitor_healthy():
    from core.architecture.monitor.health import HealthMonitor
    hm = HealthMonitor()
    hm.register("db", lambda: True)
    result = loop.run_until_complete(hm.check_all())
    assert result["db"] == "healthy"
total += 1; r = run_test("HealthMonitor healthy check", test_health_monitor_healthy); passed += r; failed += (not r)

def test_health_monitor_unhealthy():
    from core.architecture.monitor.health import HealthMonitor
    hm = HealthMonitor()
    def failing():
        raise RuntimeError("DB down!")
    hm.register("db", failing)
    result = loop.run_until_complete(hm.check_all())
    assert result["db"] == "unhealthy"
total += 1; r = run_test("HealthMonitor unhealthy check", test_health_monitor_unhealthy); passed += r; failed += (not r)

def test_health_is_healthy():
    from core.architecture.monitor.health import HealthMonitor
    hm = HealthMonitor()
    hm.register("ok", lambda: True)
    loop.run_until_complete(hm.check_all())
    assert hm.is_healthy()
total += 1; r = run_test("HealthMonitor is_healthy()", test_health_is_healthy); passed += r; failed += (not r)

def test_health_unhealthy_callback():
    from core.architecture.monitor.health import HealthMonitor
    hm = HealthMonitor()
    alerts = []
    hm.on_unhealthy(lambda name, err: alerts.append(name))
    def bad():
        raise RuntimeError("fail")
    hm.register("bad", bad)
    loop.run_until_complete(hm.check_all())
    assert "bad" in alerts
total += 1; r = run_test("HealthMonitor on_unhealthy callback", test_health_unhealthy_callback); passed += r; failed += (not r)

def test_watcher():
    from core.architecture.monitor.health import Watcher
    w = Watcher()
    w.watch("counter", 0)
    assert w.get("counter") == 0
    changed = w.update("counter", 5)
    assert changed is True
    assert w.get("counter") == 5
total += 1; r = run_test("Watcher watch/update/get", test_watcher); passed += r; failed += (not r)

def test_watcher_no_change():
    from core.architecture.monitor.health import Watcher
    w = Watcher()
    w.watch("val", 10)
    changed = w.update("val", 10)
    assert changed is False
total += 1; r = run_test("Watcher no-change returns False", test_watcher_no_change); passed += r; failed += (not r)

def test_watcher_callback():
    from core.architecture.monitor.health import Watcher
    w = Watcher()
    changes = []
    w.watch("x", 0)
    w.on_change("x", lambda k, old, new: changes.append((old, new)))
    w.update("x", 1)
    w.update("x", 2)
    assert changes == [(0, 1), (1, 2)]
total += 1; r = run_test("Watcher on_change callback", test_watcher_callback); passed += r; failed += (not r)

def test_observer():
    from core.architecture.monitor.health import Observer
    obs = Observer()
    received = []
    obs.subscribe("evt", lambda e, d: received.append(d))
    loop.run_until_complete(obs.notify("evt", "data1"))
    assert received == ["data1"]
total += 1; r = run_test("Observer subscribe/notify", test_observer); passed += r; failed += (not r)

def test_observer_unsubscribe():
    from core.architecture.monitor.health import Observer
    obs = Observer()
    received = []
    handler = lambda e, d: received.append(d)
    obs.subscribe("evt", handler)
    obs.unsubscribe("evt", handler)
    loop.run_until_complete(obs.notify("evt", "data"))
    assert received == []
total += 1; r = run_test("Observer unsubscribe", test_observer_unsubscribe); passed += r; failed += (not r)

def test_console():
    from core.architecture.monitor.console import RuntimeConsole
    console = RuntimeConsole()
    console.register_command("hello", lambda: "world")
    result = loop.run_until_complete(console.execute("hello"))
    assert result == "world"
total += 1; r = run_test("RuntimeConsole command", test_console); passed += r; failed += (not r)

def test_console_unknown():
    from core.architecture.monitor.console import RuntimeConsole
    console = RuntimeConsole()
    result = loop.run_until_complete(console.execute("xyz"))
    assert "Unknown" in result or "unknown" in result.lower()
total += 1; r = run_test("RuntimeConsole unknown command", test_console_unknown); passed += r; failed += (not r)

# ═══ Wiring Tests ═══
logger.info("\n── architecture.wiring ──")

def test_wire_no_errors():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
total += 1; r = run_test("wire_components no errors", test_wire_no_errors); passed += r; failed += (not r)

def test_wire_subscribers():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    bus = registry["event_bus"]
    total_subs = sum(len(v) for v in bus._subscribers.values())
    assert total_subs >= 10, f"Expected >= 10 subscribers, got {total_subs}"
total += 1; r = run_test("EventBus has >= 10 subscribers after wiring", test_wire_subscribers); passed += r; failed += (not r)

def test_wire_health_checks():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    hm = registry["health_monitor"]
    assert len(hm._checks) >= 3, f"Expected >= 3 health checks, got {len(hm._checks)}"
total += 1; r = run_test("HealthMonitor has >= 3 checks after wiring", test_wire_health_checks); passed += r; failed += (not r)

def test_wire_controller():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    ctrl = registry["controller"]
    assert len(ctrl._components) >= 4
total += 1; r = run_test("Controller manages >= 4 components", test_wire_controller); passed += r; failed += (not r)

def test_wire_admin_commands():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    console = registry["admin_console"]
    cmds = console.available_commands()
    assert "arch_status" in cmds
    assert "arch_health" in cmds
    assert "arch_metrics" in cmds
total += 1; r = run_test("AdminConsole has arch commands", test_wire_admin_commands); passed += r; failed += (not r)

def test_event_fires_telemetry():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    bus = registry["event_bus"]
    tel = registry["telemetry_monitor"]
    loop.run_until_complete(bus.publish("handler.complete", {
        "handler": "test", "user_id": 1, "duration_s": 0.5, "success": True,
    }))
    assert tel.get_counter("event.handler.complete") >= 1
total += 1; r = run_test("Event → TelemetryMonitor counter", test_event_fires_telemetry); passed += r; failed += (not r)

def test_event_fires_timing():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    bus = registry["event_bus"]
    tel = registry["telemetry_monitor"]
    loop.run_until_complete(bus.publish("handler.complete", {
        "handler": "test", "duration_s": 0.75, "success": True,
    }))
    agg = tel.aggregate("timing.handler.complete")
    assert agg is not None and agg["count"] >= 1
total += 1; r = run_test("Event → TelemetryMonitor timing", test_event_fires_timing); passed += r; failed += (not r)

def test_error_fires_diagnostics():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    bus = registry["event_bus"]
    diag = registry["diagnostics_monitor"]
    loop.run_until_complete(bus.publish("handler.error", {
        "handler": "fail", "user_id": 1, "duration_s": 1, "success": False, "error": "test",
    }))
    traces = diag.recent_traces()
    assert len(traces) >= 1
    assert traces[-1]["success"] is False
total += 1; r = run_test("Error → DiagnosticsMonitor trace", test_error_fires_diagnostics); passed += r; failed += (not r)

def test_middleware_fires_events():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components, ArchitectureMiddleware
    registry = init_architecture()
    wire_components(registry)
    mw = ArchitectureMiddleware(registry)
    tel = registry["telemetry_monitor"]

    class FakeEvent:
        class from_user:
            id = 42

    async def fake_handler(event, data):
        return "response"

    loop.run_until_complete(mw(fake_handler, FakeEvent(), {}))
    assert tel.get_counter("event.handler.start") >= 1
    assert tel.get_counter("event.handler.complete") >= 1
total += 1; r = run_test("Middleware → EventBus → Telemetry", test_middleware_fires_events); passed += r; failed += (not r)

def test_middleware_watcher_requests():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components, ArchitectureMiddleware
    registry = init_architecture()
    wire_components(registry)
    mw = ArchitectureMiddleware(registry)
    watcher = registry["watcher"]

    class FakeEvent:
        class from_user:
            id = 1

    async def handler(e, d):
        return "ok"

    for _ in range(3):
        loop.run_until_complete(mw(handler, FakeEvent(), {}))

    assert watcher.get("total_requests") == 3
    assert watcher.get("total_errors") == 0
total += 1; r = run_test("Middleware → Watcher request count", test_middleware_watcher_requests); passed += r; failed += (not r)

def test_middleware_error_tracking():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components, ArchitectureMiddleware
    registry = init_architecture()
    wire_components(registry)
    mw = ArchitectureMiddleware(registry)
    watcher = registry["watcher"]

    class FakeEvent:
        class from_user:
            id = 1

    async def failing(e, d):
        raise ValueError("boom")

    try:
        loop.run_until_complete(mw(failing, FakeEvent(), {}))
    except ValueError:
        pass

    assert watcher.get("total_errors") == 1
total += 1; r = run_test("Middleware → Watcher error count", test_middleware_error_tracking); passed += r; failed += (not r)

# ═══ Automation Tests ═══
logger.info("\n── architecture.automations ──")

def test_perf_watchdog_slow():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    from core.architecture.automations import PerformanceWatchdog
    registry = init_architecture()
    wire_components(registry)
    wd = PerformanceWatchdog(registry, slow_threshold_s=1.0)
    wd.start()
    bus = registry["event_bus"]
    loop.run_until_complete(bus.publish("handler.complete", {
        "handler": "slow", "user_id": 1, "duration_s": 5.0, "success": True,
    }))
    assert len(wd._slow_alerts) == 1
    assert wd._slow_alerts[0]["handler"] == "slow"
total += 1; r = run_test("PerformanceWatchdog detects slow handler", test_perf_watchdog_slow); passed += r; failed += (not r)

def test_perf_watchdog_fast():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    from core.architecture.automations import PerformanceWatchdog
    registry = init_architecture()
    wire_components(registry)
    wd = PerformanceWatchdog(registry, slow_threshold_s=1.0)
    wd.start()
    bus = registry["event_bus"]
    loop.run_until_complete(bus.publish("handler.complete", {
        "handler": "fast", "user_id": 1, "duration_s": 0.1, "success": True,
    }))
    assert len(wd._slow_alerts) == 0
total += 1; r = run_test("PerformanceWatchdog no false alarm", test_perf_watchdog_fast); passed += r; failed += (not r)

def test_perf_watchdog_stats():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    from core.architecture.automations import PerformanceWatchdog
    registry = init_architecture()
    wire_components(registry)
    wd = PerformanceWatchdog(registry, slow_threshold_s=10.0)
    wd.start()
    bus = registry["event_bus"]
    for i in range(5):
        loop.run_until_complete(bus.publish("handler.complete", {
            "handler": "my_handler", "user_id": 1, "duration_s": 0.1 * (i + 1),
        }))
    stats = wd.get_handler_stats()
    assert "my_handler" in stats
    assert stats["my_handler"]["count"] == 5
total += 1; r = run_test("PerformanceWatchdog handler stats", test_perf_watchdog_stats); passed += r; failed += (not r)

def test_usage_analytics_users():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    from core.architecture.automations import UsageAnalytics
    registry = init_architecture()
    wire_components(registry)
    ua = UsageAnalytics(registry)
    ua.start()
    bus = registry["event_bus"]
    for uid in [1, 1, 2, 3, 1]:
        loop.run_until_complete(bus.publish("handler.complete", {
            "handler": "chat", "user_id": uid,
        }))
    top = ua.top_users(3)
    assert len(top) > 0
    assert top[0][0] == 1  # User 1 has most requests
    assert top[0][1] == 3
total += 1; r = run_test("UsageAnalytics tracks users", test_usage_analytics_users); passed += r; failed += (not r)

def test_usage_analytics_handlers():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    from core.architecture.automations import UsageAnalytics
    registry = init_architecture()
    wire_components(registry)
    ua = UsageAnalytics(registry)
    ua.start()
    bus = registry["event_bus"]
    loop.run_until_complete(bus.publish("handler.complete", {"handler": "chat", "user_id": 1}))
    loop.run_until_complete(bus.publish("handler.complete", {"handler": "chat", "user_id": 2}))
    loop.run_until_complete(bus.publish("handler.complete", {"handler": "search", "user_id": 1}))
    top = ua.top_handlers(5)
    assert top[0][0] == "chat"
    assert top[0][1] == 2
total += 1; r = run_test("UsageAnalytics tracks handlers", test_usage_analytics_handlers); passed += r; failed += (not r)

def test_auto_health_check():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    from core.architecture.automations import AutoHealthCheck
    registry = init_architecture()
    wire_components(registry)
    ahc = AutoHealthCheck(registry)
    assert ahc.stats["checks"] == 0
    # Run a single check
    loop.run_until_complete(ahc._check())
    assert ahc._check_count == 1
total += 1; r = run_test("AutoHealthCheck single check", test_auto_health_check); passed += r; failed += (not r)

# ═══ Integration Tests ═══
logger.info("\n── Full Integration ──")

def test_boot_architecture():
    from core.architecture.setup import boot_architecture
    registry = boot_architecture()
    count = len(registry)
    assert count >= 100, f"Expected >= 100 components, got {count}"
    return count
total += 1
count_result = run_test("boot_architecture()", test_boot_architecture)
passed += count_result; failed += (not count_result)

def test_all_components_not_none():
    from core.architecture.setup import init_architecture
    registry = init_architecture()
    none_comps = [n for n, c in registry.items() if c is None]
    assert len(none_comps) == 0, f"None components: {none_comps}"
total += 1; r = run_test("All components are real objects", test_all_components_not_none); passed += r; failed += (not r)

def test_end_to_end_flow():
    from core.architecture.setup import init_architecture
    registry = init_architecture()  # already wires components
    bus = registry["event_bus"]
    tel = registry["telemetry_monitor"]
    diag = registry["diagnostics_monitor"]

    for i in range(10):
        loop.run_until_complete(bus.publish("handler.complete", {
            "handler": f"handler_{i % 3}",
            "user_id": 100 + i,
            "duration_s": 0.1 * (i + 1),
            "success": i != 7,
        }))

    count = tel.get_counter("event.handler.complete")
    assert count == 10, f"Expected 10 telemetry records, got {count}"
    traces = diag.recent_traces()
    assert len(traces) == 10
    error_traces = [t for t in traces if not t["success"]]
    assert len(error_traces) == 1
total += 1; r = run_test("End-to-end: 10 events → telemetry + diagnostics", test_end_to_end_flow); passed += r; failed += (not r)

def test_admin_console_returns_data():
    from core.architecture.setup import init_architecture
    from core.architecture.wiring import wire_components
    registry = init_architecture()
    wire_components(registry)
    console = registry["admin_console"]
    result = loop.run_until_complete(console.execute("arch_status"))
    assert "components" in result
total += 1; r = run_test("AdminConsole arch_status returns data", test_admin_console_returns_data); passed += r; failed += (not r)

# ═══ Final Report ═══
logger.info(f"\n{'='*60}")
logger.info(f"  RESULTS: {passed} passed, {failed} failed, {total} total")
logger.info(f"{'='*60}")

if failed > 0:
    sys.exit(1)
else:
    logger.info("  🎉 ALL TESTS PASSED!")


