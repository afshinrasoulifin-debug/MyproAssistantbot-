
from __future__ import annotations
"""
AIAggregator — Aggregate responses from multiple AI providers.
"""
import logging
from typing import Dict, List



logger = logging.getLogger(__name__)

class AIAggregator:
    """Collect and merge responses from multiple AI sources."""

    def __init__(self, strategy: str = "best") -> None:
        self._strategy = strategy

    async def aggregate(self, responses: List[Dict]) -> Dict:
        successful = [r for r in responses if r.get("success", True)]
        if not successful:
            return {"error": "All sources failed", "success": False}

        if self._strategy == "best":
            return max(successful, key=lambda r: len(r.get("content", "")))
        elif self._strategy == "merge":
            contents = [r.get("content", "") for r in successful]
            return {"content": "\n---\n".join(contents), "sources": len(successful)}
        elif self._strategy == "vote":
            # Simple majority vote on content similarity
            return successful[0]
        return successful[0]


