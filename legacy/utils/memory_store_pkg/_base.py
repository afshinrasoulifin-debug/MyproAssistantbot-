
from __future__ import annotations
"""
memory_store_pkg/_base.py — shared imports
Arki Engine v29.0.0
"""
"""
tg_bot/utils/memory_store.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
MEMORY STORE — Long-Term Memory Engine with RAG Pipeline

Persistent memory system enabling Arki to remember across conversations
with semantic search, user profiling, and knowledge management.

Architecture
────────────
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ Store      │───▶│ TF-IDF     │───▶│ Index      │
  │ (memories) │    │ Vectorizer │    │ (search)   │
  └────────────┘    └────────────┘    └────────────┘
        │                                    │
        ▼                                    ▼
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ User       │    │ Auto-Tag   │    │ RAG        │
  │ Profiles   │    │ Engine     │    │ Pipeline   │
  └────────────┘    └────────────┘    └────────────┘
        │                                    │
        ▼                                    ▼
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ Style      │    │ Forgetting │    │ Context    │
  │ Learning   │    │ Curve      │    │ Builder    │
  └────────────┘    └────────────┘    └────────────┘

Features
────────
  • TF-IDF vector similarity search (no external deps)
  • BM25 scoring as alternative ranking method
  • RAG context builder with token budget management
  • User profiles with style learning (formality, verbosity, technicality)
  • 8 memory types: conversation, fact, preference, skill, result,
    summary, personality, instruction
  • Auto-tagging from content analysis (20+ topic patterns)
  • Importance estimation with content heuristics
  • Memory consolidation (merge highly similar memories)
  • Forgetting curve (Ebbinghaus-inspired decay)
  • Recency & frequency boosting in search
  • Per-user memory isolation
  • JSON export/import with full state preservation
  • Memory statistics & health monitoring
  • Conversation summarization hooks

References
──────────
  Port of: apex_app/src/lib/memory-store.ts (602 lines)
  Enhanced with: BM25 scoring, richer auto-tagger, forgetting curve math,
                 style learning with EMA, memory health stats
"""



# ── TITANIUM v29.0 Integration ──


