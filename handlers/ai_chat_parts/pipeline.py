
"""
ai_chat_parts/pipeline.py — v9 IntelligentPipeline helper
Extracted from handle_text() to reduce complexity.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def run_intelligent_pipeline(
    text: str,
    user_id: int,
    ai_client: Any,
    user_config: Dict,
    history: list,
) -> Optional[str]:
    """Run the v9 IntelligentPipeline: classify → context → reason → execute.
    
    Returns AI response text or None if pipeline is unavailable.
    """
    try:
        from arki_project.core.reasoning_pkg.reasoningengine import ReasoningEngine
        engine = ReasoningEngine()
        result = await engine.reason(text, context={
            "user_id": user_id,
            "config": user_config,
            "history": history[-10:] if history else [],
        })
        if result and isinstance(result, dict):
            return result.get("response") or result.get("text")
        return str(result) if result else None
    except ImportError:
        logger.debug("ReasoningEngine not available")
        return None
    except Exception as exc:
        logger.warning("Pipeline error: %s", exc)
        return None


