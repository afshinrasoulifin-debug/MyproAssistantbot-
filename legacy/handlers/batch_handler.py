
from __future__ import annotations
"""
from typing import Any
tg_bot/handlers/batch_handler.py — Batch AI Processing v2.0
════════════════════════════════════════════════════════════
Process multiple inputs through AI in one go: translate lists,
generate descriptions for multiple products, bulk summarize.

Commands:
  /batchai <mode> — Start batch processing
  /batchai translate fa en   — Batch translate
  /batchai describe          — Batch product descriptions
  /batchai caption           — Batch captions
  /batchai hashtag           — Batch hashtags
  /batchai review            — Batch text review
"""


import logging
import time

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.safe_send import safe_reply
from arki_project.handlers.shared import extract_args

try:
    from arki_project.utils.titanium.error_shield import sanitize_error as _ti_sanitize
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False

logger = logging.getLogger(__name__)
router = Router(name="batch_handler_v2")

# Active batch sessions
_batch_sessions: dict[int, dict] = {}

BATCH_MODES = {
    "translate": {
        "label": "🌐 ترجمه دسته‌ای",
        "prompt": "Translate each item below. Keep the numbering. Target language: {target}",
        "instruction": "هر خط = یک آیتم برای ترجمه. ارسال کنید:",
    },
    "describe": {
        "label": "📝 توضیح محصول",
        "prompt": "Write a compelling product description for each item. In Farsi. Keep numbering.",
        "instruction": "نام محصولات را بنویسید (هر خط یکی):",
    },
    "caption": {
        "label": "✍️ کپشن",
        "prompt": "Write an engaging Instagram caption for each item. Include emojis. In Farsi.",
        "instruction": "موضوعات پست را بنویسید (هر خط یکی):",
    },
    "hashtag": {
        "label": "#️⃣ هشتگ",
        "prompt": "Generate 10 relevant hashtags for each item. Mix Farsi and English.",
        "instruction": "موضوعات را بنویسید (هر خط یکی):",
    },
    "review": {
        "label": "📋 بررسی متن",
        "prompt": "Review each text for grammar, clarity, and tone. Suggest improvements. In Farsi.",
        "instruction": "متن‌ها را بنویسید (هر خط یکی):",
    },
    "seo": {
        "label": "🔍 عنوان SEO",
        "prompt": "Write SEO-optimized title and meta description for each item. In Farsi.",
        "instruction": "عنوان صفحات را بنویسید (هر خط یکی):",
    },
}


@router.message(Command("batchai"))
async def cmd_batchai(message: Message, ai_client: AIClient, settings: Settings) -> None:
    """Batch AI processing."""
    raw = extract_args(message.text or "", "/batchai")
    uid = message.from_user.id
    parts = raw.strip().split()

    if not parts:
        mode_list = "\n".join(f"  `{k}` — {v['label']}" for k, v in BATCH_MODES.items())
        await safe_reply(message,
            "🔄 *پردازش دسته‌ای AI*\n\n"
            f"*حالت‌ها:*\n{mode_list}\n\n"
            "*استفاده:*\n"
            "  `/batchai describe`\n"
            "  سپس لیست آیتم‌ها را ارسال کنید (هر خط یکی)\n\n"
            "*یا مستقیم:*\n"
            "  `/batchai describe\nمحصول ۱\nمحصول ۲\nمحصول ۳`"
        )
        return

    mode = parts[0].lower()
    if mode not in BATCH_MODES:
        await safe_reply(message, f"⚠️ حالت `{mode}` نامعتبر. `/batchai` را ببینید.")
        return

    mode_info = BATCH_MODES[mode]
    remaining = " ".join(parts[1:])

    # Check if items are provided inline (after mode name)
    items_text = ""
    if "\n" in raw:
        # Items are on subsequent lines
        lines = raw.split("\n")[1:]
        items_text = "\n".join(l.strip() for l in lines if l.strip())
    elif remaining and not remaining.split()[0] in BATCH_MODES:
        items_text = remaining

    if not items_text:
        # Start a batch session — wait for next message
        _batch_sessions[uid] = {"mode": mode, "ts": time.time()}
        await safe_reply(message,
            f"{mode_info['label']}\n\n"
            f"{mode_info['instruction']}\n\n"
            "_(هر خط = یک آیتم)_"
        )
        return

    # Process items now
    await _process_batch(message, ai_client, mode, items_text)


async def _process_batch(message: Message, ai_client: AIClient, mode: str, items_text: str) -> Any:
    """Process a batch of items."""
    mode_info = BATCH_MODES[mode]
    items = [l.strip() for l in items_text.split("\n") if l.strip()]

    if not items:
        await safe_reply(message, "⚠️ آیتمی یافت نشد.")
        return

    if len(items) > 50:
        await safe_reply(message, "⚠️ حداکثر ۵۰ آیتم. لطفاً تقسیم کنید.")
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    # Build numbered list
    numbered = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    prompt = f"{mode_info['prompt']}\n\nItems:\n{numbered}"

    start = time.time()
    try:
        result = await ai_client.ask(
            user_id=message.from_user.id,
            text=prompt,
            system_prompt=(
                "You are a professional content creator. Process each item separately. "
                "Keep the numbering. Be concise but thorough. Respond in Farsi unless "
                "the task requires another language."
            ),
            temperature=0.7,
            max_tokens=8192,
        )

        elapsed = time.time() - start
        header = (
            f"{mode_info['label']} — {len(items)} آیتم\n"
            f"⏱ {elapsed:.1f}s\n\n"
        )

        full_result = header + (result or "—")

        # If result is too long, send as file
        if len(full_result) > 4000:
            doc = BufferedInputFile(
                full_result.encode("utf-8"),
                filename=f"batch_{mode}_{int(time.time())}.txt",
            )
            await message.answer_document(doc, caption=f"{mode_info['label']} — {len(items)} آیتم ✅")
        else:
            await safe_reply(message, full_result)

    except Exception as e:
        logger.error("Batch processing error: %s", e)
        err = _ti_sanitize(str(e)) if _TITANIUM_ACTIVE else str(e)
        await safe_reply(message, f"⚠️ خطا: {err}")


@router.callback_query(F.data.startswith("batch:"))
async def cb_batch(callback: CallbackQuery) -> Any:
    """Handle batch callbacks."""
    await callback.answer("✅")


