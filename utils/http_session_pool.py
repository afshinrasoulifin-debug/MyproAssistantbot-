
"""
Centralized HTTP Session Pool v9.1
Provides reusable aiohttp.ClientSession instances.
Prevents creating disposable sessions across the codebase.
"""
import aiohttp
import logging
from typing import Optional, Dict

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)


class HTTPSessionPool:
    """
    Manages reusable aiohttp client sessions with:
    - Connection pooling (per-host limits)
    - Automatic cleanup on shutdown
    - Named sessions for different use cases
    - Request/response metrics
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._stats = {
            "sessions_created": 0,
            "requests_total": 0,
        }
        self._default_timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self._connector_kwargs = {
            "limit": 100,           # Total connection limit
            "limit_per_host": 30,   # Per-host limit
            "ttl_dns_cache": 300,   # DNS cache TTL
            "enable_cleanup_closed": True,
        }

    async def get_session(
        self, 
        name: str = "default",
        headers: Optional[Dict] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
    ) -> aiohttp.ClientSession:
        """Get or create a named session."""
        if name not in self._sessions or self._sessions[name].closed:
            connector = aiohttp.TCPConnector(**self._connector_kwargs)
            self._sessions[name] = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout or self._default_timeout,
                headers=headers or {},
            )
            self._stats["sessions_created"] += 1
            logger.debug("Created HTTP session: %s", name)
        return self._sessions[name]

    async def request(
        self,
        method: str,
        url: str,
        session_name: str = "default",
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make a request using a pooled session."""
        session = await self.get_session(session_name)
        self._stats["requests_total"] += 1
        return await session.request(method, url, **kwargs)

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request("POST", url, **kwargs)

    async def close_all(self) -> None:
        """Close all sessions. Call on shutdown."""
        for name, session in self._sessions.items():
            if not session.closed:
                await session.close()
                logger.debug("Closed HTTP session: %s", name)
        self._sessions.clear()

    async def close_session(self, name: str) -> None:
        """Close a specific session."""
        if name in self._sessions and not self._sessions[name].closed:
            await self._sessions[name].close()
            del self._sessions[name]

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "active_sessions": len([
                s for s in self._sessions.values() if not s.closed
            ]),
        }


# Singleton
_pool: Optional[HTTPSessionPool] = None

def get_http_pool() -> HTTPSessionPool:
    global _pool
    if _pool is None:
        _pool = HTTPSessionPool()
    return _pool

async def cleanup_http_pool() -> None:
    """Call on application shutdown."""
    global _pool
    if _pool:
        await _pool.close_all()
        _pool = None


