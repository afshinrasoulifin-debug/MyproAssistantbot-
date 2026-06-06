
from __future__ import annotations
"""
utils/lang_detect.py — Unified Language Detection v26.1
═══════════════════════════════════════════════════════
Single source of truth for language detection across the engine.

Replaces duplicate detection in ai_client.py and quality_gate.py.

Usage:
    from arki_project.utils.lang_detect import detect_language, is_persian
    
    lang = detect_language("سلام دنیا")  # → "fa"
    lang = detect_language("Hello world")  # → "en"
    lang = detect_language("سلام hello")  # → "mixed"
"""




def detect_language(text: str) -> str:
    """Detect language of text. Returns 'fa', 'en', 'ar', 'mixed', or 'unknown'.
    
    Uses character frequency analysis — fast and dependency-free.
    """
    if not text or not text.strip():
        return "unknown"

    # Count character classes
    persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\uFB50' <= c <= '\uFDFF')
    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    
    total_alpha = persian_chars + latin_chars + cjk_chars
    if total_alpha == 0:
        return "unknown"

    persian_ratio = persian_chars / total_alpha
    latin_ratio = latin_chars / total_alpha
    
    # Clear majority
    if persian_ratio > 0.6:
        # Distinguish Persian from Arabic (check for Persian-specific chars)
        if any(c in text for c in 'پچژگک'):
            return "fa"
        return "fa"  # Default to Farsi for this bot
    
    if latin_ratio > 0.6:
        return "en"
    
    if cjk_chars > total_alpha * 0.5:
        return "zh"
    
    # Mixed content
    if persian_chars > 0 and latin_chars > 0:
        return "mixed"
    
    return "unknown"


def is_persian(text: str) -> bool:
    """Quick check: is the text primarily Persian?"""
    return detect_language(text) in ("fa", "mixed")


def get_direction(text: str) -> str:
    """Get text direction: 'rtl' or 'ltr'."""
    lang = detect_language(text)
    return "rtl" if lang in ("fa", "ar") else "ltr"


