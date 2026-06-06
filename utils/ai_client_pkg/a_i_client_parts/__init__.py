
"""
AIClient — Composed from domain mixins
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)

# Import needed names that __init__ body uses
try:
    from arki_project.utils.circuit_breaker import CircuitBreaker
except Exception:
    class CircuitBreaker:
        def __init__(self, *a, **kw): pass

try:
    from arki_project.utils.api_key_manager import get_key_manager
    _INTERNAL_MGMT = True
except Exception:
    _INTERNAL_MGMT = False
    def get_key_manager(): return None

try:
    from arki_project.exceptions import AIProviderError
except Exception:
    AIProviderError = Exception

try:
    from arki_project.utils.ai_client_pkg.chat_message import ChatMessage
except Exception:
    ChatMessage = dict

# Mixin imports
class _EmptyMixin: pass
try:
    from .chat import AIClientChatMixin
except Exception:
    AIClientChatMixin = _EmptyMixin
try:
    from .config import AIClientConfigMixin
except Exception:
    AIClientConfigMixin = _EmptyMixin
try:
    from .core import AIClientCoreMixin
except Exception:
    AIClientCoreMixin = _EmptyMixin
try:
    from .providers import AIClientProvidersMixin
except Exception:
    AIClientProvidersMixin = _EmptyMixin


class AIClient(AIClientChatMixin, AIClientConfigMixin, AIClientCoreMixin, AIClientProvidersMixin):
    """Assembled AIClient from all domain mixins."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "gemini-2.5-pro",  # v10.2: Pro default
        max_history: int = 500,  # v9.7.1: Deep context
        temperature: float = 0.7,
        max_tokens: int = 65536,  # v10.2: TITANIUM unlimited
        groq_api_key: str = "",
        openrouter_api_key: str = "",
    ) -> None:
        self._api_key = api_key
        # v3.3: Register keys with internal key manager for rotation
        if _INTERNAL_MGMT:
            try:
                km = get_key_manager()
                if api_key:
                    km.add_key("gemini", api_key, label="primary_gemini")
                if groq_api_key:
                    km.add_key("groq", groq_api_key, label="primary_groq")
                if openrouter_api_key:
                    km.add_key("openrouter", openrouter_api_key, label="primary_openrouter")
                km.load_from_env()  # Load any additional keys from env
                logger.info("v3.3: Internal key manager initialized with %s",
                           {p: km.get_provider_status(p)["total_keys"]
                            for p in ["gemini", "groq", "openrouter"]})
            except AIProviderError as e:
                logger.debug("Key manager init: %s (non-fatal)", e)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_history = max_history
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._groq_api_key = groq_api_key
        self._openrouter_api_key = openrouter_api_key
        # In-memory caches.
        self._history: Dict[int, List[ChatMessage]] = defaultdict(list)
        self._loaded_users: set[int] = set()
        self._config_cache: dict[int, tuple[float, dict]] = {}  # user_id → (timestamp, config)
        self._config_cache_ttl: float = 300.0  # 5 minutes
        # Use centralized HTTP pool (shared across all modules)
        # No duplicate clients — saves memory and connections
        from arki_project.utils.http_pool import get_client as _get_pool_client
        self._get_pool_client = _get_pool_client
        # v9.5: Circuit breaker per provider
        self._breakers = {
            'gemini': CircuitBreaker('gemini', failure_threshold=5, recovery_timeout=60.0),
            'groq': CircuitBreaker('groq', failure_threshold=5, recovery_timeout=60.0),
            'openrouter': CircuitBreaker('openrouter', failure_threshold=3, recovery_timeout=120.0),
            'claude_ultra': CircuitBreaker('claude_ultra', failure_threshold=5, recovery_timeout=90.0),
        }


__all__ = ["AIClient"]


