
from __future__ import annotations
"""Victor v7.0 TITAN — Data models (dataclasses)"""

import time
from dataclasses import dataclass, field
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════════
# 1. MEMORY STORE v7 — TF-IDF + BM25 + Knowledge Graph
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Memory:
    """A single memory unit."""
    id: str
    content: str
    memory_type: str        # "fact", "skill", "episode", "pattern", "correction", "rule", "conversation"
    topic: str              # Category/topic
    keywords: List[str]     # Extracted keywords for retrieval
    associations: List[str] # Related memory IDs
    strength: float = 1.0   # How strong/important (grows with reinforcement)
    access_count: int = 0   # How many times accessed
    created_at: str = ""
    last_accessed: str = ""
    source: str = "admin"   # Who taught this
    sentiment: str = "neutral"  # positive/negative/neutral
    language: str = "fa"    # fa/en/mixed
    embedding: List[float] = field(default_factory=list)  # TF-IDF vector

class KnowledgeEdge:
    """A relationship between two concepts in the knowledge graph."""
    from_node: str
    to_node: str
    relation: str           # "is_a", "has", "does", "related_to", "causes", "part_of",
                            # "opposite_of", "example_of", "requires", "produces"
    weight: float = 1.0
    bidirectional: bool = False

class InferenceRule:
    """An if/then rule for logical inference."""
    id: str
    condition_topic: str    # If a query matches this topic...
    condition_keywords: List[str]  # ...and contains these keywords...
    conclusion: str         # ...then this is the answer
    confidence: float = 0.8
    use_count: int = 0

# ═══════════════════════════════════════════════════════════════════
# v6 NEW COMPONENTS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Turn:
    """A single conversation turn (v6)."""
    role: str           # "user" or "bot"
    text: str
    timestamp: float = field(default_factory=time.time)
    intent: str = ""
    confidence: float = 0.0
    entities: Dict[str, List[str]] = field(default_factory=dict)

# ═══════════════════════════════════════════════════════════════════
# 2. PATTERN ENGINE v5 — Fuzzy + N-gram + Context-Aware
# ═══════════════════════════════════════════════════════════════════

@dataclass
class IntentPattern:
    """A learned pattern for recognizing user intent."""
    intent: str
    patterns_fa: List[str]   # Persian keyword patterns
    patterns_en: List[str]   # English keyword patterns
    response_template: str   # How to respond (supports {variables})
    action: str = "reply"    # "reply", "execute_module", "recall", "learn", "infer"
    module: str = ""         # Which Arki module to call if action=execute_module
    priority: int = 5        # Higher = checked first
    context_hint: str = ""   # Only match if recent context contains this


