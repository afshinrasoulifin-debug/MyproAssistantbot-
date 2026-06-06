
"""
telegram_parts/state_manager.py — Victor conversation state
Extracted from cmd_victor() to reduce complexity.
"""
from __future__ import annotations
from typing import Any, Dict, Optional


class VictorState:
    """Manages conversation state for Victor commands.
    
    Reduces the many local variable checks in cmd_victor() into
    a structured state object.
    """
    
    _states: Dict[int, Dict] = {}
    
    @classmethod
    def get(cls, user_id: int) -> Dict[str, Any]:
        if user_id not in cls._states:
            cls._states[user_id] = {
                "section": "main",
                "waiting_for": None,
                "context": {},
                "last_command": None,
            }
        return cls._states[user_id]
    
    @classmethod
    def set_section(cls, user_id: int, section: str) -> None:
        state = cls.get(user_id)
        state["section"] = section
    
    @classmethod
    def set_waiting(cls, user_id: int, waiting_for: Optional[str]) -> None:
        state = cls.get(user_id)
        state["waiting_for"] = waiting_for
    
    @classmethod
    def clear(cls, user_id: int) -> None:
        cls._states.pop(user_id, None)


