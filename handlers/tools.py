
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/tools.py
────────────────────────
Specialty command handlers that call the AI with tuned system prompts:

  /translate, /summarize, /code, /rewrite, /explain, /math, /brainstorm
"""


import logging

from aiogram import Router
from arki_project.utils.safe_send import safe_reply
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.safe_send import safe_reply
from arki_project.handlers.shared import extract_args
from arki_project.utils.v7_core import (


# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

    enhance_system_prompt, store_result, get_memory,
)

logger = logging.getLogger(__name__)

# v9.1: Pipeline integration
try:
    from arki_project.utils.v7_core import get_pipeline, get_memory
except HandlerError as exc:
    logger.error("Error in handler: %s", exc)
    get_pipeline = None
    get_memory = None
router = Router(name="tools")


# ══════════ helper ══════════

async def _specialty(
    message: Message,
    ai_client: AIClient,
    settings: Settings,
    *,
    cmd_name: str,
    system_prompt: str,
    prefix_emoji: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> None:
    """Shared logic for all specialty commands."""
    text = extract_args(message.text or "", f"/{cmd_name}")
    if not text:
        await safe_reply(message, f"{prefix_emoji} `/{cmd_name} متن/سوال`")
        return

    user_id = message.from_user.id  # type: ignore[union-attr]

    # Typing indicator.
    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        cfg = await ai_client.get_user_config(user_id)
        mk = working_model_key(
            cfg["model"], settings.ai_api_key, settings.groq_api_key,
        )

        import time as _t; _t0 = _t.time()
        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt(system_prompt, user_text=text, user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": text},
            ],
            model_key=mk,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        store_result(message.from_user.id if message.from_user else 0, text[:300], answer[:500] if answer else "", "tools", duration_s=_t.time()-_t0)
        for chunk in split_for_telegram(f"{prefix_emoji}\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ══════════ /translate ══════════

@router.message(Command("translate"))
async def cmd_translate(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="translate",
        system_prompt=(
            "Professional translator. Persian↔English. Auto-detect and "
            "translate. Only output the translation, nothing else."
        ),
        prefix_emoji="🌐 *ترجمه:*",
        temperature=0.3,
    )


# ══════════ /summarize ══════════

@router.message(Command("summarize"))
async def cmd_summarize(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="summarize",
        system_prompt=(
            "Summarize concisely in the same language. Use bullet points "
            "for key points. Be thorough but brief."
        ),
        prefix_emoji="📝 *خلاصه:*",
        temperature=0.3,
    )


# ══════════ /code ══════════

@router.message(Command("code"))
async def cmd_code(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="code",
        system_prompt=(
            "World-class programmer. Write clean, production-ready, "
            "well-commented code. Use proper code blocks with language "
            "tags. Handle edge cases."
        ),
        prefix_emoji="💻 *کد:*",
        temperature=0.12,
        max_tokens=8192,
    )


# ══════════ /polish ══════════

@router.message(Command("polish"))
async def cmd_polish(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="polish",
        system_prompt=(
            "Rewrite this text: make it clearer, more professional, "
            "better structured. Preserve the meaning. Same language."
        ),
        prefix_emoji="✏️ *بازنویسی:*",
        temperature=0.6,
    )


# ══════════ /explain ══════════

@router.message(Command("explain"))
async def cmd_explain(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="explain",
        system_prompt=(
            "Explain this concept simply as if to a 15-year-old. "
            "Use analogies, examples, and step-by-step explanations. "
            "Same language."
        ),
        prefix_emoji="📖 *توضیح:*",
        temperature=0.5,
    )


# ══════════ /math ══════════

@router.message(Command("math"))
async def cmd_math(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="math",
        system_prompt=(
            "Expert mathematician. Solve step by step, show all work. "
            "Use proper notation. Double-check your answer."
        ),
        prefix_emoji="🧮 *ریاضی:*",
        temperature=0.08,
        max_tokens=16384,
    )


# ══════════ /brainstorm ══════════

@router.message(Command("brainstorm"))
async def cmd_brainstorm(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await _specialty(
        message, ai_client, settings,
        cmd_name="brainstorm",
        system_prompt=(
            "Brainstorm 10+ creative, unique, and actionable ideas. "
            "Number each. Explain briefly why each is good. Same language."
        ),
        prefix_emoji="💡 *ایده:*",
        temperature=1.1,
    )

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
# ══════════ helper ══════════


