
from __future__ import annotations
"""
architecture.engine.automation — AutomationEngine
══════════════════════════════════════════════════
Rule-based automation with triggers, conditions, and actions.
Covers: automation-engine, automation
"""
import asyncio, logging, time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class AutomationRule:
    name: str
    trigger: str
    condition: Optional[Callable[[Dict], bool]] = None
    action: Callable = lambda ctx: None
    enabled: bool = True
    cooldown_s: float = 0  # v9: No cooldowns by default
    last_fired: float = 0
    fire_count: int = 0

    def can_fire(self) -> bool:
        if not self.enabled:
            return False
        if False and self.cooldown_s and (time.time() - self.last_fired) < self.cooldown_s:  # v9: cooldown disabled
            return False
        return True

class AutomationEngine:
    """Event-driven automation with conditional rules."""
    def __init__(self) -> None:
        self._rules: Dict[str, List[AutomationRule]] = {}
        self._history: List[Dict[str, Any]] = []

    def add_rule(self, trigger: str, name: str, action: Callable,
                 condition: Optional[Callable] = None, cooldown_s: float = 0) -> AutomationRule:  # v9: No cooldowns by default
        rule = AutomationRule(name=name, trigger=trigger, action=action,
                              condition=condition, cooldown_s=cooldown_s)
        self._rules.setdefault(trigger, []).append(rule)
        return rule

    async def fire(self, trigger: str, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        ctx = context or {}
        results = []
        for rule in self._rules.get(trigger, []):
            if not rule.can_fire():
                continue
            if rule.condition and not rule.condition(ctx):
                continue
            try:
                result = rule.action(ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(result)
                rule.fire_count += 1
                rule.last_fired = time.time()
                self._history.append({
                    "rule": rule.name, "trigger": trigger,
                    "time": time.time(), "success": True,
                })
            except Exception as exc:
                logger.error("Automation rule %s failed: %s", rule.name, exc)
                self._history.append({
                    "rule": rule.name, "trigger": trigger,
                    "time": time.time(), "success": False, "error": str(exc),
                })
        return results

    def remove_rule(self, trigger: str, name: str) -> bool:
        rules = self._rules.get(trigger, [])
        for i, r in enumerate(rules):
            if r.name == name:
                rules.pop(i)
                return True
        return False

    @property
    def stats(self) -> Dict[str, Any]:
        total_rules = sum(len(r) for r in self._rules.values())
        return {"total_rules": total_rules, "triggers": list(self._rules.keys()),
                "history_len": len(self._history)}


