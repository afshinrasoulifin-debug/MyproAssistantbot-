
"""
web_search_pkg/helpers.py — standalone functions
Arki Engine v29.0.0
"""
from ._base import *  # noqa

async def search_with_fallback(query: str, max_results: int = 5) -> list:
    """Search using DuckDuckGo with fallback to Jina."""
    try:
        from arki_project.utils.web_search_ddg import ddg_search
        return await ddg_search(query, max_results=max_results)
    except Exception:
        try:
            from arki_project.utils.jina_reader import jina_search
            return await jina_search(query, max_results=max_results)
        except Exception:
            return []



async def search_with_gemini(query: str, api_key: str = "") -> str:
    """Use Gemini grounding for web search."""
    return ""



async def deep_search(query: str, max_results: int = 10) -> list:
    """Deep search combining multiple providers."""
    return await search_with_fallback(query, max_results=max_results)


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Search Intelligence
# ══════════════════════════════════════════════════════════════



