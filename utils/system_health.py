
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/system_health.py — System Health Monitor v3.3
═══════════════════════════════════════════════════════════════
Unified health monitoring for all system components.
Provides real-time status, diagnostics, and alerting.
"""
import asyncio, logging, os, platform, time, sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class SystemHealth:
    """Central health monitoring for all components."""

    def __init__(self) -> None:
        self._boot_time = time.time()
        self._checks: Dict[str, Dict] = {}
        self._alerts: list = []

    async def full_check(self) -> Dict[str, Any]:
        """Run comprehensive health check across all components."""
        report = {
            "status": "healthy",
            "uptime_seconds": int(time.time() - self._boot_time),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "components": {},
        }

        # Check each component
        checks = [
            ("ai_client", self._check_ai_client),
            ("kms", self._check_kms),
            ("rbac", self._check_rbac),
            ("stealth_evasion", self._check_stealth_evasion),
            ("kms_enforcer", self._check_kms_enforcer),
            ("key_manager", self._check_key_manager),
            ("event_bus", self._check_event_bus),
            ("request_queue", self._check_request_queue),
            ("automation", self._check_automation),
            ("marketing", self._check_marketing),
            ("search_privacy", self._check_search_privacy),
            ("proxy_rotator", self._check_proxy_rotator),
            ("database", self._check_database),
        ]

        unhealthy = 0
        for name, check_fn in checks:
            try:
                result = await check_fn() if asyncio.iscoroutinefunction(check_fn) else check_fn()
                report["components"][name] = result
                if result.get("status") == "error":
                    unhealthy += 1
            except ArkiBaseError as e:
                report["components"][name] = {"status": "error", "error": str(e)}
                unhealthy += 1

        if unhealthy > len(checks) // 2:
            report["status"] = "critical"
        elif unhealthy > 0:
            report["status"] = "degraded"

        return report

    def _check_key_manager(self) -> Dict:
        try:
            from arki_project.utils.api_key_manager import get_key_manager
            km = get_key_manager()
            status = km.get_all_status()
            return {"status": "ok", **status}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_event_bus(self) -> Dict:
        try:
            from arki_project.utils.event_bus import get_event_bus
            bus = get_event_bus()
            return {"status": "ok", **bus.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_request_queue(self) -> Dict:
        try:
            from arki_project.utils.request_queue import get_request_queue
            q = get_request_queue()
            return {"status": "ok", **q.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_automation(self) -> Dict:
        try:
            from arki_project.utils.automation_connector import get_automation_connector
            conn = get_automation_connector()
            return {"status": "ok", **conn.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_marketing(self) -> Dict:
        try:
            from arki_project.utils.marketing_engine import get_marketing_engine
            engine = get_marketing_engine()
            return {"status": "ok", **engine.get_analytics(days=1)}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_search_privacy(self) -> Dict:
        try:
            from arki_project.utils.search_privacy import get_search_privacy
            sp = get_search_privacy()
            return {"status": "ok", **sp.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_proxy_rotator(self) -> Dict:
        try:
            from arki_project.utils.proxy_rotator import get_proxy_rotator
            pr = get_proxy_rotator()
            return {"status": "ok", **pr.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    async def _check_ai_client(self) -> Dict:
        return {"status": "ok", "note": "Requires runtime bot context"}

    async def _check_database(self) -> Dict:
        try:
            db_url = os.environ.get("DATABASE_URL", "")
            return {"status": "ok" if db_url else "not_configured",
                    "configured": bool(db_url)}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_stealth_evasion(self) -> Dict:
        try:
            from arki_project.utils.anti_detection import get_stealth_matrix
            matrix = get_stealth_matrix()
            return {"status": "ok", **matrix.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_kms_enforcer(self) -> Dict:
        try:
            from arki_project.utils.kms_enforcer import get_kms_enforcer
            enforcer = get_kms_enforcer()
            return {"status": "ok", **enforcer.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_kms(self) -> Dict:
        try:
            from arki_project.utils.kms import get_kms
            kms = get_kms()
            return {"status": "ok", **kms.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def _check_rbac(self) -> Dict:
        try:
            from arki_project.utils.rbac import get_rbac
            rbac = get_rbac()
            return {"status": "ok", **rbac.stats}
        except ArkiBaseError as e:
            return {"status": "error", "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "uptime": int(time.time() - self._boot_time),
            "alerts": len(self._alerts),
        }

_health: Optional[SystemHealth] = None
def get_system_health() -> SystemHealth:
    global _health
    if _health is None:
        _health = SystemHealth()
    return _health


