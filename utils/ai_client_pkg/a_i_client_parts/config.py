
"""
AIClient — Config mixin
"""
from __future__ import annotations

import time
import logging

from sqlalchemy import select

try:
    from arki_project.database.connection import get_session
except Exception:
    get_session = None

try:
    from arki_project.database.models import UserConfig
except Exception:
    UserConfig = None

try:
    from arki_project.utils.models_core import DEFAULT_MODEL
except Exception:
    DEFAULT_MODEL = "gemini-2.5-pro"

try:
    from arki_project.utils.api_key_manager import get_key_manager
    _INTERNAL_MGMT = True
except Exception:
    _INTERNAL_MGMT = False
    def get_key_manager(): return None

try:
    from arki_project.exceptions import ProviderAuthError
except Exception:
    ProviderAuthError = Exception

logger = logging.getLogger(__name__)


class AIClientConfigMixin:
    """Methods related to config."""

    async def _get_rotated_key(self, provider: str) -> str:
        """v3.3: Get API key from rotation pool, fallback to primary."""
        if _INTERNAL_MGMT:
            try:
                km = get_key_manager()
                key = await km.get_key(provider)
                if key:
                    return key
            except ProviderAuthError as _err:
                logger.warning("Suppressed error: %s", _err)
        # Fallback to primary keys
        if provider == "gemini":
            return self._api_key
        elif provider == "groq":
            return self._groq_api_key
        elif provider == "openrouter":
            return self._openrouter_api_key
        return self._api_key

    async def get_user_config(self, user_id: int) -> dict:
        """Return dict with model, persona, autotune, voice (cached)."""
        if user_id in self._config_cache:
            cached_at, cached_val = self._config_cache[user_id]
            if time.time() - cached_at < self._config_cache_ttl:
                return cached_val
            del self._config_cache[user_id]

        async with get_session() as session:
            result = await session.execute(
                select(UserConfig).where(
                    UserConfig.telegram_id == user_id,
                ),
            )
            cfg = result.scalar_one_or_none()
            if cfg is None:
                result_dict = {
                    "model": DEFAULT_MODEL,
                    "persona": "assistant",
                    "autotune": True,
                    "voice": "Zephyr",
                }
            else:
                result_dict = {
                    "model": cfg.model,
                    "persona": cfg.persona,
                    "autotune": cfg.autotune,
                    "voice": cfg.voice,
                }

        self._config_cache[user_id] = (time.time(), result_dict)
        return result_dict

    async def set_user_config(
        self, user_id: int, key: str, value: object
    ) -> None:
        self._config_cache.pop(user_id, None)  # invalidate cache
        async with get_session() as session:
            result = await session.execute(
                select(UserConfig).where(
                    UserConfig.telegram_id == user_id,
                ),
            )
            cfg = result.scalar_one_or_none()
            if cfg is None:
                cfg = UserConfig(telegram_id=user_id)
                session.add(cfg)
                await session.flush()
            setattr(cfg, key, value)
            await session.flush()


