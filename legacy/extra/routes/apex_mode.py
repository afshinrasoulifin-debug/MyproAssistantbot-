
from __future__ import annotations
"""APEX activation and evaluation commands — v9.5."""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from arki_project.utils.safe_send import safe_reply

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)
router = Router(name="apex_mode")


@router.message(Command("apex"))
async def cmd_apex_mode(message: Message) -> None:
    """Activate APEX evaluation mode."""
    await safe_reply(message,
        "🔥 *APEX Mode Activated*\n\n"
        "حالت ارزیابی LLM فعال شد.\n"
        "دستورات:\n"
        "• `/eval` — شروع ارزیابی امنیتی مدل\n"
        "• `/eval <model>` — ارزیابی مدل خاص\n"
        "• `/models` — لیست مدل‌ها"
    )


@router.message(Command("eval"))
async def cmd_eval(message: Message) -> None:
    """Run APEX robustness evaluation on an AI model."""
    from arki_project.utils.apex_evaluator import APEXEvaluator

    # Parse model name from args
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    model = parts[1] if len(parts) > 1 else "gemini-2.5-pro"

    status = await message.answer("🔬 در حال ارزیابی امنیتی مدل `{}`...".format(model))

    try:
        evaluator = APEXEvaluator()
        report = await evaluator.evaluate_model(model)

        report_text = evaluator.format_report(report)

        # Delete status message
        try:
            await status.delete()
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

        await safe_reply(message, report_text)

    except Exception as e:
        logger.error("APEX evaluation failed: %s", e)
        await safe_reply(message, f"❌ خطا در ارزیابی: {e}")


