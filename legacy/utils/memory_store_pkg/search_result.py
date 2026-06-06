
"""
memory_store_pkg/search_result.py — SearchResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class SearchResult:
    """A single search result with score and explanation."""
    memory: Memory
    score: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory.id,
            "score": round(self.score, 4),
            "reason": self.reason,
            "type": self.memory.type.value,
            "content_preview": self.memory.content[:200],
        }


# ═══════════════════════════════════════════════════════════════════
# TF-IDF Vector Engine (No External Dependencies)
# ═══════════════════════════════════════════════════════════════════



