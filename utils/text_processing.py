
"""
utils/text_processing.py — Text cleanup, STM pipeline, Telegram splitting
──────────────────────────────────────────────────────────────────────────
Semantic Transformation Modules ported from APEX-main.
"""
from __future__ import annotations

import re
from typing import Final, Tuple

# ═══════════════════ THINK TAG REMOVAL ═══════════════════

_THINK_TAG_PATTERN: Final[re.Pattern] = re.compile(r"<think>.*?</think>", re.DOTALL)

# ═══════════════════ STM PATTERNS (pre-compiled) ═══════════════════

# Phase 2: direct_mode — strip preambles
_STM_PREAMBLE_PATTERNS: Final[Tuple[re.Pattern, ...]] = (
    re.compile(r"^(Sure,?\s*)", re.IGNORECASE),
    re.compile(r"^(Of course,?\s*)", re.IGNORECASE),
    re.compile(r"^(Certainly,?\s*)", re.IGNORECASE),
    re.compile(r"^(Absolutely,?\s*)", re.IGNORECASE),
    re.compile(r"^(Great question!?\s*)", re.IGNORECASE),
    re.compile(r"^(That's a great question!?\s*)", re.IGNORECASE),
    re.compile(r"^(I'd be happy to help( you)?( with that)?[.!]?\s*)", re.IGNORECASE),
    re.compile(r"^(Let me help you with that[.!]?\s*)", re.IGNORECASE),
    re.compile(r"^(I understand[.!]?\s*)", re.IGNORECASE),
    re.compile(r"^(Thanks for asking[.!]?\s*)", re.IGNORECASE),
)

# Phase 3: hedge_reducer — remove hedging language
_STM_HEDGE_PATTERNS: Final[Tuple[re.Pattern, ...]] = (
    re.compile(r"\bI think\s+", re.IGNORECASE),
    re.compile(r"\bI believe\s+", re.IGNORECASE),
    re.compile(r"\bperhaps\s+", re.IGNORECASE),
    re.compile(r"\bmaybe\s+", re.IGNORECASE),
    re.compile(r"\bIt seems like\s+", re.IGNORECASE),
    re.compile(r"\bIt appears that\s+", re.IGNORECASE),
    re.compile(r"\bprobably\s+", re.IGNORECASE),
    re.compile(r"\bpossibly\s+", re.IGNORECASE),
    re.compile(r"\bI would say\s+", re.IGNORECASE),
    re.compile(r"\bIn my opinion,?\s*", re.IGNORECASE),
    re.compile(r"\bFrom my perspective,?\s*", re.IGNORECASE),
)

# Phase 4: casual_mode — formal→casual substitutions
_STM_CASUAL_RULES: Final[Tuple[Tuple[re.Pattern, str], ...]] = (
    (re.compile(r"\bHowever\b"), "But"),
    (re.compile(r"\bTherefore\b"), "So"),
    (re.compile(r"\bFurthermore\b"), "Also"),
    (re.compile(r"\bAdditionally\b"), "Plus"),
    (re.compile(r"\bNevertheless\b"), "Still"),
    (re.compile(r"\bConsequently\b"), "So"),
    (re.compile(r"\bMoreover\b"), "Also"),
    (re.compile(r"\bUtilize\b"), "Use"),
    (re.compile(r"\butilize\b"), "use"),
    (re.compile(r"\bPurchase\b"), "Buy"),
    (re.compile(r"\bpurchase\b"), "buy"),
    (re.compile(r"\bObtain\b"), "Get"),
    (re.compile(r"\bobtain\b"), "get"),
    (re.compile(r"\bCommence\b"), "Start"),
    (re.compile(r"\bcommence\b"), "start"),
    (re.compile(r"\bTerminate\b"), "End"),
    (re.compile(r"\bterminate\b"), "end"),
    (re.compile(r"\bPrior to\b", re.IGNORECASE), "Before"),
    (re.compile(r"\bSubsequent to\b", re.IGNORECASE), "After"),
    (re.compile(r"\bIn order to\b", re.IGNORECASE), "To"),
    (re.compile(r"\bDue to the fact that\b", re.IGNORECASE), "Because"),
    (re.compile(r"\bAt this point in time\b", re.IGNORECASE), "Now"),
    (re.compile(r"\bIn the event that\b", re.IGNORECASE), "If"),
)

_SENTENCE_START = re.compile(r"^\s*([a-z])", re.MULTILINE)


def clean_think_tags(text: str) -> str:
    """Remove <think>…</think> + full STM pipeline (5 phases)."""
    if not text:
        return ""
    text = _THINK_TAG_PATTERN.sub("", text).strip()
    for pat in _STM_PREAMBLE_PATTERNS:
        text = pat.sub("", text)
    for pat in _STM_HEDGE_PATTERNS:
        text = pat.sub("", text)
    for pat, repl in _STM_CASUAL_RULES:
        text = pat.sub(repl, text)
    text = _SENTENCE_START.sub(lambda m: m.group(1).upper(), text)
    return text.strip()


# ═══════════════════ TELEGRAM HELPERS ═══════════════════

def split_for_telegram(text: str, max_len: int = 4096) -> list[str]:
    """Split long text into Telegram-safe chunks."""
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        idx = text.rfind("\n", 0, max_len)
        if idx == -1:
            idx = text.rfind(" ", 0, max_len)
        if idx == -1:
            idx = max_len
        parts.append(text[:idx])
        text = text[idx:].lstrip()
    return parts


def user_friendly_error(exc: Exception) -> str:
    """Convert exception to user-facing Persian error message."""
    s = str(exc).lower()
    if "429" in s or "rate" in s or "quota" in s:
        return "⏳ محدودیت نرخ. چند ثانیه صبر کن و دوباره بزن."
    if any(w in s for w in ("high demand", "overload", "503", "502", "unavailable", "capacity")):
        return "⏳ سرورها شلوغ‌اند. چند ثانیه صبر کن و دوباره بزن."
    if "401" in s or "unauth" in s:
        return "🔑 کلید API نامعتبره."
    if "404" in s:
        return "❌ مدل غیرفعاله. `/model` برای تغییر"
    if "timeout" in s:
        return "⏱ تایم‌اوت. دوباره تلاش کن."
    if "block" in s or "safety" in s:
        return "🛡 فیلتر ایمنی فعال شد. درخواست رو تغییر بده."
    return f"⚠️ {str(exc)[:200]}"


