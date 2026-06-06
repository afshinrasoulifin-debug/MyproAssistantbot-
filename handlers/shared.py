
from __future__ import annotations
"""
tg_bot/handlers/shared.py
─────────────────────────
Shared helpers used across multiple handler modules.

v29.0.0:
  • ai_generate: unified AI helper with automatic retry
  • extract_args: better input sanitization
  • brand_ctx & products_ctx: richer context
  • format_ai_response: post-process AI output
"""


from arki_project.utils.data_store import store

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]



# ═══════════════════ DEFAULT BRAND ═══════════════════
# Single source of truth — used when user hasn't set /brand yet.
DEFAULT_BRAND_INFO = {
    "name": "Handmade concrete/stone candles & accessories",
    "location": "Finland",
    "style": "Minimalist Scandinavian",
    "tone": "Warm, authentic, premium artisan",
    "languages": "EN, FI",
    "products": "Handmade concrete candles, tealight holders, decorative accessories",
    "price_range": "€10-50",
}


_MAX_INPUT_LEN = 4000  # Max chars accepted from user input


def extract_args(text: str, command: str) -> str:
    """
    Extract arguments after a /command.

    Handles:
      /command args       → "args"
      /command@botname args → "args"
      empty               → ""
    """
    if not text:
        return ""
    first = text.split()[0] if text.split() else ""
    if "@" in first:
        raw = text[len(first):].strip()
    elif text.startswith(command):
        raw = text[len(command):].strip()
    else:
        raw = text.strip()
    # Sanitize: limit length, strip null bytes, strip leading/trailing whitespace
    return raw[:_MAX_INPUT_LEN].replace("\x00", "").strip()


def brand_ctx(chat_id: int) -> str:
    """
    Return brand context string for AI prompts.

    Uses user-defined brand (from /brand) if available,
    otherwise falls back to DEFAULT_BRAND_INFO.
    """
    b = store.get_brand(chat_id)
    if b:
        parts = []
        if b.get("name"):
            parts.append(f"Brand: {b['name']}")
        if b.get("slogan"):
            parts.append(f"Slogan: {b['slogan']}")
        if b.get("style"):
            parts.append(f"Style: {b['style']}")
        if b.get("audience"):
            parts.append(f"Audience: {b['audience']}")
        if b.get("tone"):
            parts.append(f"Tone: {b['tone']}")
        if b.get("colors"):
            parts.append(f"Colors: {b['colors']}")
        if b.get("location"):
            parts.append(f"Location: {b['location']}")
        if b.get("languages"):
            parts.append(f"Languages: {b['languages']}")
        return "\n".join(parts) + "\n" if parts else _default_brand_ctx()
    return _default_brand_ctx()


def _default_brand_ctx() -> str:
    d = DEFAULT_BRAND_INFO
    return (
        f"Brand: {d['name']}, {d['location']}-based.\n"
        f"Style: {d['style']}\n"
        f"Tone: {d['tone']}\n"
        f"Languages: {d['languages']}\n"
    )


def products_ctx(chat_id: int) -> str:
    """
    Return products context string for AI prompts.

    Uses user's product catalog if available.
    """
    prods = store.get_products(chat_id)
    if prods:
        lines = []
        for pid, p in prods.items():
            line = f"- {p.get('name', '?')} (€{p.get('price', '?')})"
            if p.get("desc"):
                line += f": {p['desc']}"
            if p.get("category"):
                line += f" [{p['category']}]"
            lines.append(line)
        return "Products:\n" + "\n".join(lines) + "\n"

    d = DEFAULT_BRAND_INFO
    return f"Products: {d['products']} ({d['price_range']})\n"


# ═══════════════════ UNIFIED AI HELPER ═══════════════════

async def ai_generate(
    ai_client: "AIClient",
    settings: "Settings",
    prompt: str,
    *,
    system_prompt: str = "",
    model_key: str = "",
    user_id: int = 0,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """
    Unified AI generation helper for all handlers.

    Resolves the working model, calls ask_raw, and returns the answer.
    Handles the common pattern of:
      1. Resolve working model (with fallback)
      2. Build messages
      3. Call AI
      4. Return response
    """
    from arki_project.utils.models_registry import working_model_key

    # If user_id provided, use their configured model as base
    if user_id and not model_key:
        cfg = await ai_client.get_user_config(user_id)
        model_key = cfg.get("model", "gemini-pro")

    mk = working_model_key(
        model_key or "gemini-pro",
        settings.ai_api_key,
        settings.groq_api_key,
    )
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    return await ai_client.ask_raw(
        messages, mk,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def format_ai_response(text: str, prefix: str = "", suffix: str = "") -> str:
    """Post-process AI response for Telegram display."""
    # Strip common AI prefixes
    for noise in ("Sure!", "Of course!", "Here's", "Here is"):
        if text.startswith(noise):
            text = text[len(noise):].lstrip(": \n")

    # Combine prefix + text + suffix
    parts = []
    if prefix:
        parts.append(prefix)
    parts.append(text)
    if suffix:
        parts.append(suffix)

    return "\n\n".join(parts)


def safe_user_id(message: str) -> int:
    """Safely extract user ID from a message. Raises ValueError if unavailable."""
    if message.from_user is None:
        raise ValueError("Message has no from_user (channel post or anonymous)")
    return message.from_user.id


def safe_user_name(message: str) -> str:
    """Safely extract user's first name for display."""
    if message.from_user is None:
        return "کاربر"
    return message.from_user.first_name or message.from_user.username or "کاربر"


