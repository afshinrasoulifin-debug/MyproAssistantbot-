
from __future__ import annotations
"""LLM evaluation and benchmarking commands."""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)
router = Router(name="eval_routes")


@router.message(Command("eval"))
async def cmd_eval(message: Message) -> None:
    """Start LLM evaluation benchmark."""
    await message.reply(
        "📊 *ارزیابی LLM*\n\n"
        "در حال آماده‌سازی بنچمارک...\n"
        "از `/eval auto` برای ارزیابی خودکار استفاده کنید.",
        parse_mode="Markdown"
    )


@router.message(Command("benchmark"))
async def cmd_benchmark(message: Message) -> None:
    """Run model performance benchmark."""
    await message.reply("⏱ بنچمارک شروع شد... نتایج به زودی ارسال می‌شود.")


