
from __future__ import annotations
"""
tg_bot/utils/titanium/integration.py — Universal TITANIUM Integration Helpers v10.3.1
════════════════════════════════════════════════════════════════════════════════
Provides drop-in replacement functions for any module that makes HTTP calls
or uses random. Import these instead of raw httpx/random.

Usage:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post
    resp = await shielded_post(url, json_data=body, headers=headers)
    if resp.success:
        data = resp.json()
"""


import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("titanium.integration")


async def shielded_get(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300.0,
    provider_name: str = "",
    **kwargs: Any,
) -> Any:
    """Drop-in shielded GET with L1-L7 security."""
    from arki_project.utils.titanium.shielded_client import get_shielded_pool
    pool = get_shielded_pool()
    return await pool.get(url, headers=headers, timeout=timeout, provider_name=provider_name, **kwargs)


async def shielded_post(
    url: str,
    *,
    json_data: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300.0,
    provider_name: str = "",
    **kwargs: Any,
) -> Any:
    """Drop-in shielded POST with L1-L7 security."""
    from arki_project.utils.titanium.shielded_client import get_shielded_pool
    pool = get_shielded_pool()
    return await pool.post(url, json_data=json_data, headers=headers, timeout=timeout,
                           provider_name=provider_name, **kwargs)


async def shielded_request(
    method: str,
    url: str,
    *,
    json_data: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300.0,
    provider_name: str = "",
    **kwargs: Any,
) -> Any:
    """Drop-in shielded request with L1-L7 security."""
    from arki_project.utils.titanium.shielded_client import get_shielded_pool
    pool = get_shielded_pool()
    return await pool.request(method, url, json_data=json_data, headers=headers,
                              timeout=timeout, provider_name=provider_name, **kwargs)


def get_secure_random() -> Any:
    """Get a drop-in replacement for Python's random module."""
    from arki_project.utils.titanium.compat import secure_random
    return secure_random


