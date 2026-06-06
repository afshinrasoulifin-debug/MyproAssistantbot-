
from __future__ import annotations
"""
tg_bot/utils/model_watcher.py — Model Deprecation Watcher v9.4
Monitor AI model availability and auto-fallback when deprecated.
"""
import logging
import time
from typing import Dict, Any
from arki_project.utils.circuit_breaker import get_circuit_breaker

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

MODEL_FALLBACK_CHAIN = [
    "gemini-2.5-pro",
    "gemini-2.5-pro",
    "llama-3.3-70b-versatile",
    "qwen-qwq-32b",
    "deepseek-r1-distill-llama-70b",
]


class ModelWatcher:
    """Watch model availability and provide fallback."""

    def __init__(self) -> None:
        self._deprecated: Dict[str, float] = {}
        self._last_success: Dict[str, float] = {}

    def mark_deprecated(self, model: str) -> Any:
        self._deprecated[model] = time.time()
        logger.warning("Model marked deprecated: %s", model)

    def is_available(self, model: str) -> bool:
        if model in self._deprecated:
            return False
        cb = get_circuit_breaker(f"model_{model}")
        return cb.state.value != "open"

    def get_best_model(self, preferred: str = "") -> str:
        """Get the best available model, with fallback."""
        if preferred and self.is_available(preferred):
            return preferred
        for model in MODEL_FALLBACK_CHAIN:
            if self.is_available(model):
                if model != preferred:
                    logger.info("Falling back from %s to %s", preferred, model)
                return model
        return MODEL_FALLBACK_CHAIN[0]  # Last resort

    def record_success(self, model: str) -> Any:
        self._last_success[model] = time.time()
        cb = get_circuit_breaker(f"model_{model}")
        cb.record_success()

    def record_failure(self, model: str) -> Any:
        cb = get_circuit_breaker(f"model_{model}")
        cb.record_failure()


_watcher = None

def get_model_watcher() -> ModelWatcher:
    global _watcher
    if _watcher is None:
        _watcher = ModelWatcher()
    return _watcher


