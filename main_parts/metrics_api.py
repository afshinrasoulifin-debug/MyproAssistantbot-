"""
main_parts/metrics_api.py — Metrics + OpenAPI endpoints
Extracted from main.py to reduce complexity.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def init_metrics_api(bot, settings, ai_client=None):
    """Initialize metrics and OpenAPI endpoints (available only in webhook mode)."""
    try:
        from aiohttp import web
    except ImportError:
        logger.debug("aiohttp not available, skipping metrics API")
        return

    logger.info("Metrics API endpoints available in webhook mode")
