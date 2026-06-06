
from __future__ import annotations
"""
tg_bot/utils/web_engine.py — Unified Web Engine v9.8.6
═══════════════════════════════════════════════════
Consolidates: web_automation.py, web_automation_v9.py, web_engine_unified.py

Provides:
  • Multi-source web search (DuckDuckGo, Jina, Bing)
  • URL content extraction via Jina Reader
  • Browser automation (Playwright when available)
  • Request pooling via HTTP session pool
"""
import logging
from typing import Any, Dict, List
from functools import lru_cache

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)


class WebEngine:
    """Unified web engine — single entry point for all web operations."""

    def __init__(self) -> None:
        self._http_pool = None
        self._browser = None
        self._stats = {"searches": 0, "fetches": 0, "errors": 0}

    async def _get_pool(self) -> Any:
        if not self._http_pool:
            try:
                from arki_project.utils.http_session_pool import get_http_pool
                self._http_pool = get_http_pool()
            except ImportError as _exc:
                logger.debug("Suppressed: %s", _exc)
        return self._http_pool

    # ── Search ──

    async def search(self, query: str, max_results: int = 10,
                     sources: List[str] = None) -> List[Dict[str, Any]]:
        """Multi-source web search."""
        sources = sources or ["ddg", "jina"]
        results = []
        self._stats["searches"] += 1

        for source in sources:
            try:
                if source == "ddg":
                    results.extend(await self._search_ddg(query, max_results))
                elif source == "jina":
                    results.extend(await self._search_jina(query, max_results))
                if len(results) >= max_results:
                    break
            except Exception as e:
                logger.debug("Search source %s failed: %s", source, e)
                self._stats["errors"] += 1

        # Deduplicate by URL
        seen = set()
        unique = []
        for r in results:
            url = r.get("url", "")
            if url not in seen:
                seen.add(url)
                unique.append(r)
        return unique[:max_results]

    async def _search_ddg(self, query: str, max_results: int) -> List[Dict]:
        try:
            from arki_project.utils.web_search_ddg import ddg_search
            return await ddg_search(query, max_results=max_results)
        except ImportError:
            return []

    async def _search_jina(self, query: str, max_results: int) -> List[Dict]:
        try:
            # v10.1: Route through TITANIUM shielded client
            if _TITANIUM_ACTIVE:
                resp = await shielded_get(
                    f"https://s.jina.ai/{query}",
                    headers={"Accept": "application/json"},
                    timeout=15.0,
                    provider_name="jina_search",
                )
                if resp.success:
                    data = resp.json()
                    return [
                        {"title": r.get("title", ""), "url": r.get("url", ""),
                         "snippet": r.get("description", ""), "source": "jina"}
                        for r in data.get("data", [])[:max_results]
                    ]
            else:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://s.jina.ai/{query}",
                        headers={"Accept": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return [
                                {"title": r.get("title", ""), "url": r.get("url", ""),
                                 "snippet": r.get("description", ""), "source": "jina"}
                                for r in data.get("data", [])[:max_results]
                            ]
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)
        return []

    # ── Fetch URL Content ──

    async def fetch_url(self, url: str, timeout: float = 15.0) -> str:
        """Fetch clean content from URL via Jina Reader."""
        self._stats["fetches"] += 1
        try:
            from arki_project.utils.jina_reader import fetch_url_content
            return await fetch_url_content(url, timeout=timeout)
        except Exception as e:
            logger.warning("fetch_url failed for %s: %s", url, e)
            self._stats["errors"] += 1
            return ""

    async def fetch_urls(self, urls: List[str], timeout: float = 15.0) -> Dict[str, str]:
        """Fetch multiple URLs concurrently."""
        tasks = {url: self.fetch_url(url, timeout) for url in urls}
        results = {}
        for url, task in tasks.items():
            try:
                results[url] = await task
            except Exception:
                results[url] = ""
        return results

    # ── Browser Automation ──

    async def browse(self, url: str, actions: List[Dict] = None) -> Dict[str, Any]:
        """Browser automation with Playwright."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)

                result = {
                    "url": page.url,
                    "title": await page.title(),
                    "content": await page.content(),
                }

                if actions:
                    for action in actions:
                        action_type = action.get("type")
                        if action_type == "click":
                            await page.click(action["selector"])
                        elif action_type == "fill":
                            await page.fill(action["selector"], action["value"])
                        elif action_type == "screenshot":
                            result["screenshot"] = await page.screenshot()

                await browser.close()
                return result
        except ImportError:
            return {"error": "playwright not installed"}
        except Exception as e:
            return {"error": str(e)}

    # ── Element Scoring (from web_automation.py) ──

    def score_elements(self, html: str, target_type: str = "form") -> List[Dict]:
        """Score HTML elements for automation targeting."""
        import re
        elements = []
        if target_type == "form":
            for match in re.finditer(r'<form[^>]*>(.*?)</form>', html, re.DOTALL):
                inputs = len(re.findall(r'<input', match.group(1)))
                score = inputs * 10  # More inputs = more important form
                elements.append({"type": "form", "inputs": inputs, "score": score,
                                 "html": match.group()[:500]})
        elif target_type == "link":
            link_re = re.compile(r'<a[^>]*href=["\x27]([^"\x27]*)["\x27][^>]*>(.*?)</a>', re.DOTALL)
            for match in link_re.finditer(html):
                elements.append({"type": "link", "url": match.group(1),
                                 "text": match.group(2)[:100], "score": 5})
        return sorted(elements, key=lambda x: x["score"], reverse=True)

    @property
    def stats(self) -> dict:
        return self._stats.copy()


@lru_cache(maxsize=1)
def get_web_engine() -> WebEngine:
    return WebEngine()


