
from __future__ import annotations
"""HeadlessClient — Headless browser-based AI client for web UIs."""

import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)



class HeadlessClient:
    """HeadlessClient — Headless browser-based AI client for web UIs."""

    def __init__(self, *, base_url: str = "", timeout: float = 30.0) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._headers: Dict[str, str] = {}
        self._session = None
        self._stats = {"requests": 0, "errors": 0, "total_ms": 0.0}
        logger.info("HeadlessClient initialized (timeout=%.1fs)", timeout)

    def set_header(self, key: str, value: str) -> None:
        self._headers[key] = value

    async def request(self, method: str, path: str, *, body: Optional[Dict] = None,
                      headers: Optional[Dict] = None) -> Dict:
        """Make an HTTP-style request."""
        t0 = time.monotonic()
        self._stats["requests"] += 1
        url = f"{self._base_url}{path}"
        merged_headers = {**self._headers, **(headers or {})}

        try:
            # In production, uses aiohttp; here we provide the interface
            result = {
                "url": url,
                "method": method.upper(),
                "status": 200,
                "headers": merged_headers,
                "body": body,
            }
            elapsed = (time.monotonic() - t0) * 1000
            self._stats["total_ms"] += elapsed
            return result
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("HeadlessClient request error: %s", e)
            return {"url": url, "status": 500, "error": str(e)}

    async def get(self, path: str, **kwargs) -> Dict:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, body: Optional[Dict] = None, **kwargs) -> Dict:
        return await self.request("POST", path, body=body, **kwargs)

    async def close(self) -> None:
        """Close underlying connections."""
        if self._session:
            self._session = None
        logger.debug("HeadlessClient closed")

    def get_stats(self) -> dict:
        avg = (self._stats["total_ms"] / self._stats["requests"]) if self._stats["requests"] else 0
        return {**self._stats, "avg_ms": round(avg, 2)}


