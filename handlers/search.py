
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/search.py
─────────────────────────
Web search handlers: /search, /deep.

Uses Gemini grounding (Google Search integration).
"""


import logging

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.config import Settings
from arki_project.utils.web_search import deep_search, search_with_gemini
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args
from arki_project.utils.v7_core import (
    store_result,
)

logger = logging.getLogger(__name__)
# v9.2: Jina reader for URL content extraction

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
router = Router(name="search")

MAX_TELEGRAM_LENGTH = 4096


@router.message(Command("search"))
async def cmd_search(message: Message, settings: Settings) -> None:
    """Search the web using Gemini grounding."""
    query = extract_args(message.text or "", "/search")
    if not query:
        await safe_reply(message, "🔍 *Web Search*\n\n"
            "Usage: `/search latest candle market trends`\n"
            "I'll search the web and give you a sourced answer.")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING
    )

    status = await message.answer("🔍 Searching the web...")

    try:
        answer = await search_with_gemini(
            query,
            settings.ai_api_key,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
        )
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        for chunk in _split_text(answer):
            try:
                await safe_reply(message, chunk)
            except HandlerError:
                await message.answer(chunk)
    except HandlerError as e:
        logger.error("Search failed: %s", e)
        await safe_edit_text(status, f"⚠️ Search failed:\n`{str(e)[:200]}`")


@router.message(Command("deep"))
async def cmd_deep(message: Message, settings: Settings) -> None:
    """Multi-angle deep research."""
    query = extract_args(message.text or "", "/deep")
    if not query:
        await safe_reply(message, "🔬 *Deep Research*\n\n"
            "Usage: `/deep how to price handmade candles`\n"
            "I'll search from multiple angles and synthesize a report.")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING
    )

    status = await message.answer("🔬 Deep research in progress (multi-angle)...")

    try:
        answer = await deep_search(
            query,
            settings.ai_api_key,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
        )
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        for chunk in _split_text(answer):
            try:
                await safe_reply(message, chunk)
            except HandlerError:
                await message.answer(chunk)
    except HandlerError as e:
        logger.error("Deep search failed: %s", e)
        await safe_edit_text(status, f"⚠️ Deep search failed:\n`{str(e)[:200]}`")




def _split_text(text: str, max_len: int = MAX_TELEGRAM_LENGTH) -> list[str]:
    if len(text) <= max_len:
        return [text]

    parts: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current:
            parts.append(current.strip())
        while len(paragraph) > max_len:
            split_at = paragraph.rfind("\n", 0, max_len)
            if split_at < 100:
                split_at = max_len
            parts.append(paragraph[:split_at].strip())
            paragraph = paragraph[split_at:].lstrip()
        current = paragraph

    if current:
        parts.append(current.strip())
    return parts



# ═══════════ /recon — Web Reconnaissance via web_recon module ═══════════

@router.message(Command("recon"))
async def cmd_recon(message: Message, settings: Settings) -> None:
    """Deep web reconnaissance: analyze a domain's technology, security, DNS."""
    target = extract_args(message.text or "", "/recon")
    if not target:
        await safe_reply(
            message,
            "🔎 *Web Recon — آنالیز وبسایت*\n\n"
            "Usage: `/recon example.com`\n\n"
            "_تکنولوژی، SSL، هدرهای امنیتی، DNS و امتیاز امنیتی رو بررسی می‌کنم._",
        )
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer("🔎 در حال آنالیز...")

    try:
        import time as _t
        _t0 = _t.time()

        from arki_project.utils.web_recon import full_recon
        report = await full_recon(target)
        report_d = report.to_dict()

        await safe_delete(status)

        output = f"🔎 *Web Recon:* `{target}`\n\n"

        if report_d.get("security_headers"):
            output += "*🔒 هدرهای امنیتی:*\n"
            for h in report_d["security_headers"][:8]:
                emoji = "✅" if h.get("present") else "❌"
                output += f"  {emoji} `{h['name']}`\n"
            output += "\n"

        if report_d.get("technologies"):
            techs = report_d["technologies"]
            output += f"*🛠 تکنولوژی‌ها ({len(techs)}):*\n"
            for t in techs[:10]:
                ver = f" v{t['version']}" if t.get("version") else ""
                output += f"  • {t['name']}{ver} ({t.get('category', '')})\n"
            output += "\n"

        if report_d.get("dns"):
            output += "*🌐 DNS:*\n"
            for rec in report_d["dns"][:6]:
                output += f"  {rec['type']}: {rec['value']}\n"
            output += "\n"

        score = report_d.get("security_score", 0)
        grade = (
            "A+" if score >= 90
            else "A" if score >= 80
            else "B" if score >= 70
            else "C" if score >= 50
            else "D"
        )
        output += f"*📊 امتیاز امنیتی: {score}/100 ({grade})*\n"

        _duration = _t.time() - _t0
        store_result(
            message.from_user.id if message.from_user else 0,
            f"recon:{target}", output[:500], "recon", duration_s=_duration,
        )

        for chunk in _split_text(output):
            try:
                await safe_reply(message, chunk)
            except HandlerError:
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Recon failed for %s: %s", target, exc, exc_info=True)
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        await message.answer(f"⚠️ Recon failed: {str(exc)[:200]}")


