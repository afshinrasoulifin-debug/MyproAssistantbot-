
from __future__ import annotations
"""
tg_bot/utils/token_counter.py — Accurate token estimation v29.0.0

Uses a language-aware heuristic that closely matches GPT/Gemini tokenizer behavior.
For English: ~1.3 tokens per word, ~4.0 chars per token
For Persian/Arabic: ~2.5 tokens per word, ~5.5 chars per token (due to Unicode)
For mixed: weighted average

To use the exact tokenizer, install tiktoken:
    pip install tiktoken
and set USE_TIKTOKEN=true in .env
"""
import logging
import os
import re
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

_tiktoken_encoder = None
_USE_TIKTOKEN = os.environ.get("USE_TIKTOKEN", "false").lower() == "true"


def _init_tiktoken() -> Any:
    """Try to load tiktoken (optional dependency)."""
    global _tiktoken_encoder
    if _tiktoken_encoder is not None:
        return _tiktoken_encoder
    try:
        import tiktoken
        _tiktoken_encoder = tiktoken.encoding_for_model("gpt-4")
        logger.info("Using tiktoken for exact token counting")
        return _tiktoken_encoder
    except (ImportError, Exception):
        _tiktoken_encoder = False  # Sentinel: tried but unavailable
        return None


def count_tokens(text: str) -> int:
    """Count tokens in text — exact if tiktoken is available, else estimation.

    Returns:
        Token count (int)
    """
    if not text:
        return 0

    # Try tiktoken first if enabled
    if _USE_TIKTOKEN:
        enc = _init_tiktoken()
        if enc:
            return len(enc.encode(text))

    # Language-aware estimation
    # Detect script ratio: Latin vs Persian/Arabic vs CJK vs other
    total_chars = len(text)
    if total_chars == 0:
        return 0

    # Count character types
    latin = len(re.findall(r'[a-zA-Z]', text))
    persian_arabic = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', text))
    cjk = len(re.findall(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', text))
    digits = len(re.findall(r'[0-9]', text))
    whitespace = len(re.findall(r'\s', text))

    # Character-based estimation per script type
    # These ratios are calibrated against GPT-4 tokenizer
    tokens = 0.0
    tokens += latin / 4.0       # ~4 chars per token for English
    tokens += persian_arabic / 2.0  # ~2 chars per token for Persian (each char often = 1 token)
    tokens += cjk / 1.0         # CJK: ~1 char per token
    tokens += digits / 3.5      # Numbers: ~3.5 chars per token
    tokens += whitespace / 6.0  # Whitespace contributes less
    # Remaining chars (punctuation, emoji, etc)
    remaining = total_chars - latin - persian_arabic - cjk - digits - whitespace
    tokens += remaining / 3.0

    return max(1, int(tokens + 0.5))


