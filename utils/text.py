
from __future__ import annotations
"""
tg_bot/utils/text.py
────────────────────
Text utilities for Telegram message formatting.

v29.0.0:
  • escape_markdown: escape special Markdown characters
  • truncate_text: smart truncation with ellipsis
  • format_number: format numbers with separators
  • format_duration: human-readable duration
  • clean_for_ai: strip markup for AI prompts
"""


import re

# ── TITANIUM v29.0 Integration ──



def split_for_telegram(text: str, limit: int = 4080) -> list[str]:
    """Split long text into Telegram-safe chunks, preserving paragraphs."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        if len(current) + len(para) + 2 > limit:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current += ("\n\n" if current else "") + para
    if current:
        chunks.append(current.strip())

    # Sub-split any remaining over-sized chunks.
    final: list[str] = []
    for ch in chunks:
        while len(ch) > limit:
            # Try to split at newline
            sp = ch.rfind("\n", 0, limit)
            if sp < 100:
                # Try to split at sentence boundary
                sp = max(
                    ch.rfind(". ", 0, limit),
                    ch.rfind("! ", 0, limit),
                    ch.rfind("? ", 0, limit),
                    ch.rfind("؟ ", 0, limit),  # Persian question mark
                    ch.rfind("۔ ", 0, limit),  # Urdu full stop
                )
            if sp < 100:
                sp = limit
            final.append(ch[:sp])
            ch = ch[sp:].lstrip()
        if ch:
            final.append(ch)
    return final


def escape_markdown(text: str) -> str:
    """Escape Telegram Markdown V1 special characters."""
    special = r"_*[`"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


def truncate_text(text: str, max_len: int = 200, suffix: str = "…") -> str:
    """Truncate text intelligently at word boundary."""
    if len(text) <= max_len:
        return text
    truncated = text[: max_len - len(suffix)]
    # Try to cut at a space
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + suffix


def format_number(n: int | float, sep: str = ",") -> str:
    """Format a number with thousand separators."""
    if isinstance(n, float):
        return f"{n:,.2f}".replace(",", sep)
    return f"{n:,}".replace(",", sep)


def format_duration(seconds: int | float) -> str:
    """Format seconds into human-readable Persian duration."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} ثانیه"
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m} دقیقه" + (f" و {s} ثانیه" if s else "")
    h, remainder = divmod(seconds, 3600)
    m = remainder // 60
    return f"{h} ساعت" + (f" و {m} دقیقه" if m else "")


def clean_for_ai(text: str) -> str:
    """Strip Telegram markup and clean text for AI prompts."""
    # Remove markdown formatting
    text = re.sub(r"[*_`~]", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r"https?://[^\s<>\[\]()\"']+",
        re.IGNORECASE,
    )
    return url_pattern.findall(text)


def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def safe_markdown(text: str) -> str:
    """Make text safe for Telegram Markdown V1 by closing unclosed formatting.
    Prevents parse errors that cause message send failures."""
    # Count single asterisks (bold markers)
    bold_count = text.count("*") - text.count("\\*")
    if bold_count % 2 != 0:
        text += "*"  # Close unclosed bold
    
    # Count underscores (italic markers)
    italic_count = text.count("_") - text.count("\\_")
    if italic_count % 2 != 0:
        text += "_"  # Close unclosed italic
    
    # Count backticks (code markers) — only single, not triple
    code_count = text.count("`") - text.count("```") * 3
    if code_count % 2 != 0:
        text += "`"  # Close unclosed code
    
    return text


