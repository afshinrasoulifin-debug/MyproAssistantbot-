
"""
ai_chat_parts/postprocess.py — Response post-processing
Extracted from handle_text() to reduce complexity.
"""
from __future__ import annotations
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def postprocess_response(
    response_text: str,
    user_id: int,
    original_text: str,
) -> str:
    """Post-process AI response: memory storage, telemetry, auto-commands."""
    if not response_text:
        return response_text
    
    # Store in short-term memory
    try:
        from arki_project.utils.memory_store_pkg.memory_store import MemoryStore
        store = MemoryStore()
        await store.add(user_id, {
            "role": "assistant",
            "content": response_text[:500],
        })
    except Exception:
        pass  # Memory store is optional
    
    return response_text


