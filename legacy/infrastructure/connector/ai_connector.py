
from __future__ import annotations
"""AIConnector — Connect to AI APIs with auto-configuration."""
import os, logging
from typing import Dict



logger = logging.getLogger(__name__)

class AIConnector:
    """Auto-detect and connect to available AI services."""

    def __init__(self) -> None:
        self._connections: Dict[str, dict] = {}

    def auto_connect(self) -> Dict[str, bool]:
        results = {}
        for name, env_key in [
            ("gemini", "AI_API_KEY"), ("groq", "GROQ_API_KEY"),
            ("openrouter", "OPENROUTER_API_KEY"), ("openai", "OPENAI_API_KEY"),
        ]:
            key = os.environ.get(env_key, "").strip()
            if key:
                self._connections[name] = {"key": key[:8] + "...", "status": "connected"}
                results[name] = True
            else:
                results[name] = False
        logger.info("AIConnector: %d providers connected", sum(results.values()))
        return results

    @property
    def connected(self) -> list:
        return list(self._connections.keys())


