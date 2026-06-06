
"""agents_pkg.cmd_plan_group — sub-module of agents"""

from __future__ import annotations
from arki_project.exceptions import AgentExecutionError


import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone

import httpx
from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import *  # auto-fixed

__all__ = ['cmd_plan', 'start_monitor_bg', 'cmd_agent']

async def cmd_plan(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/plan")
    if not raw:
        await safe_reply(message, "📅 *برنامه‌ریز محتوا:*\n\n"
            "`/plan week شمع دکوری` — برنامه ۷ روزه\n"
            "`/plan month فروشگاه شمع` — برنامه ۳۰ روزه\n"
            "`/plan idea شمع معطر` — ۱۰ ایده خلاقانه")
        return

    parts = raw.split(maxsplit=1)
    mode = parts[0].lower()
    topic = parts[1] if len(parts) > 1 else "کسب‌وکار"

    prompts = {
        "week": (
            f"یک تقویم محتوایی ۷ روزه حرفه‌ای برای «{topic}» بنویس. "
            "هر روز شامل:\n"
            "📅 روز هفته | ⏰ بهترین ساعت پست\n"
            "📌 نوع محتوا (پست/ریلز/استوری/لایو)\n"
            "💡 موضوع و عنوان\n"
            "✍️ خلاصه کپشن (۲ خط)\n"
            "# هشتگ‌ها (۵ عدد)\n"
            "🎯 هدف (آگاهی/فروش/تعامل)\n\n"
            "فرمت تمیز و خوانا. فارسی."
        ),
        "month": (
            f"یک تقویم محتوایی ۳۰ روزه برای «{topic}» بنویس. "
            "هر هفته ۱ تم اصلی داشته باشه. "
            "هر روز: نوع محتوا + موضوع + هدف. "
            "فرمت جدولی فشرده. فارسی."
        ),
        "idea": (
            f"۱۵ ایده محتوایی خلاقانه و ترند برای «{topic}» بنویس. "
            "هر ایده شامل:\n"
            "💡 عنوان ایده\n"
            "📌 نوع (پست/ریلز/استوری/لایو)\n"
            "📝 توضیح اجرا (۳ خط)\n"
            "🎵 موسیقی/صدای پیشنهادی\n"
            "🎯 هدف + CTA\n"
            "فارسی + ایموجی."
        ),
    }

    if mode not in prompts:
        await safe_reply(message, "❌ `/plan week` یا `/plan month` یا `/plan idea`")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer("📅 دارم برنامه محتوا رو طراحی می‌کنم...")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "تو یک استراتژیست سوشال مدیا و تولید محتوای حرفه‌ای هستی. "
                    "خروجی‌ات باید عملی، دقیق و آماده اجرا باشه."},
                {"role": "user", "content": prompts[mode]},
            ],
            model_key=mk, temperature=0.8, max_tokens=65536,
        )

        try:
            await safe_delete(status)
        except AgentExecutionError as e:
            logger.debug("Suppressed: %s", e)
        mode_names = {"week": "هفتگی", "month": "ماهانه", "idea": "ایده‌ها"}
        header = f"📅 *برنامه {mode_names[mode]} — {topic}:*\n\n"

        for chunk in split_for_telegram(header + answer):
            try:
                await safe_reply(message, chunk)
            except AgentExecutionError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except AgentExecutionError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ════════════════════════════════════════



# ── Monitor auto-check background task ──

_monitor_bg_task: asyncio.Task | None = None


async def _monitor_auto_check(bot: "Bot", interval: int = 3600) -> None:
    """Background task: check all monitors every `interval` seconds."""

    while True:
        await asyncio.sleep(interval)
        try:
            async with get_session() as session:
                result = await session.execute(select(WebMonitor))
                monitors = result.scalars().all()

            if not monitors:
                continue

            for mon in monitors:
                try:
                    # v10.1: TITANIUM shielded check
                    if _TITANIUM_ACTIVE:
                        _ti = await shielded_get(mon.url, timeout=60.0, provider_name="web_monitor")
                        _resp_text = _ti.text
                    else:
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            _raw = await client.get(mon.url, follow_redirects=True)
                            _resp_text = _raw.text
                    new_hash = hashlib.md5(_resp_text.encode()).hexdigest()
                    new_size = len(_resp_text)

                    changed = new_hash != mon.last_hash

                    # Update DB
                    async with get_session() as session:
                        result2 = await session.execute(
                            select(WebMonitor).where(WebMonitor.id == mon.id)
                        )
                        db_mon = result2.scalar_one_or_none()
                        if db_mon:
                            db_mon.last_hash = new_hash
                            db_mon.last_size = new_size
                            db_mon.check_count += 1
                            await session.flush()

                    if changed:
                        size_diff = new_size - (mon.last_size or 0)
                        text = (
                            f"🔔 *تغییر در مانیتور #{mon.id}:*\n\n"
                            f"🏷 {mon.label}\n"
                            f"📏 {mon.last_size:,} → {new_size:,} ({size_diff:+,} bytes)\n"
                            f"🔗 {mon.url[:80]}"
                        )
                        try:
                            await bot.send_message(mon.chat_id, text, parse_mode="Markdown")
                        except AgentExecutionError as e:
                            logger.debug("Suppressed: %s", e)
                except AgentExecutionError as exc:
                    logger.warning("Monitor #%d check failed: %s", mon.id, exc)

        except AgentExecutionError as exc:
            logger.warning("Monitor auto-check failed: %s", exc)


