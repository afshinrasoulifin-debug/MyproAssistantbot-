
from __future__ import annotations
"""
tg_bot/handlers/inline_handler.py — Telegram Inline Mode
Allows using the bot directly from any chat via @botusername query.
"""
import logging
import hashlib
from aiogram import Router
from aiogram.types import (

    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
)



logger = logging.getLogger(__name__)
router = Router(name="inline")


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery) -> None:
    """Handle inline queries from any chat."""
    query = inline_query.query.strip()

    if not query:
        # Show help when no query
        results = [
            InlineQueryResultArticle(
                id="help",
                title="🤖 Arki Engine",
                description="پیام خود را تایپ کنید...",
                input_message_content=InputTextMessageContent(
                    message_text="🤖 *Arki Engine*\n\nبرای استفاده، متن خود را بعد از نام بات تایپ کنید.",
                    parse_mode="Markdown",
                ),
            ),
        ]
    else:
        # Quick AI response
        result_id = hashlib.md5(query.encode()).hexdigest()

        try:
            from arki_project.utils.v7_core import get_pipeline
            pipeline = get_pipeline()
            if pipeline and hasattr(pipeline, 'quick_classify'):
                classification = pipeline.quick_classify(query)
                category = classification.get('category', 'chat')
            else:
                category = 'chat'
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            category = 'chat'

        results = [
            InlineQueryResultArticle(
                id=result_id,
                title=f"🧠 پاسخ AI: {query[:50]}",
                description="کلیک کنید تا پاسخ ارسال شود",
                input_message_content=InputTextMessageContent(
                    message_text=f"🤖 *Arki AI*\n\n❓ {query}\n\n💡 برای پاسخ کامل، به چت خصوصی بات مراجعه کنید.",
                    parse_mode="Markdown",
                ),
            ),
            InlineQueryResultArticle(
                id=f"{result_id}_search",
                title=f"🔍 جستجو: {query[:50]}",
                description="جستجوی وب",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔍 *جستجوی Arki*\n\n{query}\n\n_برای نتایج کامل، به چت خصوصی بات مراجعه کنید._",
                    parse_mode="Markdown",
                ),
            ),

        ]

    await inline_query.answer(results, cache_time=30, is_personal=True)


