
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/api_key_manager.py — Internal API Key Manager v3.3
═══════════════════════════════════════════════════════════════
Manages multiple API keys per provider with rotation, health tracking,
usage quotas, and automatic failover. Eliminates single-key dependency.
"""
import asyncio, logging, os, time, json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class APIKeyEntry:
    key: str
    provider: str
    label: str = ""
    is_active: bool = True
    total_calls: int = 0
    total_errors: int = 0
    total_tokens: int = 0
    last_used: float = 0.0
    last_error: float = 0.0
    last_error_msg: str = ""
    rate_limit_until: float = 0.0
    daily_budget_usd: float = 10.0
    daily_spent_usd: float = 0.0
    budget_reset_at: float = 0.0

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_errors / self.total_calls

    @property
    def is_available(self) -> bool:
        if not self.is_active:
            return False
        if time.time() < self.rate_limit_until:
            return False
        if self.daily_spent_usd >= self.daily_budget_usd:
            if time.time() < self.budget_reset_at:
                return False
            self.daily_spent_usd = 0.0
            self.budget_reset_at = time.time() + 86400
        return True

    @property
    def masked_key(self) -> str:
        if len(self.key) < 8:
            return "***"
        return self.key[:4] + "..." + self.key[-4:]


class APIKeyManager:
    """Multi-key rotation manager with health tracking and budget control."""

    def __init__(self, keys_file: str = "") -> None:
        self._keys: Dict[str, List[APIKeyEntry]] = {}
        self._rotation_index: Dict[str, int] = {}
        self._keys_file = keys_file or os.environ.get("API_KEYS_FILE", "")
        self._lock = asyncio.Lock()
        self._stats = {"rotations": 0, "failovers": 0, "exhausted": 0}

    def add_key(self, provider: str, key: str, label: str = "",
                daily_budget: float = 10.0) -> APIKeyEntry:
        entry = APIKeyEntry(
            key=key, provider=provider, label=label or f"{provider}_{len(self._keys.get(provider, []))}",
            daily_budget_usd=daily_budget,
            budget_reset_at=time.time() + 86400,
        )
        self._keys.setdefault(provider, []).append(entry)
        self._rotation_index.setdefault(provider, 0)
        logger.info("Added API key %s for %s", entry.masked_key, provider)
        return entry

    def load_from_env(self) -> int:
        """Load keys from environment variables.
        Format: PROVIDER_API_KEY_N (e.g. OPENROUTER_API_KEY_1, GROQ_API_KEY_2)
        """
        loaded = 0
        providers = ["OPENROUTER", "GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]
        for provider in providers:
            # Primary key
            primary = os.environ.get(f"{provider}_API_KEY", "")
            if primary:
                self.add_key(provider.lower(), primary, label=f"{provider.lower()}_primary")
                loaded += 1
            # Numbered keys
            for i in range(1, 11):
                key = os.environ.get(f"{provider}_API_KEY_{i}", "")
                if key:
                    self.add_key(provider.lower(), key, label=f"{provider.lower()}_{i}")
                    loaded += 1
        logger.info("Loaded %d API keys from environment", loaded)
        return loaded

    def load_from_file(self, path: str = "") -> int:
        """Load keys from JSON file: {"provider": [{"key": "...", "budget": 10}]}"""
        fpath = path or self._keys_file
        if not fpath or not os.path.exists(fpath):
            return 0
        try:
            with open(fpath) as f:
                data = json.load(f)
            loaded = 0
            for provider, keys in data.items():
                for entry in keys:
                    self.add_key(provider, entry["key"],
                                label=entry.get("label", ""),
                                daily_budget=entry.get("budget", 10.0))
                    loaded += 1
            return loaded
        except ArkiBaseError as e:
            logger.error("Failed to load keys file: %s", e)
            return 0

    def load_from_free_router(self) -> int:
        """Load keys from the Free Access Router's provisioned keys."""
        try:
            from arki_project.utils.free_access_router import get_free_router
            router = get_free_router()
            loaded = 0
            for provider, keys in router._provisioned_keys.items():
                km_provider = provider.replace("_free", "").replace("_nokey", "")
                if km_provider == "google_aistudio":
                    km_provider = "gemini"
                for key in keys:
                    existing_keys = [k.key for k in self._keys.get(km_provider, [])]
                    if key not in existing_keys:
                        self.add_key(km_provider, key, label=f"auto_{provider}")
                        loaded += 1
            return loaded
        except ArkiBaseError:
            return 0

    async def get_key(self, provider: str) -> Optional[str]:
        """Get next available key for provider using round-robin rotation."""
        async with self._lock:
            keys = self._keys.get(provider, [])
            if not keys:
                return None
            available = [k for k in keys if k.is_available]
            if not available:
                self._stats["exhausted"] += 1
                logger.warning("All keys exhausted for %s", provider)
                # Try resetting rate-limited ones
                for k in keys:
                    if k.is_active and time.time() >= k.rate_limit_until:
                        available.append(k)
                if not available:
                    return None

            idx = self._rotation_index.get(provider, 0) % len(available)
            key_entry = available[idx]
            self._rotation_index[provider] = idx + 1
            self._stats["rotations"] += 1
            key_entry.total_calls += 1
            key_entry.last_used = time.time()
            return key_entry.key

    async def report_success(self, provider: str, key: str, tokens: int = 0,
                            cost_usd: float = 0.0) -> None:
        for entry in self._keys.get(provider, []):
            if entry.key == key:
                entry.total_tokens += tokens
                entry.daily_spent_usd += cost_usd
                break

    async def report_error(self, provider: str, key: str, error: str,
                          is_rate_limit: bool = False) -> None:
        for entry in self._keys.get(provider, []):
            if entry.key == key:
                entry.total_errors += 1
                entry.last_error = time.time()
                entry.last_error_msg = error[:200]
                if is_rate_limit:
                    entry.rate_limit_until = time.time() + 60
                    logger.warning("Key %s rate-limited for 60s", entry.masked_key)
                elif entry.error_rate > 0.5 and entry.total_calls > 10:
                    entry.is_active = False
                    logger.error("Key %s disabled (error rate %.0f%%)",
                                entry.masked_key, entry.error_rate * 100)
                self._stats["failovers"] += 1
                break

    def get_provider_status(self, provider: str) -> Dict[str, Any]:
        keys = self._keys.get(provider, [])
        return {
            "total_keys": len(keys),
            "active": sum(1 for k in keys if k.is_available),
            "disabled": sum(1 for k in keys if not k.is_active),
            "rate_limited": sum(1 for k in keys if time.time() < k.rate_limit_until),
            "total_calls": sum(k.total_calls for k in keys),
            "total_errors": sum(k.total_errors for k in keys),
            "budget_remaining": sum(
                max(0, k.daily_budget_usd - k.daily_spent_usd)
                for k in keys if k.is_active
            ),
        }

    def get_all_status(self) -> Dict[str, Any]:
        return {
            "providers": {p: self.get_provider_status(p) for p in self._keys},
            **self._stats,
        }


# Singleton
_manager: Optional[APIKeyManager] = None

def get_key_manager() -> APIKeyManager:
    global _manager
    if _manager is None:
        _manager = APIKeyManager()
        _manager.load_from_env()
        _manager.load_from_free_router()
    return _manager


def refresh_keys_from_free_router() -> Any:
    """Refresh API keys from the Free Access Router.
    Call periodically to pick up newly provisioned keys.
    """
    try:
        from arki_project.utils.free_access_router import get_free_router
        router = get_free_router()
        km = get_key_manager()
        added = 0
        for provider, keys in router._provisioned_keys.items():
            # Map free router provider names to key manager provider names
            km_provider = provider.replace("_free", "").replace("_nokey", "")
            if km_provider == "google_aistudio":
                km_provider = "gemini"
            for key in keys:
                existing = [k.key for k in km._keys.get(km_provider, [])]
                if key not in existing:
                    km.add_key(km_provider, key, label=f"auto_{provider}")
                    added += 1
        if added:
            logger.info("Refreshed %d keys from Free Access Router", added)
        return added
    except ArkiBaseError as e:
        logger.debug("Free router key refresh: %s", e)
        return 0


