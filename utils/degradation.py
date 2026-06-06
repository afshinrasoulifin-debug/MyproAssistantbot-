
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/degradation.py — Graceful Degradation v9.4
Per-feature degradation: when one service fails, others continue.
"""
import logging
from typing import Dict, Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class DegradationManager:
    """Track service health and enable graceful degradation."""

    def __init__(self) -> None:
        self._service_health: Dict[str, bool] = {
            "ai_gemini": True,
            "ai_groq": True,
            "ai_openrouter": True,
            "web_search": True,
            "image_gen": True,
            "voice_stt": True,
            "redis": True,
            "database": True,
            "telegram_api": True,
        }
        self._degraded_messages: Dict[str, str] = {
            "ai_gemini": "⚠️ Gemini موقتاً در دسترس نیست. از مدل جایگزین استفاده می‌شود.",
            "ai_groq": "⚠️ Groq موقتاً در دسترس نیست.",
            "web_search": "⚠️ جستجوی وب موقتاً غیرفعال است.",
            "image_gen": "⚠️ تولید تصویر موقتاً غیرفعال است.",
            "voice_stt": "⚠️ تبدیل صدا به متن موقتاً غیرفعال است.",
        }

    def mark_down(self, service: str) -> Any:
        self._service_health[service] = False
        logger.warning("Service degraded: %s", service)

    def mark_up(self, service: str) -> Any:
        self._service_health[service] = True
        logger.info("Service recovered: %s", service)

    # Alias for consistency
    mark_healthy = mark_up

    def is_healthy(self, service: str) -> bool:
        return self._service_health.get(service, True)

    def get_degraded_message(self, service: str) -> str:
        return self._degraded_messages.get(service, f"⚠️ سرویس {service} موقتاً در دسترس نیست.")

    def get_status(self) -> Dict[str, bool]:
        return dict(self._service_health)

    def get_fallback_model(self) -> Optional[str]:
        """Get best available AI model based on health."""
        if self.is_healthy("ai_gemini"):
            return "gemini-2.5-pro"
        if self.is_healthy("ai_groq"):
            return "llama-3.3-70b"
        if self.is_healthy("ai_openrouter"):
            return "openrouter/auto"
        return None

    def register_service(self, name: str) -> None:
        """Register a new service for health tracking."""
        if name not in self._service_health:
            self._service_health[name] = True

    async def check_and_recover(self) -> Dict[str, str]:
        """Probe degraded services and auto-recover if possible (v10.3.1)."""
        recoveries: Dict[str, str] = {}

        for service, healthy in list(self._service_health.items()):
            if healthy:
                continue  # Already up — skip

            recovered = False
            try:
                if "ai_" in service:
                    # Check circuit breaker state
                    from arki_project.utils.circuit_breaker import get_circuit_breaker
                    cb = get_circuit_breaker(service.replace("ai_", ""))
                    if cb.state.value != "open":
                        recovered = True
                elif service == "redis":
                    import os, socket
                    redis_url = os.environ.get("REDIS_URL", "")
                    if redis_url:
                        parts = redis_url.replace("redis://", "").split(":")
                        host = parts[0] if parts else "localhost"
                        port_str = parts[1].split("/")[0] if len(parts) > 1 else "6379"
                        s = socket.create_connection((host, int(port_str)), timeout=2)
                        s.close()
                        recovered = True
                elif service == "database":
                    from arki_project.database.connection import health_check
                    if await health_check():
                        recovered = True
            except ArkiBaseError as _err:
                logger.warning("Suppressed error: %s", _err)

            if recovered:
                self.mark_up(service)
                recoveries[service] = "recovered"
                logger.info("Auto-recovery: %s is back up", service)
            else:
                recoveries[service] = "still_down"

        return recoveries


_manager: Optional[DegradationManager] = None

def get_degradation_manager() -> DegradationManager:
    global _manager
    if _manager is None:
        _manager = DegradationManager()
    return _manager


