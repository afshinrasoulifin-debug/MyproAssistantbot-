
"""
tg_bot/utils/jina_reader.py — Jina Reader (free URL→Markdown)
══════════════════════════════════════════════════════════════════
Extracts clean markdown from any URL. Free, no API key, no deps.

Usage:
    from arki_project.utils.jina_reader import fetch_url_content
    content = await fetch_url_content("https://example.com")
"""
import logging
from arki_project.exceptions import ArkiBaseError

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)


async def fetch_url_content(url: str, timeout: float = 15.0) -> str:
    """Fetch clean markdown from URL via Jina Reader — free."""
    try:
        # v10.1: Route through TITANIUM
        if _TITANIUM_ACTIVE:
            resp = await shielded_get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "text/markdown"},
                timeout=timeout,
                provider_name="jina_reader",
            )
            return resp.text if resp.success else ""
        else:
            import httpx
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    f"https://r.jina.ai/{url}",
                    headers={"Accept": "text/markdown"},
                )
                resp.raise_for_status()
                return resp.text
    except ArkiBaseError as e:
        logger.warning("Jina reader failed for %s: %s", url, e)
        return ""


async def jina_search(query: str, max_results: int = 5) -> list:
    """Search via Jina AI Reader API."""
    url = f"https://r.jina.ai/{query}"
    try:
        # v10.1: Route through TITANIUM
        if _TITANIUM_ACTIVE:
            resp = await shielded_get(url, timeout=15.0, provider_name="jina_search")
            if resp.success:
                return [{"title": query, "snippet": resp.text[:500], "url": url}]
            return []
        else:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    text = await resp.text()
                    return [{"title": query, "snippet": text[:500], "url": url}]
    except ArkiBaseError:
        return []


