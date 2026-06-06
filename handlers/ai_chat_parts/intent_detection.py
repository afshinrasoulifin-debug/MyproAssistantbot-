
"""
ai_chat_parts/intent_detection.py — Smart intent detection (search + image)
Extracted from handle_text() to reduce complexity.
"""
from __future__ import annotations
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def detect_intent(text: str, user_lang: str = "fa") -> Tuple[Optional[str], Optional[str]]:
    """Detect if text implies a search or image generation intent.
    
    Returns:
        (intent_type, modified_text) — intent_type is 'search', 'image', or None.
    """
    lower = text.lower().strip()
    
    # Search intent patterns
    search_patterns = [
        r"^(جستجو|سرچ|search|بگرد)\s+",
        r"^(چیست|چیه|what is|what's)\s+",
        r"(درباره|about)\s+.*\?$",
    ]
    for pattern in search_patterns:
        if re.search(pattern, lower):
            return ("search", text)
    
    # Image intent patterns
    image_patterns = [
        r"^(بساز|بکش|draw|generate|create)\s+(تصویر|عکس|image|picture)",
        r"(تصویر|عکس|image|picture)\s+(بساز|بکش|draw|generate|create)",
    ]
    for pattern in image_patterns:
        if re.search(pattern, lower):
            return ("image", text)
    
    return (None, text)


