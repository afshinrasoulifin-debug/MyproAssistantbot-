
"""
tg_bot/utils/web_search_ddg.py — DuckDuckGo Free Search
═══════════════════════════════════════════════════════════
No API key, no rate limits, no cost.

Usage:
    from arki_project.utils.web_search_ddg import ddg_search
    results = ddg_search("python web scraping", max_results=10)
"""
import logging

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


def ddg_search(query: str, max_results: int = 10) -> list:
    """Search via DuckDuckGo — free, no API key."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "duckduckgo",
                })
        return results
    except ImportError:
        logger.warning("duckduckgo-search not installed")
        return []
    except Exception as e:
        logger.warning("DDG search failed: %s", e)
        return []


async def ddg_search_async(query: str, max_results: int = 10) -> list:
    """Async wrapper for DuckDuckGo search."""
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ddg_search, query, max_results)


