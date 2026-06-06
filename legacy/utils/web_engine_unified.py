
# CONSOLIDATED into web_engine.py — this file kept for backward compatibility
# Use: from arki_project.utils.web_engine import get_web_engine

"""
Unified Web Engine v9.8.6
Consolidates: web_search.py, web_search_ddg.py, web_automation.py,
              web_automation_v9.py, web_recon.py

Provides a single entry point for all web operations.
"""
import logging
from typing import Any, Dict, List
from functools import lru_cache

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class WebEngineUnified:
    """
    Single interface for all web operations:
    - search(query) — multi-engine search
    - scrape(url) — content extraction
    - monitor(url) — change detection
    - recon(target) — security reconnaissance
    - seo(url) — SEO analysis
    """

    def __init__(self) -> None:
        self._search_engine = None
        self._automation = None
        self._recon = None
        self._stats = {
            "searches": 0,
            "scrapes": 0,
            "monitors": 0,
        }

    def _get_search(self) -> Any:
        """Lazy-load search engine."""
        if self._search_engine is None:
            try:
                from utils.web_search_ddg import search_ddg
                self._search_engine = "ddg"
            except ImportError:
                self._search_engine = "generic"
        return self._search_engine

    def _get_automation(self) -> Any:
        """Lazy-load automation (prefer v9)."""
        if self._automation is None:
            try:
                from utils.web_automation_v9 import WebAutomationV9
                self._automation = WebAutomationV9()
            except ImportError:
                from utils.web_automation_compat import WebAutomation
                self._automation = WebAutomation()
        return self._automation

    async def search(
        self, 
        query: str,
        max_results: int = 10,
        engine: str = "auto",
    ) -> List[Dict[str, Any]]:
        """Multi-engine web search."""
        self._stats["searches"] += 1
        logger.info("Web search: %s (engine=%s)", query, engine)

        try:
            if engine == "ddg" or (engine == "auto"):
                try:
                    from utils.web_search_ddg import search_ddg
                    return await search_ddg(query, max_results=max_results)
                except Exception as _exc:
                    logger.debug("Suppressed: %s", _exc)

            from utils.web_search import search_web
            return await search_web(query, max_results=max_results)
        except Exception as e:
            logger.error("Search failed: %s", e)
            return []

    async def scrape(
        self,
        url: str,
        extract_text: bool = True,
        extract_links: bool = False,
    ) -> Dict[str, Any]:
        """Extract content from URL."""
        self._stats["scrapes"] += 1
        automation = self._get_automation()

        try:
            if hasattr(automation, 'extract_content'):
                return await automation.extract_content(url)
            elif hasattr(automation, 'scrape'):
                return await automation.scrape(url)
            return {"url": url, "error": "No scraper available"}
        except Exception as e:
            logger.error("Scrape failed for %s: %s", url, e)
            return {"url": url, "error": str(e)}

    async def monitor(
        self,
        url: str,
        check_interval: int = 3600,
    ) -> Dict[str, Any]:
        """Monitor URL for changes."""
        self._stats["monitors"] += 1
        automation = self._get_automation()

        try:
            if hasattr(automation, 'monitor_url'):
                return await automation.monitor_url(url, check_interval)
            return {"url": url, "status": "monitoring not available"}
        except Exception as e:
            logger.error("Monitor failed for %s: %s", url, e)
            return {"url": url, "error": str(e)}

    async def seo_analyze(self, url: str) -> Dict[str, Any]:
        """SEO analysis of a URL."""
        automation = self._get_automation()
        try:
            if hasattr(automation, 'analyze_seo'):
                return await automation.analyze_seo(url)
            return {"url": url, "error": "SEO analysis not available"}
        except Exception as e:
            return {"url": url, "error": str(e)}

    @property
    def stats(self) -> dict:
        return self._stats.copy()


@lru_cache(maxsize=1)
def get_web_engine() -> WebEngineUnified:
    return WebEngineUnified()


