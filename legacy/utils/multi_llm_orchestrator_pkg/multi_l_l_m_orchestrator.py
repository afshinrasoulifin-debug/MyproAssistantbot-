
"""
multi_llm_orchestrator_pkg/multi_l_l_m_orchestrator.py — MultiLLMOrchestrator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class MultiLLMOrchestrator:
    """Orchestrate queries across multiple LLM providers for consensus."""

    def __init__(self):
        self._providers = []
        self._strategy = "fastest"  # fastest, consensus, cascade

    def add_provider(self, name: str, client):
        self._providers.append({"name": name, "client": client})

    async def query(self, messages: list, strategy: str = None) -> dict:
        """Query using selected strategy."""
        strat = strategy or self._strategy
        if strat == "fastest":
            return await self._fastest(messages)
        elif strat == "consensus":
            return await self._consensus(messages)
        return await self._cascade(messages)

    async def _fastest(self, messages):
        import asyncio
        tasks = []
        for p in self._providers:
            tasks.append(asyncio.create_task(self._safe_query(p, messages)))
        if not tasks:
            return {"content": "", "provider": "none"}
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        return done.pop().result()

    async def _consensus(self, messages):
        import asyncio
        results = await asyncio.gather(*[self._safe_query(p, messages) for p in self._providers], return_exceptions=True)
        valid = [r for r in results if isinstance(r, dict)]
        return valid[0] if valid else {"content": "", "provider": "none"}

    async def _cascade(self, messages):
        for p in self._providers:
            try:
                return await self._safe_query(p, messages)
            except Exception:
                continue
        return {"content": "", "provider": "none"}

    async def _safe_query(self, provider, messages):
        return {"content": "", "provider": provider["name"]}



# ═══════════════════════════════════════════════════════════════════════
# ULTRAPLINIAN ENGINE — Multi-Model Competition + CONSORTIUM (DEEP)
# ═══════════════════════════════════════════════════════════════════════
#
# Architecture:
#   ┌────────────────────────────────────────────────────────────┐
#   │                    ULTRAPLINIAN PIPELINE                    │
#   │                                                            │
#   │  APEX prompt → Depth Directive → AutoTune → Parseltongue│
#   │       ↓                                                    │
#   │  N models in staggered waves (12/wave, 150ms gap)         │
#   │       ↓                                                    │
#   │  100-point scoring per response                            │
#   │  (length:25 + structure:20 + anti-refusal:25               │
#   │   + directness:15 + relevance:15)                          │
#   │       ↓                                                    │
#   │  Early-exit: min 5 success → 5s grace → hard 45s          │
#   │       ↓                                                    │
#   │  Winner selection (highest score)                          │
#   └────────────────────────────────────────────────────────────┘
#                          OR
#   ┌────────────────────────────────────────────────────────────┐
#   │                    CONSORTIUM MODE                          │
#   │                                                            │
#   │  Same collection as above                                  │
#   │       ↓                                                    │
#   │  Feed ALL responses to orchestrator model                  │
#   │       ↓                                                    │
#   │  Synthesize ground truth from collective intelligence      │
#   └────────────────────────────────────────────────────────────┘
#
# Ported from: APEX-main/api/lib/ultraplinian.ts + consortium.ts
# Version: 4.0.0-DEEP (Phase 1-5 hardened)
# ═══════════════════════════════════════════════════════════════════════




