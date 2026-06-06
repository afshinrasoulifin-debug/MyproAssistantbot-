
from __future__ import annotations
"""APEX Model Selection Routes."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelSelectRouter:
    """Handle model selection and tier routing for APEX."""

    def __init__(self) -> None:
        self._models: Dict[str, Dict] = {}
        self._user_prefs: Dict[int, str] = {}

    def register_model(self, key: str, info: Dict) -> None:
        self._models[key] = info

    def get_model(self, key: str) -> Optional[Dict]:
        return self._models.get(key)

    def select_for_task(self, task_type: str, *, tier: str = "pro") -> Optional[str]:
        """Select optimal model for a task type and tier."""
        candidates = []
        for key, info in self._models.items():
            if info.get("tier", "").lower() == tier.lower():
                if task_type in info.get("capabilities", []) or not info.get("capabilities"):
                    candidates.append((key, info.get("priority", 0)))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        return None

    def set_user_preference(self, user_id: int, model_key: str) -> None:
        self._user_prefs[user_id] = model_key

    def get_user_preference(self, user_id: int) -> Optional[str]:
        return self._user_prefs.get(user_id)

    def list_by_tier(self, tier: str) -> List[str]:
        return [k for k, v in self._models.items() if v.get("tier", "").lower() == tier.lower()]

    def get_stats(self) -> Dict:
        tiers = {}
        for v in self._models.values():
            t = v.get("tier", "unknown")
            tiers[t] = tiers.get(t, 0) + 1
        return {"total": len(self._models), "tiers": tiers, "user_prefs": len(self._user_prefs)}


