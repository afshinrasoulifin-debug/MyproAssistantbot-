
from __future__ import annotations
"""
tests/test_marketing_automation_deep.py — Tests for marketing automation service
════════════════════════════════════════════════════════════════════════════════
Tests: MarketingEventBus, MarketingAutomationService, ScheduledTask.
"""

import asyncio
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_async(coro):
    """Helper to run async functions in sync test."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── EventBus Tests ──────────────────────────────────────────

class TestMarketingEventBus(unittest.TestCase):
    """Test the lightweight async event bus."""

    def _make_bus(self):
        from services.marketing_automation_service import MarketingEventBus
        return MarketingEventBus()

    def test_create_bus(self):
        bus = self._make_bus()
        self.assertIsNotNone(bus)
        self.assertEqual(len(bus._history), 0)

    def test_subscribe_handler(self):
        bus = self._make_bus()
        async def handler(data): pass
        bus.subscribe("test_event", handler)
        self.assertIn(handler, bus._handlers["test_event"])

    def test_unsubscribe_handler(self):
        bus = self._make_bus()
        async def handler(data): pass
        bus.subscribe("test_event", handler)
        bus.unsubscribe("test_event", handler)
        self.assertNotIn(handler, bus._handlers["test_event"])

    def test_publish_calls_handler(self):
        bus = self._make_bus()
        results = []
        async def handler(data):
            results.append(data)
        bus.subscribe("test_event", handler)
        run_async(bus.publish("test_event", {"key": "value"}))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["key"], "value")

    def test_publish_multiple_handlers(self):
        bus = self._make_bus()
        results = []
        async def h1(data): results.append("h1")
        async def h2(data): results.append("h2")
        bus.subscribe("test", h1)
        bus.subscribe("test", h2)
        run_async(bus.publish("test"))
        self.assertEqual(sorted(results), ["h1", "h2"])

    def test_publish_no_handler_no_crash(self):
        bus = self._make_bus()
        run_async(bus.publish("nonexistent_event", {"data": 1}))

    def test_history_recorded(self):
        bus = self._make_bus()
        run_async(bus.publish("event_a", {"x": 1}))
        run_async(bus.publish("event_b", {"y": 2}))
        history = bus.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["type"], "event_a")
        self.assertEqual(history[1]["type"], "event_b")

    def test_history_filter_by_type(self):
        bus = self._make_bus()
        run_async(bus.publish("a"))
        run_async(bus.publish("b"))
        run_async(bus.publish("a"))
        history = bus.get_history(event_type="a")
        self.assertEqual(len(history), 2)

    def test_history_limit(self):
        bus = self._make_bus()
        for i in range(10):
            run_async(bus.publish("evt", {"i": i}))
        history = bus.get_history(limit=3)
        self.assertEqual(len(history), 3)
        # Should be last 3
        self.assertEqual(history[0]["data"]["i"], 7)

    def test_history_max_cap(self):
        bus = self._make_bus()
        bus._max_history = 5
        for i in range(10):
            run_async(bus.publish("evt", {"i": i}))
        self.assertLessEqual(len(bus._history), 5)

    def test_handler_exception_doesnt_crash(self):
        bus = self._make_bus()
        async def bad_handler(data):
            raise ValueError("boom")
        async def good_handler(data):
            pass
        bus.subscribe("test", bad_handler)
        bus.subscribe("test", good_handler)
        # Should not raise
        run_async(bus.publish("test"))

    def test_event_timestamp_is_iso(self):
        bus = self._make_bus()
        run_async(bus.publish("test"))
        ts = bus._history[0]["timestamp"]
        # Should be parseable ISO format
        datetime.fromisoformat(ts)


# ── ScheduledTask Tests ──────────────────────────────────────

class TestScheduledTask(unittest.TestCase):
    """Test ScheduledTask dataclass."""

    def test_defaults(self):
        from services.marketing_automation_service import ScheduledTask
        t = ScheduledTask()
        self.assertEqual(t.name, "")
        self.assertEqual(t.interval_hours, 24.0)
        self.assertIsNone(t.last_run)
        self.assertTrue(t.enabled)

    def test_custom_values(self):
        from services.marketing_automation_service import ScheduledTask
        t = ScheduledTask(name="hunt", interval_hours=6.0, enabled=False)
        self.assertEqual(t.name, "hunt")
        self.assertEqual(t.interval_hours, 6.0)
        self.assertFalse(t.enabled)


# ── MarketingAutomationService Tests ─────────────────────────

class TestMarketingAutomationService(unittest.TestCase):
    """Test the main automation service."""

    def _make_service(self, admin_ids=None):
        from services.marketing_automation_service import MarketingAutomationService
        return MarketingAutomationService(admin_user_ids=admin_ids)

    def test_create_service(self):
        svc = self._make_service()
        self.assertIsNotNone(svc)
        self.assertFalse(svc._running)

    def test_admin_check(self):
        svc = self._make_service(admin_ids={123, 456})
        self.assertTrue(svc.is_admin(123))
        self.assertTrue(svc.is_admin(456))
        self.assertFalse(svc.is_admin(789))

    def test_require_admin_pass(self):
        svc = self._make_service(admin_ids={123})
        self.assertTrue(svc.require_admin(123))

    def test_require_admin_fail(self):
        svc = self._make_service(admin_ids={123})
        self.assertFalse(svc.require_admin(999))

    def test_health_before_start(self):
        svc = self._make_service()
        health = run_async(svc.get_health())
        self.assertEqual(health["service"], "stopped")
        self.assertIsNone(health["uptime_hours"])
        self.assertEqual(health["tasks_executed"], 0)
        # All engines not initialized
        for eng_name, status in health["engines"].items():
            self.assertEqual(status, "not_initialized", f"Engine '{eng_name}' should be not_initialized")

    def test_event_bus_exists(self):
        svc = self._make_service()
        self.assertIsNotNone(svc.event_bus)

    def test_enable_disable_task(self):
        svc = self._make_service()
        # Setup scheduled tasks
        svc._setup_scheduled_tasks()
        tasks = svc.list_tasks()
        if tasks:
            key = tasks[0]["key"]
            # Disable
            self.assertTrue(svc.disable_task(key))
            self.assertFalse(svc._scheduled_tasks[key].enabled)
            # Re-enable
            self.assertTrue(svc.enable_task(key))
            self.assertTrue(svc._scheduled_tasks[key].enabled)

    def test_enable_nonexistent_task(self):
        svc = self._make_service()
        self.assertFalse(svc.enable_task("nonexistent"))

    def test_disable_nonexistent_task(self):
        svc = self._make_service()
        self.assertFalse(svc.disable_task("nonexistent"))

    def test_list_tasks_structure(self):
        svc = self._make_service()
        svc._setup_scheduled_tasks()
        tasks = svc.list_tasks()
        self.assertIsInstance(tasks, list)
        for t in tasks:
            self.assertIn("key", t)
            self.assertIn("name", t)
            self.assertIn("enabled", t)
            self.assertIn("interval_hours", t)
            self.assertIn("last_run", t)

    def test_run_task_now_nonexistent(self):
        svc = self._make_service()
        result = run_async(svc.run_task_now("nonexistent"))
        self.assertFalse(result)

    def test_pipeline_no_campaign_manager(self):
        svc = self._make_service()
        result = run_async(svc.run_full_pipeline(user_id=1))
        self.assertIn("error", result)

    def test_dashboard_minimal(self):
        svc = self._make_service()
        dashboard = run_async(svc.get_dashboard())
        self.assertIn("health", dashboard)


# ── Integration: EventBus + Service ──────────────────────────

class TestEventBusIntegration(unittest.TestCase):
    """Test event flow through the service."""

    def test_service_event_bus_publish(self):
        from services.marketing_automation_service import MarketingAutomationService
        svc = MarketingAutomationService()
        captured = []
        async def handler(data):
            captured.append(data)
        svc.event_bus.subscribe("test_flow", handler)
        run_async(svc.event_bus.publish("test_flow", {"source": "test"}))
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["source"], "test")


if __name__ == "__main__":
    unittest.main()


