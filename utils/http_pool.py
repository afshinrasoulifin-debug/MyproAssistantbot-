
"""
tg_bot/utils/http_pool.py — REDIRECT v10.0 (TITANIUM-enhanced)
HTTP pool — redirects to http_session_pool.py. All functionality lives in http_session_pool.py.
v10: Added TITANIUM ShieldedClient integration for anti-detection HTTP.
"""
from typing import Any
# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════

# Redirect to http_session_pool (v9.8.7 fixed: use class-based pool)
try:
    from arki_project.utils.http_session_pool import get_http_pool, cleanup_http_pool

    async def get_session(name: str = "default", **kwargs) -> Any:
        """Compatibility wrapper → HTTPSessionPool.get_session()."""
        pool = get_http_pool()
        return await pool.get_session(name=name, **kwargs)

    async def close_session(name: str = "default") -> None:
        """Compatibility wrapper → HTTPSessionPool.close_session()."""
        pool = get_http_pool()
        await pool.close_session(name)

    def session_stats() -> dict:
        """Compatibility wrapper → HTTPSessionPool stats."""
        pool = get_http_pool()
        return pool._stats.copy()

except ImportError:
    get_session = None  # type: ignore
    close_session = None  # type: ignore
    session_stats = None  # type: ignore

import aiohttp
import logging

logger = logging.getLogger(__name__)

_sessions: dict = {}

async def get_client(name: str = "default", **kwargs) -> aiohttp.ClientSession:
    """Get or create a named HTTP client session."""
    if name not in _sessions or _sessions[name].closed:
        timeout = aiohttp.ClientTimeout(total=kwargs.get("timeout", 30))
        _sessions[name] = aiohttp.ClientSession(timeout=timeout)
    return _sessions[name]


async def close_all() -> None:
    """Close all HTTP sessions."""
    for name, session in list(_sessions.items()):
        if not session.closed:
            await session.close()
    _sessions.clear()


def pool_stats() -> dict:
    """Return stats about active HTTP sessions."""
    stats = {
        "active_sessions": len([s for s in _sessions.values() if not s.closed]),
        "total_created": len(_sessions),
        "session_names": list(_sessions.keys()),
    }
    # v10: Include TITANIUM shielded pool stats
    try:
        from arki_project.utils.titanium.shielded_client import get_shielded_pool
        pool = get_shielded_pool()
        stats["titanium"] = pool.stats
    except (ImportError, Exception):
        stats["titanium"] = {"status": "not_loaded"}
    return stats


# ── v10: TITANIUM Shielded Client Access ──

def get_shielded_client() -> Any:
    """Get the TITANIUM shielded HTTP client (curl_cffi + L1-L3 security).

    Returns None if TITANIUM not available.
    """
    try:
        from arki_project.utils.titanium.shielded_client import get_shielded_pool
        return get_shielded_pool()
    except ImportError:
        return None


