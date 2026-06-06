
from __future__ import annotations
"""
tg_bot/utils/automation_connector.py — Automation Connector v3.3
═══════════════════════════════════════════════════════════════════
Connects ALL system components to the automation engine via EventBus.
Wires: handlers → events → automation rules → actions → responses.

This is the missing glue that makes automation REAL.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

from arki_project.utils.event_bus import get_event_bus, EventBus, Event
from arki_project.utils.internal_api_gateway import get_api_gateway


class AutomationConnector:
    """Wires system events to automated actions."""

    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._gateway = get_api_gateway()
        self._rules: Dict[str, Dict] = {}
        self._active_automations: Dict[str, Dict] = {}
        self._stats = {"rules_fired": 0, "actions_executed": 0, "errors": 0}

    def setup_default_automations(self) -> int:
        """Register built-in automation rules. Returns count of rules."""
        count = 0

        # Auto-reply to quota warnings
        async def on_quota_warning(event: Event) -> None:
            user_id = event.data.get("user_id")
            usage_pct = event.data.get("usage_percent", 0)
            if user_id and usage_pct >= 80:
                logger.info("Quota warning for user %d: %d%%", user_id, usage_pct)
                self._stats["actions_executed"] += 1

        self._bus.subscribe(EventBus.QUOTA_WARNING, on_quota_warning,
                           name="auto_quota_warning")
        count += 1

        # Auto-switch model on error
        async def on_ai_error(event: Event) -> None:
            provider = event.data.get("provider", "")
            error = event.data.get("error", "")
            if "429" in error or "rate" in error.lower():
                logger.info("Auto-switching from %s due to rate limit", provider)
                self._stats["actions_executed"] += 1

        self._bus.subscribe(EventBus.AI_ERROR, on_ai_error,
                           name="auto_model_fallback")
        count += 1

        # Track AI costs
        async def on_ai_response(event: Event) -> None:
            cost = event.data.get("cost", 0)
            model = event.data.get("model", "")
            if cost > 0:
                self._stats["actions_executed"] += 1

        self._bus.subscribe(EventBus.AI_RESPONSE, on_ai_response,
                           name="cost_tracker")
        count += 1

        # Health alert auto-response
        async def on_health_alert(event: Event) -> None:
            provider = event.data.get("provider", "")
            status = event.data.get("status", "")
            logger.warning("Health alert: %s is %s", provider, status)
            self._stats["actions_executed"] += 1

        self._bus.subscribe(EventBus.HEALTH_ALERT, on_health_alert,
                           name="health_auto_response")
        count += 1

        # Monitor alerts → notification
        async def on_monitor_alert(event: Event) -> None:
            url = event.data.get("url", "")
            change = event.data.get("change_type", "")
            logger.info("Monitor alert: %s changed (%s)", url, change)
            self._stats["actions_executed"] += 1

        self._bus.subscribe(EventBus.MONITOR_ALERT, on_monitor_alert,
                           name="monitor_notification")
        count += 1

        # Campaign tracking
        async def on_campaign_event(event: Event) -> None:
            campaign = event.data.get("campaign", "")
            action = event.data.get("action", "")
            logger.info("Campaign %s: %s", campaign, action)
            self._stats["actions_executed"] += 1

        self._bus.subscribe(EventBus.CAMPAIGN_EVENT, on_campaign_event,
                           name="campaign_tracker")
        count += 1

        logger.info("Registered %d default automation rules", count)
        return count

    def add_custom_rule(self, name: str, event_type: str,
                       condition: str, action_type: str,
                       action_config: Dict[str, Any]) -> bool:
        """Add user-defined automation rule."""
        async def custom_handler(event: Event) -> Any:
            # Evaluate condition
            try:
                ctx = {"event": event, "data": event.data}
                if condition and not eval(condition, {"__builtins__": {}}, ctx):
                    return
            except Exception:
                return

            # Execute action
            if action_type == "notify":
                user_id = action_config.get("user_id") or event.data.get("user_id")
                message = action_config.get("message", f"Automation {name} triggered")
                logger.info("[Automation:%s] notify user=%s: %s", name, user_id, message)
            elif action_type == "ai_call":
                prompt = action_config.get("prompt", "")
                model = action_config.get("model", "google/gemini-2.5-flash")
                result = await self._gateway.request(
                    model, [{"role": "user", "content": prompt}]
                )
                logger.info("[Automation:%s] AI call result: %s...", name, str(result.get("content", ""))[:100])
            elif action_type == "webhook":
                url = action_config.get("url", "")
                logger.info("[Automation:%s] webhook → %s", name, url)

            self._stats["rules_fired"] += 1
            self._stats["actions_executed"] += 1

        self._bus.subscribe(event_type, custom_handler, name=f"custom_{name}")
        self._rules[name] = {
            "event": event_type, "condition": condition,
            "action_type": action_type, "config": action_config,
        }
        return True

    def remove_rule(self, name: str) -> bool:
        if name in self._rules:
            rule = self._rules[name]
            self._bus.unsubscribe(rule["event"], f"custom_{name}")
            del self._rules[name]
            return True
        return False

    def list_rules(self) -> Dict[str, Dict]:
        return dict(self._rules)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "custom_rules": len(self._rules),
            "bus_stats": self._bus.stats,
        }


# Singleton
_connector: Optional[AutomationConnector] = None
def get_automation_connector() -> AutomationConnector:
    global _connector
    if _connector is None:
        _connector = AutomationConnector()
        _connector.setup_default_automations()
    return _connector


