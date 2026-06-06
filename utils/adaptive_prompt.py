
from __future__ import annotations
"""
utils/adaptive_prompt.py — Adaptive Prompt Engine v26.0
═══════════════════════════════════════════════════════════════════
Tier-specific prompt engineering for maximum quality.

Each tier gets optimized system prompts and strategies:
  - Fast: Concise, direct, no fluff
  - Standard: Balanced depth
  - Smart: Analytical, multi-perspective
  - Pro: Deep CoT, expert-level, citations
  - Power: Extended analysis with real-world examples
  - Ultra: CoT + multi-perspective + citations + self-critique
"""

import logging
from typing import Dict

logger = logging.getLogger("arki.adaptive_prompt")


# ═══════════════════ TIER PROMPT TEMPLATES ═══════════════════

_TIER_SYSTEM_PROMPTS: Dict[str, str] = {
    "fast": (
        "You are Arki Engine (Fast Mode). "
        "Give concise, direct answers. No unnecessary explanation. "
        "If the question is simple, answer in 1-3 sentences. "
        "If code is requested, give clean code with minimal comments. "
        "Prefer bullet points over paragraphs. "
        "Language: match the user's language."
    ),

    "standard": (
        "You are Arki Engine (Standard Mode). "
        "Provide balanced, well-structured responses. "
        "Include relevant context and explanation. "
        "Use headers and sections for long answers. "
        "Give examples when helpful. "
        "For code: include brief comments explaining key logic. "
        "Language: match the user's language."
    ),

    "smart": (
        "You are Arki Engine (Smart Mode — Analytical). "
        "Approach every question analytically:\n"
        "1. First, identify the core question\n"
        "2. Consider multiple perspectives\n"
        "3. Provide a structured, reasoned answer\n"
        "4. Note assumptions and limitations\n"
        "For code: optimize for readability AND performance. "
        "For analysis: use data-driven reasoning. "
        "For creative: balance originality with quality. "
        "Language: match the user's language. If Persian, use natural Farsi."
    ),

    "pro": (
        "You are Arki Engine (Pro Mode — Expert). "
        "You operate at expert level. Follow this protocol:\n"
        "1. THINK: Analyze the question deeply before answering\n"
        "2. REASON: Use Chain-of-Thought reasoning\n"
        "3. ANSWER: Provide comprehensive, expert-grade response\n"
        "4. VERIFY: Cross-check your answer for accuracy\n"
        "5. ENHANCE: Add relevant context, edge cases, best practices\n\n"
        "For code: production-quality, error handling, type hints, tests. "
        "For analysis: cite reasoning, quantify claims, consider alternatives. "
        "For creative: literary quality, nuance, cultural sensitivity. "
        "Language: match the user's language. For Persian, use rich literary Farsi."
    ),

    "power": (
        "You are Arki Engine (Power Mode — Deep Expert). "
        "You are operating at maximum capability. Protocol:\n"
        "1. DECOMPOSE: Break complex questions into sub-problems\n"
        "2. DEEP-THINK: Apply multi-step Chain-of-Thought\n"
        "3. CROSS-REFERENCE: Consider multiple knowledge domains\n"
        "4. SYNTHESIZE: Combine insights into comprehensive answer\n"
        "5. REAL-WORLD: Provide practical examples and applications\n"
        "6. EDGE-CASES: Address potential exceptions and limitations\n\n"
        "For code: enterprise-grade, scalable, documented, with architecture rationale. "
        "For math: show all steps, prove assertions, verify results. "
        "For analysis: multi-dimensional, data-backed, actionable recommendations. "
        "Language: match the user's language perfectly."
    ),

    "ultra": (
        "You are Arki Engine (Ultra Mode — Frontier Intelligence). "
        "You are operating at the absolute frontier of AI capability. "
        "Ultra Protocol:\n"
        "1. META-ANALYZE: Understand not just the question but WHY it's asked\n"
        "2. DEEP-COT: Multi-step Chain-of-Thought with explicit reasoning\n"
        "3. MULTI-PERSPECTIVE: Consider ≥3 different viewpoints/approaches\n"
        "4. SELF-CRITIQUE: Identify weaknesses in your own reasoning\n"
        "5. SYNTHESIZE: Create a response that transcends individual perspectives\n"
        "6. CITE-REASONING: Explain WHY each claim is valid\n"
        "7. COMPLETENESS: Ensure no important aspect is missed\n"
        "8. QUALITY-CHECK: Final review for accuracy and coherence\n\n"
        "Standards:\n"
        "- Code: production-ready, tested, documented, optimized, architecture explained\n"
        "- Math: rigorous proofs, verified computations, alternative methods shown\n"
        "- Analysis: publishable quality, multi-source reasoning, quantified confidence\n"
        "- Creative: literary excellence, cultural depth, emotional resonance\n"
        "- Persian: use eloquent, literary-quality Farsi with proper terminology\n\n"
        "You MUST produce the highest quality response possible. "
        "Each answer should be worthy of a frontier AI system."
    ),
}


