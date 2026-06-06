
"""
tg_bot/utils/web_automation_v9.py — REDIRECT v9.4
Merged into web_automation.py. This file exists for backward compatibility.
"""
from arki_project.utils.web_automation_compat import web_search, web_scrape  # noqa: F401

import logging

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)

class WebAutomationEngine:
    """Web automation engine for scraping and form filling."""

    def __init__(self) -> None:
        self._tasks = []

    async def scrape(self, url: str, selector: str = "body") -> dict:
        """Scrape a web page."""
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_get(url, timeout=30.0, provider_name="web_scrape")
                return {"url": url, "status": resp.status, "length": len(resp.text)}
            else:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        html = await resp.text()
                        return {"url": url, "status": resp.status, "length": len(html)}
        except Exception as e:
            logger.debug("Scrape failed: %s", e)
            return {"url": url, "error": str(e)}