async def start_monitor_bg(bot: "Bot") -> asyncio.Task:
    """Start the background monitor checker. Returns the task handle."""
    global _monitor_bg_task
    _monitor_bg_task = asyncio.create_task(_monitor_auto_check(bot))
    return _monitor_bg_task


# ═══════════ /agent — Autonomous Agent via agent_executor ═══════════

@router.message(Command("agent"))
async def cmd_agent(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Execute an autonomous agent that plans, uses tools, reflects, and answers."""
    query = extract_args(message.text or "", "/agent")
    if not query:
        await safe_reply(message, "🤖 *عامل هوشمند — Autonomous Agent*\n\n"
            "`/agent تحلیل رقبای فروش شمع`\n"
            "`/agent بهترین زمان پست اینستاگرام`\n\n"
            "_عامل هوشمند برنامه‌ریزی می‌کنه → ابزارها رو صدا می‌زنه → نتیجه رو تحلیل می‌کنه → "
            "بازتاب (self-reflection) انجام می‌ده._")
        return

    import os
    # v25.0 AUTONOMOUS: Resolve key from all sources
    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not or_key:
        try:
            from arki_project.utils.free_access_router import get_free_router
            _pk = get_free_router()._provisioned_keys.get("openrouter_free", [])
            or_key = _pk[0] if _pk else ""
        except AgentExecutionError:
            or_key = ""

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await safe_reply(message, "🤖 *Agent شروع شد...* (برنامه‌ریزی → اجرا → بازتاب)")

    try:
        import time as _t
        _t0 = _t.time()

        agent_mod = get_agent_executor()
        config = agent_mod.AgentConfig(
            api_key=or_key,
            model="google/gemini-2.5-pro",
            max_steps=6,
            max_time_s=120,
            temperature=0.3,
            enable_reflection=True,
            enable_caching=True,
        )

        # Pipeline classification for metadata
        _pipe_cat = None
        try:
            pipe = get_pipeline()
            pr = await pipe.process(user_id=message.from_user.id if message.from_user else 0, text=query)
            _pipe_cat = pr.category.value
        except AgentExecutionError as e:
            logger.debug("Suppressed: %s", e)

        trace = await agent_mod.execute_agent(
            query=query,
            messages=[],
            config=config,
        )

        await safe_delete(status)

        # Format output
        output = "🤖 *نتیجه عامل هوشمند:*\n\n"
        output += f"*سوال:* _{query}_\n"
        output += f"*وضعیت:* {'✅ موفق' if trace.success else '❌ ناموفق'}\n"
        output += f"*مراحل:* {len(trace.steps)}\n"
        if _pipe_cat:
            output += f"*دسته‌بندی:* {_pipe_cat}\n"
        output += "\n"

        # Show steps
        for step in trace.steps:
            emoji = "✅" if step.status_code == agent_mod.StepStatus.COMPLETED else "⏳" if step.status_code == agent_mod.StepStatus.RUNNING else "❌"
            if step.action:
                output += f"{emoji} *ابزار:* `{step.action.get('tool', '?')}` → {step.observation[:200] if step.observation else '—'}\n"
            elif step.thought:
                output += f"💭 {step.thought[:200]}\n"

        # Reflection
        if trace.reflection:
            output += f"\n🪞 *بازتاب:* {trace.reflection[:400]}\n"

        # Final answer
        if trace.final_answer:
            output += f"\n━━ *پاسخ نهایی* ━━\n{trace.final_answer}"

        _duration = _t.time() - _t0
        output += f"\n\n⏱ {_duration:.1f}s | 🪙 {trace.tokens_used} tokens"

        store_result(
            message.from_user.id if message.from_user else 0,
            query[:300], trace.final_answer[:500] if trace.final_answer else "", "agent",
            duration_s=_duration,
        )

        for chunk in split_for_telegram(output):
            try:
                await safe_reply(message, chunk)
            except AgentExecutionError:
                await message.answer(chunk)

    except AgentExecutionError as exc:
        logger.error("Agent failed: %s", exc, exc_info=True)
        try:
            await safe_delete(status)
        except AgentExecutionError as e:
            logger.debug("Suppressed: %s", e)
        await message.answer(user_friendly_error(exc))