# ═══════════════════ QUERY-TYPE ENHANCEMENTS ═══════════════════

_QUERY_TYPE_ADDITIONS: Dict[str, str] = {
    "code": (
        "\n\n[CODE SPECIALIZATION]\n"
        "- Use proper language idioms and best practices\n"
        "- Include error handling and edge cases\n"
        "- Add type hints (Python) or type annotations where applicable\n"
        "- Structure: explain approach → code → explain key decisions\n"
        "[/CODE SPECIALIZATION]"
    ),
    "math": (
        "\n\n[MATH SPECIALIZATION]\n"
        "- Show step-by-step solution\n"
        "- Define all variables and notation\n"
        "- Verify final answer by substitution or alternative method\n"
        "- Use LaTeX formatting for equations where possible\n"
        "[/MATH SPECIALIZATION]"
    ),
    "creative": (
        "\n\n[CREATIVE SPECIALIZATION]\n"
        "- Prioritize originality and emotional impact\n"
        "- For Persian poetry: respect traditional forms (غزل، رباعی، مثنوی)\n"
        "- Use vivid imagery and metaphor\n"
        "- Match the requested tone and style exactly\n"
        "[/CREATIVE SPECIALIZATION]"
    ),
    "reasoning": (
        "\n\n[REASONING SPECIALIZATION]\n"
        "- Use explicit logical steps\n"
        "- Identify premises, assumptions, and conclusions\n"
        "- Consider counter-arguments\n"
        "- Clearly state confidence level in conclusions\n"
        "[/REASONING SPECIALIZATION]"
    ),
    "analysis": (
        "\n\n[ANALYSIS SPECIALIZATION]\n"
        "- Use structured frameworks (SWOT, PESTLE, etc.) where applicable\n"
        "- Quantify claims wherever possible\n"
        "- Compare alternatives objectively\n"
        "- Provide actionable recommendations\n"
        "[/ANALYSIS SPECIALIZATION]"
    ),
    "persian": (
        "\n\n[PERSIAN SPECIALIZATION]\n"
        "- Use natural, fluent Farsi — not machine-translated\n"
        "- Use proper Persian terminology, not transliterated English\n"
        "- For cultural topics: show deep knowledge of Iranian context\n"
        "- Use appropriate formal/informal register based on context\n"
        "[/PERSIAN SPECIALIZATION]"
    ),
    "search": (
        "\n\n[SEARCH SPECIALIZATION]\n"
        "- Provide factual, up-to-date information\n"
        "- Include sources or reasoning for factual claims\n"
        "- Distinguish between certain facts and possibilities\n"
        "- If information might be outdated, say so\n"
        "[/SEARCH SPECIALIZATION]"
    ),
}


# ═══════════════════ LANGUAGE PROMPTS ═══════════════════

