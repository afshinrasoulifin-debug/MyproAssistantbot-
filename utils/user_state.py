
"""
utils/user_state.py — Lightweight user state management
No database dependency — in-memory with optional persistence.
"""
import time
from typing import Any, Dict, Optional

# Per-user config: model, persona, autotune, voice
_user_configs: Dict[int, Dict[str, Any]] = {}

# Pending actions: when a button is clicked that needs text input
_pending_actions: Dict[int, Dict[str, Any]] = {}

DEFAULTS = {
    "model": "cohere-command",
    "persona": "assistant",
    "autotune": True,
    "voice": "Zephyr",
}


def get_config(user_id: int) -> dict:
    if user_id not in _user_configs:
        _user_configs[user_id] = dict(DEFAULTS)
    return _user_configs[user_id]


def set_config(user_id: int, key: str, value: Any) -> None:
    cfg = get_config(user_id)
    cfg[key] = value


def set_pending(user_id: int, action: str, meta: Optional[dict] = None) -> None:
    _pending_actions[user_id] = {"action": action, "ts": time.time(), "meta": meta or {}}


def get_pending(user_id: int) -> Optional[Dict[str, Any]]:
    p = _pending_actions.get(user_id)
    if p and time.time() - p["ts"] < 300:  # 5 min expiry
        return p
    _pending_actions.pop(user_id, None)
    return None


def clear_pending(user_id: int) -> None:
    _pending_actions.pop(user_id, None)


