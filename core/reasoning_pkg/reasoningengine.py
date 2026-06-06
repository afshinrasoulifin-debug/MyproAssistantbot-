
"""reasoning_pkg.reasoningengine — sub-module of reasoning"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──

__all__ = ['ReasoningEngine']

class ReasoningEngine:
    """
    Main reasoning engine v10 that coordinates all strategies.

    This is what makes Arki THINK, not just respond.

    v10 enhancements:
    - Auto-selects optimal strategy based on task analysis
    - Supports strategy escalation (if initial strategy fails)
    - Persian/Farsi native support
    - Confidence-based quality gating
    """

    def __init__(self) -> None:
        self.cot = ChainOfThoughtStrategy()
        self.react = ReActStrategy()
        self.tot = TreeOfThoughtStrategy()
        self.self_refine = SelfRefineStrategy()
        self.meta_cog = MetaCognitiveStrategy()
        self.decompose = DecomposeStrategy()
        # v10: Track strategy effectiveness
        self._strategy_scores: Dict[str, List[float]] = {}

    def auto_select_strategy(
        self,
        user_text: str,
        category: str = "chat",
        complexity: int = 1,
    ) -> str:
        """
        v10: Intelligently select the best reasoning strategy.

        Uses task characteristics, not just complexity level.
        """
        text_lower = user_text.lower()
        word_count = len(user_text.split())

        # Multi-part tasks → Decompose
        multi_part_signals = [
            "و همچنین", "علاوه بر", "سپس", "بعد از آن",
            "and also", "additionally", "then", "after that",
            bool(re.search(r"\d+\.\s", user_text)),  # numbered list
        ]
        if sum(1 for s in multi_part_signals if (isinstance(s, bool) and s) or (isinstance(s, str) and s in text_lower)) >= 2:
            return "decompose"

        # Tool-requiring tasks → ReAct
        tool_signals = [
            "search", "جستجو", "calculate", "محاسبه",
            "scan", "اسکن", "workflow", "encrypt", "رمز",
        ]
        if any(s in text_lower for s in tool_signals):
            return "react"

        # Expert-level complexity → ToT
        if complexity >= 5 or word_count > 100:
            return "tree_of_thought"

        # Complex tasks → Meta-cognitive
        if complexity >= 4:
            return "meta_cognitive"

        # Moderate tasks → CoT
        if complexity >= 3 or word_count > 30:
            return "chain_of_thought"

        # Tasks requiring polish → Self-refine
        if category in ("creative", "sales", "content"):
            return "self_refine"

        # Simple → Direct
        return "direct"

    def get_strategy_prompt(
        self,
        strategy: str,
        user_text: str,
        context: str = "",
        tools: Optional[List[Tool]] = None,
    ) -> str:
        """Get the enhanced prompt for a given strategy."""
        if strategy in ("chain_of_thought", "cot"):
            return self.cot.build_prompt(user_text, context)
        elif strategy == "react":
            return self.react.build_initial_prompt(user_text, tools, context)
        elif strategy in ("tree_of_thought", "tot"):
            prompts = self.tot.build_branch_prompts(user_text, context)
            return prompts[0] if prompts else user_text
        elif strategy == "self_refine":
            return self.self_refine.build_initial_prompt(user_text, context)
        elif strategy == "meta_cognitive":
            return self.meta_cog.build_prompt(user_text, context)
        elif strategy == "decompose":
            return self.decompose.build_decompose_prompt(user_text, context)
        else:
            # Direct strategy — add a quality nudge
            if _is_persian(user_text):
                return (
                    f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                    f"{user_text}\n\n"
                    "پاسخ دقیق، کامل و مفید ارائه بده."
                )
            return (
                f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
                f"{user_text}\n\n"
                "Provide an accurate, complete, and helpful response."
            )

    def get_escalation_strategy(self, current_strategy: str) -> Optional[str]:
        """v10: If current strategy produced low-quality output, escalate."""
        escalation_map = {
            "direct": "chain_of_thought",
            "chain_of_thought": "self_refine",
            "self_refine": "tree_of_thought",
            "react": "tree_of_thought",
            "meta_cognitive": "tree_of_thought",
            "tree_of_thought": None,  # Already top-level
            "decompose": "tree_of_thought",
        }
        return escalation_map.get(current_strategy)

    def record_strategy_outcome(self, strategy: str, quality: float) -> None:
        """v10: Track strategy effectiveness for adaptive selection."""
        if strategy not in self._strategy_scores:
            self._strategy_scores[strategy] = []
        self._strategy_scores[strategy].append(quality)
        # Keep last 100 scores
        if len(self._strategy_scores[strategy]) > 100:
            self._strategy_scores[strategy] = self._strategy_scores[strategy][-100:]

    def get_strategy_effectiveness(self) -> Dict[str, float]:
        """v10: Get average effectiveness of each strategy."""
        return {
            strategy: sum(scores) / len(scores)
            for strategy, scores in self._strategy_scores.items()
            if scores
        }

    def get_tool_definitions(self) -> List[Tool]:
        """Get all available tools for ReAct."""
        return AVAILABLE_TOOLS

# ═══════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════

def _is_persian(text: str) -> bool:
    """Detect if text is primarily Persian/Farsi."""
    if not text:
        return False
    persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\uFB50' <= c <= '\uFDFF')
    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return persian_chars > latin_chars

# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Reasoning Engine
# ══════════════════════════════════════════════════════════════