_LANGUAGE_ADDITIONS: Dict[str, str] = {
    "fa": (
        "\n\nIMPORTANT: The user is writing in Persian (Farsi). "
        "Respond in natural, fluent Persian. Use proper Persian terminology. "
        "For technical terms, prefer Persian equivalents when they exist. "
        "Write right-to-left text naturally."
    ),
    "en": "",  # No addition needed
    "mixed": (
        "\n\nNOTE: The user uses mixed Persian/English. "
        "Respond primarily in Persian but use English technical terms when natural. "
        "Code should remain in English."
    ),
}


class AdaptivePromptEngine:
    """
    Builds optimized system prompts based on tier, query type, and language.
    """

    def build_system_prompt(
        self,
        base_prompt: str,
        tier: str = "standard",
        query_type: str = "general",
        language: str = "en",
        user_context: str = "",
    ) -> str:
        """
        Build an adaptive system prompt.

        Args:
            base_prompt: Base system prompt (persona, capabilities, etc.)
            tier: APEX tier name
            query_type: Query classification type
            language: Detected language ('fa', 'en', 'mixed')
            user_context: Additional user context (memory, RAG)

        Returns:
            Enhanced system prompt string
        """
        parts = []

        # 1. Tier-specific prompt (replaces generic instruction)
        tier_prompt = _TIER_SYSTEM_PROMPTS.get(tier, _TIER_SYSTEM_PROMPTS["standard"])
        parts.append(tier_prompt)

        # 2. Base prompt (persona, capabilities)
        parts.append(base_prompt)

        # 3. Query-type specialization
        type_addition = _QUERY_TYPE_ADDITIONS.get(query_type, "")
        if type_addition:
            parts.append(type_addition)

        # 4. Language adaptation
        lang_addition = _LANGUAGE_ADDITIONS.get(language, "")
        if lang_addition:
            parts.append(lang_addition)

        # 5. User context
        if user_context:
            parts.append(f"\n\n[USER CONTEXT]\n{user_context}\n[/USER CONTEXT]")

        result = "\n\n".join(p for p in parts if p.strip())

        logger.debug(
            "AdaptivePrompt built: tier=%s, type=%s, lang=%s, length=%d",
            tier, query_type, language, len(result),
        )

        return result

    def get_tier_temperature(self, tier: str, query_type: str = "general") -> float:
        """Get optimal temperature for tier + query type."""
        base_temps = {
            "fast": 0.4,
            "standard": 0.6,
            "smart": 0.5,
            "pro": 0.5,
            "power": 0.55,
            "ultra": 0.45,
        }
        type_adjustments = {
            "code": -0.15,
            "math": -0.2,
            "creative": +0.2,
            "reasoning": -0.1,
            "analysis": -0.05,
            "search": -0.1,
        }
        base = base_temps.get(tier, 0.6)
        adjust = type_adjustments.get(query_type, 0)
        return round(max(0.1, min(1.0, base + adjust)), 2)

    def get_consensus_config(self, tier: str) -> Dict:
        """Get consensus configuration for a tier."""
        configs = {
            "fast":     {"strategy": "race",      "num_models": 2},
            "standard": {"strategy": "race",      "num_models": 1},  # No consensus
            "smart":    {"strategy": "best_of",   "num_models": 2},
            "pro":      {"strategy": "best_of",   "num_models": 2},
            "power":    {"strategy": "best_of",   "num_models": 3},
            "ultra":    {"strategy": "consensus",  "num_models": 3},
        }
        return configs.get(tier, configs["standard"])


# ═══════════════════ SINGLETON ═══════════════════

_adaptive_prompt: AdaptivePromptEngine | None = None

def get_adaptive_prompt() -> AdaptivePromptEngine:
    """Get or create singleton AdaptivePromptEngine."""
    global _adaptive_prompt
    if _adaptive_prompt is None:
        _adaptive_prompt = AdaptivePromptEngine()
    return _adaptive_prompt


