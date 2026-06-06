
"""
ai_client_pkg/helpers.py — standalone functions
Arki Engine v29.0.0
"""
from ._base import *  # noqa

def smart_select_temperature(text: str, category: str = "chat") -> float:
    """
    v10: Select optimal temperature based on task type.

    Low temperature (0.1-0.4): Factual, code, math, analysis
    Medium temperature (0.5-0.7): General chat, search
    High temperature (0.7-0.9): Creative writing, brainstorming
    """
    text_lower = text.lower()

    # Code generation → very low temperature for precision
    if category == "code" or any(w in text_lower for w in [
        "```", "code", "function", "class", "debug", "کد", "برنامه",
        "python", "javascript", "sql",
    ]):
        return 0.2

    # Math / calculation → lowest temperature
    if any(w in text_lower for w in [
        "calculate", "محاسبه", "math", "ریاضی", "equation", "formula",
    ]):
        return 0.1

    # Analysis / research → low-medium
    if category in ("analysis", "research") or any(w in text_lower for w in [
        "analyze", "تحلیل", "بررسی", "مقایسه", "compare", "research",
    ]):
        return 0.4

    # Security / technical → low
    if category == "security":
        return 0.3

    # Creative writing → high temperature
    if category == "creative" or any(w in text_lower for w in [
        "بنویس", "write", "story", "داستان", "شعر", "poem", "خلاقانه",
        "creative", "brainstorm",
    ]):
        return 0.85

    # Sales / marketing → medium-high
    if category == "sales":
        return 0.7

    # Default chat
    return 0.6



def smart_estimate_max_tokens(text: str, category: str = "chat") -> int:
    """
    v10: Estimate appropriate max_tokens to avoid waste.

    Shorter queries need shorter responses. Save tokens/cost.
    """
    word_count = len(text.split())

    # v10.2: TITANIUM — all limits removed, Pro/Ultra token allocations
    if category == "code":
        return 131072  # v10.2: Full code output
    elif category == "research":
        return 131072  # v10.2: Deep research
    elif category == "analysis":
        return 65536   # v10.2: Full analysis
    elif category in ("chat", "system"):
        if word_count < 5:
            return 16384   # v10.2: Even simple chats get room
        elif word_count < 20:
            return 32768
        else:
            return 65536
    elif category == "creative":
        return 131072  # v10.2: Full creative
    else:
        return 65536   # v10.2: Default high



def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with CSPRNG jitter: 2s, 4s, 8s... capped at 30s."""
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
    # v10: CSPRNG jitter instead of random.uniform (predictable)
    try:
        from arki_project.utils.titanium.crypto import csprng_float
        jitter = csprng_float() * delay * 0.3
    except ImportError:
        import random as _rnd
        jitter = _rnd.uniform(0, delay * 0.3)
    return delay + jitter




