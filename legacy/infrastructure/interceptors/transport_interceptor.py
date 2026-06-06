
from __future__ import annotations
"""InfraTransportInterceptor — Intercept transport-level data."""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class InfraTransportInterceptor:
    """InfraTransportInterceptor — Intercept transport-level data."""

    def __init__(self) -> None:
        self._rules: List[Dict] = []
        self._blocked: List[Dict] = []
        self._stats = {"intercepted": 0, "passed": 0, "blocked": 0}
        logger.info("InfraTransportInterceptor initialized")

    def add_rule(self, name: str, condition: Any, *, action: str = "pass") -> None:
        """Add an interception rule."""
        self._rules.append({"name": name, "condition": condition, "action": action})

    async def intercept(self, data: Dict) -> Dict:
        """Process data through all interception rules."""
        self._stats["intercepted"] += 1
        result = dict(data)

        for rule in self._rules:
            try:
                cond = rule["condition"]
                matches = cond(result) if callable(cond) else False
                if matches and rule["action"] == "block":
                    self._stats["blocked"] += 1
                    self._blocked.append({"rule": rule["name"], "data_keys": list(result.keys()), "at": time.time()})
                    return {"intercepted": True, "blocked": True, "rule": rule["name"]}
                elif matches and rule["action"] == "transform":
                    result["_transformed_by"] = rule["name"]
            except Exception as e:
                logger.warning("InfraTransportInterceptor rule '%s' error: %s", rule["name"], e)

        self._stats["passed"] += 1
        return {"intercepted": True, "blocked": False, "data": result}

    def get_blocked(self, limit: int = 20) -> List[Dict]:
        return self._blocked[-limit:]

    def clear_rules(self) -> int:
        count = len(self._rules)
        self._rules.clear()
        return count

    def get_stats(self) -> dict:
        return {**self._stats, "rules": len(self._rules)}


