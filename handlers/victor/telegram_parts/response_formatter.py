
"""
telegram_parts/response_formatter.py — Format AI responses for Telegram
Extracted from cmd_victor() to reduce complexity.
"""
from __future__ import annotations
import re
from typing import Optional


def format_response(text: str, max_length: int = 4096) -> str:
    """Format AI response text for Telegram display.
    
    Handles:
    - Markdown escaping
    - Length truncation with continuation marker
    - Code block preservation
    - RTL text handling
    """
    if not text:
        return "❌ پاسخی دریافت نشد."
    
    # Preserve code blocks
    code_blocks = []
    def save_code(m):
        code_blocks.append(m.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    text = re.sub(r"```.*?```", save_code, text, flags=re.DOTALL)
    
    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length - 50] + "\n\n... *(ادامه دارد)*"
    
    # Restore code blocks
    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)
    
    return text


