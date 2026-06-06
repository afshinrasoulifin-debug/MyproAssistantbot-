
from __future__ import annotations
"""
tg_bot/handlers/agents.py
─────────────────────────
🧠 Advanced AI Agents — real automation that actually saves time:

  /workflow    — Multi-step AI pipeline (photo→description→caption→hashtags)
  /crm        — Mini CRM: customers, orders, follow-ups
  /finance    — Income/expense tracker with reports
  /monitor    — Web page change monitor (price drops, stock)
  /autoreply  — Keyword-triggered auto-responses
  /plan       — AI content calendar generator
  /agents     — Agent hub menu
"""


import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone

import httpx
from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════
from sqlalchemy import delete, func, select

from arki_project.config import Settings
from arki_project.database.connection import get_session
from arki_project.database.models import (
    AutoReply,
    Customer,
    FinanceRecord,
    WebMonitor,
)
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args
from arki_project.autonomous_core.thinking_agent import ThinkingAgentPro
from arki_project.utils.v7_core import (
    enhance_system_prompt, store_result, get_agent_executor,
    get_pipeline,
)

logger = logging.getLogger(__name__)
# v9.2: Task queue for heavy operations

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

router = Router(name="agents")


# ════════════════════════════════════════
# /agents — Agent Hub Menu
# ════════════════════════════════════════

def _agents_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧠 Workflow", callback_data="ag:workflow"),
            InlineKeyboardButton(text="👥 CRM", callback_data="ag:crm"),
        ],
        [
            InlineKeyboardButton(text="💰 مالی", callback_data="ag:finance"),
            InlineKeyboardButton(text="🕷 مانیتور", callback_data="ag:monitor"),
        ],
        [
            InlineKeyboardButton(text="⚡ پاسخ‌گوی خودکار", callback_data="ag:autoreply"),
            InlineKeyboardButton(text="📅 برنامه محتوا", callback_data="ag:plan"),
        ],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="menu:back")],
    ])


@router.message(Command("agents"))
async def cmd_agents(message: Message) -> None:
    await safe_reply(message, "🧠 *ایجنت‌های هوشمند — اتوماسیون واقعی:*\n\n"
        "🔄 `/workflow` — پایپلاین چند مرحله‌ای AI\n"
        "  _عکس محصول → توضیح → کپشن → هشتگ → برنامه پست_\n\n"
        "👥 `/crm` — مدیریت مشتری (Mini CRM)\n"
        "  _ثبت مشتری، سفارش، پیگیری، یادآوری_\n\n"
        "💰 `/finance` — حسابداری ساده\n"
        "  _درآمد/هزینه، دسته‌بندی، گزارش ماهانه_\n\n"
        "🕷 `/monitor` — مانیتور تغییرات وب\n"
        "  _قیمت، موجودی، رقبا — اطلاع‌رسانی خودکار_\n\n"
        "⚡ `/autoreply` — پاسخ‌گوی خودکار\n"
        "  _جواب اتوماتیک بر اساس کلمات کلیدی_\n\n"
        "📅 `/plan` — برنامه‌ریز محتوا\n"
        "  _تقویم محتوایی هفتگی/ماهانه AI_\n\n"
        "یکی رو انتخاب کن:",
        reply_markup=_agents_menu_kb())


@router.callback_query(F.data.startswith("ag:"))
async def cb_agent_help(callback: CallbackQuery) -> None:
    await callback.answer()
    action = callback.data.split(":")[1]  # type: ignore[union-attr]

    # ── "back to menu" button ──
    if action == "menu":
        await safe_edit_text(callback.message,  # type: ignore[union-attr]
            "🧠 *ایجنت‌های هوشمند:*\nیکی رو انتخاب کن:",
            reply_markup=_agents_menu_kb())
        return

    helps = {
        "workflow": (
            "🔄 *Workflow Agent:*\n\n"
            "`/workflow [توضیح محصول یا موضوع]`\n\n"
            "AI یک پایپلاین کامل اجرا می‌کنه:\n"
            "1️⃣ توضیح حرفه‌ای محصول\n"
            "2️⃣ ۳ کپشن اینستاگرام\n"
            "3️⃣ ۳۰ هشتگ هدفمند\n"
            "4️⃣ برنامه پست ۷ روزه\n"
            "5️⃣ ایده استوری + ریلز\n\n"
            "_همه در یک دستور!_"
        ),
        "crm": (
            "👥 *Mini CRM:*\n\n"
            "`/crm add علی | 09121234567 | مشتری VIP`\n"
            "`/crm list` — لیست مشتریان\n"
            "`/crm order 1 | شمع معطر x3 | 450000`\n"
            "`/crm orders 1` — سفارشات مشتری\n"
            "`/crm search علی` — جستجو\n"
            "`/crm stats` — آمار کلی\n"
            "`/crm del 1` — حذف"
        ),
        "finance": (
            "💰 *حسابداری:*\n\n"
            "`/finance + 500000 فروش شمع`\n"
            "`/finance - 120000 خرید مواد اولیه`\n"
            "`/finance report` — گزارش ماهانه\n"
            "`/finance list` — آخرین تراکنش‌ها\n"
            "`/finance balance` — موجودی"
        ),
        "monitor": (
            "🕷 *مانیتور وب:*\n\n"
            "`/monitor add https://example.com`\n"
            "`/monitor list` — لیست\n"
            "`/monitor check` — بررسی الان\n"
            "`/monitor del 1` — حذف\n\n"
            "_هر ۳۰ دقیقه چک می‌کنه و تغییرات رو خبر می‌ده_"
        ),
        "autoreply": (
            "⚡ *پاسخ‌گوی خودکار:*\n\n"
            "`/autoreply add قیمت | لیست قیمت‌ها: ...`\n"
            "`/autoreply add سلام | سلام! چطور می‌تونم کمکت کنم؟`\n"
            "`/autoreply list` — لیست قوانین\n"
            "`/autoreply del 1` — حذف\n"
            "`/autoreply on` / `/autoreply off`"
        ),
        "plan": (
            "📅 *برنامه محتوا:*\n\n"
            "`/plan week شمع دکوری`\n"
            "  _تقویم محتوایی ۷ روزه_\n\n"
            "`/plan month فروشگاه شمع`\n"
            "  _برنامه محتوایی ۳۰ روزه_\n\n"
            "`/plan idea شمع معطر`\n"
            "  _۱۰ ایده محتوایی خلاقانه_"
        ),
    }
    text = helps.get(action, "")
    if text:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 منوی ایجنت‌ها", callback_data="ag:menu")],
        ])
        await safe_edit_text(callback.message, # type: ignore[union-attr]
            text, reply_markup=back_kb)


@router.message(Command("workflow"))
async def cmd_workflow(
    message: Message, ai_client: AIClient, settings: Settings,
) -> Any:
    topic = extract_args(message.text or "", "/workflow")
    if not topic:
        await safe_reply(message, "🔄 *Workflow Agent — پایپلاین هوشمند:*\n\n"
            "`/workflow شمع دکوری معطر لاکچری`\n"
            "`/workflow تخفیف ویژه یلدا`\n"
            "`/workflow محصول جدید شمع سویا`\n\n"
            "_AI یک پایپلاین ۵ مرحله‌ای اجرا می‌کنه:_\n"
            "1️⃣ توضیح حرفه‌ای\n"
            "2️⃣ ۳ کپشن\n"
            "3️⃣ ۳۰ هشتگ\n"
            "4️⃣ برنامه ۷ روزه\n"
            "5️⃣ ایده استوری + ریلز")
        return

    # 1. Prepare steps for ThinkingAgentPro
    workflow_steps = ["تحلیل اولیه", "تولید توضیح محصول", "کپشن‌نویسی", "هشتگ + برنامه + ایده (موازی)"]
    
    # 2. Initial status message
    status = await safe_reply(message, "🧠 *ایجنت در حال آماده‌سازی...*")
    if not status: return

    async with ThinkingAgentPro(
        bot=message.bot, chat_id=message.chat.id, initial_message=status, total_steps=len(workflow_steps)
    ) as agent:
        await agent.set_total_steps(len(workflow_steps), workflow_steps)
        
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
        results: list[str] = []

        # ── Step 0: Initial Analysis ──
        await agent.start_step(0)
        await agent.update_thought(f"تحلیل موضوع: {topic}", active_model=mk)
        await agent.complete_step(0)

        # ── Step 1: Product description ──
        await agent.start_step(1)
        desc = ""
        try:
            import time as _t; _t0 = _t.time()
            desc = await agent.execute_with_resilience(
                func=ai_client.ask_raw,
                user_id=message.from_user.id if message.from_user else 0,
                messages=[
                    {"role": "system", "content": enhance_system_prompt(
                        "تو کپی‌رایتر حرفه‌ای هستی. یک توضیح محصول جذاب و حرفه‌ای بنویس "
                        "که شامل ویژگی‌ها، مزایا و احساسی که ایجاد می‌کنه باشه. "
                        "۳-۴ پاراگراف. فارسی. با ایموجی مناسب.",
                        user_text=topic, user_id=str(message.from_user.id) if message.from_user else "0")},
                    {"role": "user", "content": f"محصول: {topic}"},
                ],
                model_key=mk, temperature=0.8, max_tokens=65536,
                thinking_agent=agent,
                step_index=1,
            )
            store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:300], desc[:500] if desc else "", "agents", duration_s=_t.time()-_t0)
            results.append(f"📋 *مرحله ۱ — توضیح محصول:*\n\n{desc}")
            await agent.complete_step(1)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await agent.log_self_correction(f"خطا در مرحله ۱: {exc}")
            results.append(f"❌ مرحله ۱ خطا: {exc}")
            await agent.complete_step(1, success=False)

        # ── Step 2: Captions ──
        await agent.start_step(2)
        try:
            captions = await agent.execute_with_resilience(
                func=ai_client.ask_raw,
                user_id=message.from_user.id if message.from_user else 0,
                messages=[
                    {"role": "system", "content":
                        "تو کپشن‌نویس حرفه‌ای اینستاگرام هستی. "
                        "۳ کپشن بنویس: ۱) کوتاه و ضربه‌ای ۲) متوسط با داستان ۳) بلند و آموزشی. "
                        "هر کدوم CTA (دعوت به عمل) داشته باشه. فارسی + ایموجی."},
                    {"role": "user", "content": f"محصول: {topic}\n\nتوضیح: {desc[:300]}"},
                ],
                model_key=mk, temperature=0.9, max_tokens=65536,
                thinking_agent=agent,
                step_index=2,
            )
            results.append(f"✍️ *مرحله ۲ — ۳ کپشن:*\n\n{captions}")
            await agent.complete_step(2)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await agent.log_self_correction(f"خطا در مرحله ۲: {exc}")
            results.append(f"❌ مرحله ۲ خطا: {exc}")
            await agent.complete_step(2, success=False)

        # ── Steps 3: Parallel (independent of each other) ──
        await agent.start_step(3)
        
        async def _step3_hashtags() -> str:
            return await agent.execute_with_resilience(
                func=ai_client.ask_raw,
                user_id=message.from_user.id if message.from_user else 0,
                messages=[
                    {"role": "system", "content":
                        "تو متخصص هشتگ اینستاگرام هستی. "
                        "۳۰ هشتگ در ۳ گروه تولید کن:\n"
                        "🔥 محبوب (ترافیک بالا) — ۱۰ عدد\n"
                        "🎯 متوسط (رقابت کمتر) — ۱۰ عدد\n"
                        "💎 نیچ (خاص و هدفمند) — ۱۰ عدد\n"
                        "فارسی + انگلیسی. آخر یک بلوک کپی‌پیست آماده بذار."},
                    {"role": "user", "content": f"محصول: {topic}"},
                ],
                model_key=mk, temperature=0.8, max_tokens=65536,
                thinking_agent=agent,
                step_index=3,
                step_name="هشتگ‌سازی",
            )

        async def _step4_plan() -> str:
            return await agent.execute_with_resilience(
                func=ai_client.ask_raw,
                user_id=message.from_user.id if message.from_user else 0,
                messages=[
                    {"role": "system", "content":
                        "تو استراتژیست سوشال مدیا هستی. "
                        "یک برنامه پست ۷ روزه بنویس. هر روز شامل:\n"
                        "📅 روز | 🕐 بهترین ساعت | 📝 نوع پست (پست/ریلز/استوری) | "
                        "💡 موضوع | ✍️ خلاصه کپشن\n"
                        "فرمت جدولی. فارسی."},
                    {"role": "user", "content": f"محصول: {topic}"},
                ],
                model_key=mk, temperature=0.7, max_tokens=65536,
                thinking_agent=agent,
                step_index=3,
                step_name="برنامه‌ریزی محتوا",
            )

        async def _step5_ideas() -> str:
            return await agent.execute_with_resilience(
                func=ai_client.ask_raw,
                user_id=message.from_user.id if message.from_user else 0,
                messages=[
                    {"role": "system", "content":
                        "تو ایده‌پرداز خلاق سوشال مدیا هستی. "
                        "۵ ایده استوری اینتراکتیو و ۵ ایده ریلز/ویدیو کوتاه بنویس. "
                        "هر ایده شامل: عنوان، توضیح اجرا، موسیقی پیشنهادی، و CTA. "
                        "فارسی + ایموجی."},
                    {"role": "user", "content": f"محصول: {topic}"},
                ],
                model_key=mk, temperature=0.9, max_tokens=65536,
                thinking_agent=agent,
                step_index=3,
                step_name="ایده‌پردازی استوری/ریلز",
            )

        # Run steps 3-5 in parallel
        s3, s4, s5 = await asyncio.gather(
            _step3_hashtags(), _step4_plan(), _step5_ideas(),
            return_exceptions=True,
        )

        if isinstance(s3, Exception):
            results.append(f"❌ مرحله ۳ خطا: {s3}")
        else:
            results.append(f"#️⃣ *مرحله ۳ — ۳۰ هشتگ:*\n\n{s3}")

        if isinstance(s4, Exception):
            results.append(f"❌ مرحله ۴ خطا: {s4}")
        else:
            results.append(f"📅 *مرحله ۴ — برنامه ۷ روزه:*\n\n{s4}")

        if isinstance(s5, Exception):
            results.append(f"❌ مرحله ۵ خطا: {s5}")
        else:
            results.append(f"💡 *مرحله ۵ — ایده استوری + ریلز:*\n\n{s5}")

        await agent.complete_step(3)

        # ── Send all results ──
        await agent.end_thinking(f"🔄 *Workflow کامل شد!* — `{topic}`\n━━━━━━━━━━━━━━━━━━━")

    for result in results:
        for chunk in split_for_telegram(result):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
        await asyncio.sleep(0.3)


# ════════════════════════════════════════
# 2. /crm — Mini Customer Manager
# ════════════════════════════════════════

@router.message(Command("crm_legacy_disabled"))  # Moved to sales_brain.py
async def cmd_crm(message: Message) -> None:
    raw = extract_args(message.text or "", "/crm")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw or raw == "help":
        await safe_reply(message, "👥 *Mini CRM — مدیریت مشتری:*\n\n"
            "`/crm add نام | شماره | توضیح`\n"
            "`/crm list` — لیست مشتریان\n"
            "`/crm search نام` — جستجو\n"
            "`/crm show 1` — جزئیات\n"
            "`/crm order 1 | شمع x3 | 450000` — ثبت سفارش\n"
            "`/crm orders 1` — سفارشات مشتری\n"
            "`/crm tag 1 | VIP` — تگ\n"
            "`/crm stats` — آمار کلی\n"
            "`/crm del 1` — حذف")
        return

    cmd = raw.split(maxsplit=1)
    action = cmd[0].lower()
    rest = cmd[1] if len(cmd) > 1 else ""

    # ── add ──
    if action == "add":
        parts = [p.strip() for p in rest.split("|")]
        if len(parts) < 1 or not parts[0]:
            await safe_reply(message, "❌ `/crm add نام | شماره | توضیح`")
            return
        name = parts[0]
        phone = parts[1] if len(parts) > 1 else ""
        note = parts[2] if len(parts) > 2 else ""

        async with get_session() as session:
            cust = Customer(
                owner_id=user_id, name=name, phone=phone,
                note=note, tags="",
            )
            session.add(cust)
            await session.flush()
            cid = cust.id

        await safe_reply(message, f"✅ مشتری #{cid} اضافه شد!\n\n"
            f"👤 *{name}*\n"
            f"📞 {phone}\n"
            f"📝 {note}")
        return

    # ── list ──
    if action in ("list", "لیست"):
        async with get_session() as session:
            result = await session.execute(
                select(Customer)
                .where(Customer.owner_id == user_id)
                .order_by(Customer.created_at.desc())
                .limit(20),
            )
            custs = result.scalars().all()

        if not custs:
            await safe_reply(message, "👥 هنوز مشتری‌ای ثبت نشده.\n`/crm add نام | شماره`")
            return

        text = "👥 *مشتریان:*\n\n"
        for c in custs:
            tag_icon = " 🏷" + c.tags if c.tags else ""
            orders = f" | 📦{c.total_orders}" if c.total_orders else ""
            revenue = f" | 💰{c.total_spent:,.0f}" if c.total_spent else ""
            text += f"*{c.id}.* {c.name} — {c.phone}{tag_icon}{orders}{revenue}\n"
        await safe_reply(message, text)
        return

    # ── search ──
    if action in ("search", "جستجو"):
        if not rest:
            await safe_reply(message, "❌ `/crm search نام`")
            return
        async with get_session() as session:
            result = await session.execute(
                select(Customer)
                .where(
                    Customer.owner_id == user_id,
                    Customer.name.ilike(f"%{rest}%"),
                )
                .limit(10),
            )
            custs = result.scalars().all()
        if not custs:
            await message.answer(f"❌ «{rest}» پیدا نشد.")
            return
        text = f"🔍 *نتایج «{rest}»:*\n\n"
        for c in custs:
            text += f"*{c.id}.* {c.name} — {c.phone}\n"
        await safe_reply(message, text)
        return

    # ── show ──
    if action in ("show", "نمایش"):
        try:
            cid = int(rest)
        except ValueError:
            await safe_reply(message, "❌ `/crm show [شماره]`")
            return
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id,
                ),
            )
            c = result.scalar_one_or_none()
        if not c:
            await message.answer("❌ مشتری پیدا نشد.")
            return
        dt = c.created_at.strftime("%Y-%m-%d") if c.created_at else ""
        await safe_reply(message, f"👤 *{c.name}* (#{c.id})\n\n"
            f"📞 شماره: {c.phone or '—'}\n"
            f"📝 توضیح: {c.note or '—'}\n"
            f"🏷 تگ: {c.tags or '—'}\n"
            f"📦 سفارشات: {c.total_orders}\n"
            f"💰 مجموع خرید: {c.total_spent:,.0f} تومان\n"
            f"📅 ثبت: {dt}")
        return

    # ── order ──
    if action in ("order", "سفارش"):
        parts = [p.strip() for p in rest.split("|")]
        if len(parts) < 2:
            await safe_reply(message, "❌ `/crm order [شماره مشتری] | [شرح] | [مبلغ]`")
            return
        try:
            cid = int(parts[0])
        except ValueError:
            await safe_reply(message, "❌ شماره مشتری نامعتبر")
            return
        desc = parts[1]
        amount = 0
        if len(parts) > 2:
            try:
                amount = int(parts[2].replace(",", "").replace(".", ""))
            except ValueError as _exc:
                logger.debug("Suppressed: %s", _exc)

        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id,
                ),
            )
            c = result.scalar_one_or_none()
            if not c:
                await message.answer("❌ مشتری پیدا نشد.")
                return
            c.total_orders += 1
            c.total_spent += amount
            order_log = f"\n📦 {datetime.now(timezone.utc).strftime('%m-%d')} | {desc} | {amount:,}"
            c.note = (c.note or "") + order_log
            await session.flush()

        await safe_reply(message, "✅ سفارش ثبت شد!\n\n"
            f"👤 {c.name} | 📦 {desc}\n"
            f"💰 {amount:,} تومان\n"
            f"📊 مجموع سفارشات: {c.total_orders} | مجموع: {c.total_spent:,}")
        return

    # ── orders ──
    if action in ("orders", "سفارشات"):
        try:
            cid = int(rest)
        except ValueError:
            await safe_reply(message, "❌ `/crm orders [شماره]`")
            return
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id,
                ),
            )
            c = result.scalar_one_or_none()
        if not c:
            await message.answer("❌ مشتری پیدا نشد.")
            return
        # Extract order lines from note.
        orders = [l for l in (c.note or "").split("\n") if l.strip().startswith("📦")]
        if not orders:
            await message.answer(f"👤 *{c.name}* — هنوز سفارشی ثبت نشده.")
            return
        text = f"📦 *سفارشات {c.name}:*\n\n" + "\n".join(orders[-20:])
        text += f"\n\n📊 مجموع: {c.total_orders} سفارش | {c.total_spent:,} تومان"
        await safe_reply(message, text)
        return

    # ── tag ──
    if action in ("tag", "تگ"):
        parts = [p.strip() for p in rest.split("|")]
        if len(parts) < 2:
            await safe_reply(message, "❌ `/crm tag [شماره] | [تگ]`")
            return
        try:
            cid = int(parts[0])
        except ValueError:
            await message.answer("❌ شماره نامعتبر")
            return
        tag = parts[1]
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id,
                ),
            )
            c = result.scalar_one_or_none()
            if not c:
                await message.answer("❌ مشتری پیدا نشد.")
                return
            c.tags = tag
            await session.flush()
        await message.answer(f"✅ تگ «{tag}» برای {c.name} ست شد.")
        return

    # ── stats ──
    if action in ("stats", "آمار"):
        async with get_session() as session:
            result = await session.execute(
                select(
                    func.count(Customer.id),
                    func.sum(Customer.total_orders),
                    func.sum(Customer.total_spent),
                ).where(Customer.owner_id == user_id),
            )
            row = result.one()
        total_cust = row[0] or 0
        total_orders = row[1] or 0
        total_revenue = row[2] or 0
        await safe_reply(message, "📊 *آمار CRM:*\n\n"
            f"👥 مشتریان: *{total_cust}*\n"
            f"📦 کل سفارشات: *{total_orders}*\n"
            f"💰 کل فروش: *{total_revenue:,.0f}* تومان")
        return

    # ── del ──
    if action in ("del", "حذف"):
        try:
            cid = int(rest)
        except ValueError:
            await safe_reply(message, "❌ `/crm del [شماره]`")
            return
        async with get_session() as session:
            await session.execute(
                delete(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id,
                ),
            )
        await message.answer(f"✅ مشتری #{cid} حذف شد.")
        return

    await safe_reply(message, "❌ دستور نامعتبر. `/crm` رو بزن برای راهنما.")


# ════════════════════════════════════════
# 3. /finance — Income/Expense Tracker
# ════════════════════════════════════════

@router.message(Command("finance"))
async def cmd_finance(message: Message) -> None:
    raw = extract_args(message.text or "", "/finance")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw:
        await safe_reply(message, "💰 *حسابداری ساده:*\n\n"
            "`/finance + 500000 فروش شمع`\n"
            "`/finance - 120000 خرید موم`\n"
            "`/finance report` — گزارش ماهانه\n"
            "`/finance list` — آخرین تراکنش‌ها\n"
            "`/finance balance` — موجودی\n"
            "`/finance del 1` — حذف")
        return

    # ── income/expense ──
    income_match = re.match(r"^\+\s*(\d[\d,]*)\s*(.*)", raw)
    expense_match = re.match(r"^-\s*(\d[\d,]*)\s*(.*)", raw)

    if income_match or expense_match:
        is_income = bool(income_match)
        m = income_match or expense_match
        amount = int(m.group(1).replace(",", ""))  # type: ignore[union-attr]
        desc = m.group(2).strip() or ("درآمد" if is_income else "هزینه")  # type: ignore[union-attr]

        async with get_session() as session:
            rec = FinanceRecord(
                user_id=user_id,
                amount=amount if is_income else -amount,
                category=desc,
                description=desc,
            )
            session.add(rec)
            await session.flush()
            rid = rec.id

        icon = "📈" if is_income else "📉"
        color = "+" if is_income else "-"
        await safe_reply(message, f"{icon} *ثبت شد!* (#{rid})\n\n"
            f"💰 {color}{amount:,} تومان\n"
            f"📝 {desc}")
        return

    cmd = raw.split(maxsplit=1)
    action = cmd[0].lower()

    # ── balance ──
    if action in ("balance", "موجودی"):
        async with get_session() as session:
            result = await session.execute(
                select(func.sum(FinanceRecord.amount))
                .where(FinanceRecord.user_id == user_id),
            )
            total = result.scalar() or 0

            # This month.
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            result2 = await session.execute(
                select(
                    func.sum(func.max(FinanceRecord.amount, 0)),
                    func.sum(func.min(FinanceRecord.amount, 0)),
                ).where(
                    FinanceRecord.user_id == user_id,
                    FinanceRecord.created_at >= month_start,
                ),
            )
            row = result2.one()
        month_income = row[0] or 0
        month_expense = row[1] or 0

        await safe_reply(message, "💰 *موجودی:*\n\n"
            f"📊 کل: *{total:,.0f}* تومان\n\n"
            "📅 این ماه:\n"
            f"  📈 درآمد: +{month_income:,.0f}\n"
            f"  📉 هزینه: {month_expense:,.0f}\n"
            f"  📊 خالص: {month_income + month_expense:,.0f}")
        return

    # ── list ──
    if action in ("list", "لیست"):
        async with get_session() as session:
            result = await session.execute(
                select(FinanceRecord)
                .where(FinanceRecord.user_id == user_id)
                .order_by(FinanceRecord.created_at.desc())
                .limit(15),
            )
            records = result.scalars().all()

        if not records:
            await message.answer("💰 هنوز تراکنشی ثبت نشده.")
            return

        text = "💰 *آخرین تراکنش‌ها:*\n\n"
        for r in records:
            icon = "📈" if r.amount >= 0 else "📉"
            dt = r.created_at.strftime("%m-%d") if r.created_at else ""
            text += f"{icon} *{r.id}.* {r.amount:+,.0f} | {r.category} _{dt}_\n"
        await safe_reply(message, text)
        return

    # ── report ──
    if action in ("report", "گزارش"):
        steps = ["اتصال به دیتابیس", "تحلیل تراکنش‌ها", "محاسبه نهایی"]
        status = await safe_reply(message, "🧠 *در حال تهیه گزارش...*")
        if not status: return

        async with ThinkingAgentPro(bot=message.bot, chat_id=message.chat.id, initial_message=status, total_steps=len(steps)) as agent:
            await agent.set_total_steps(len(steps), steps)
            
            # Step 1: DB Access
            await agent.start_step(0)
            async with get_session() as session:
                now = datetime.now(timezone.utc)
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                result = await session.execute(
                    select(FinanceRecord)
                    .where(
                        FinanceRecord.user_id == user_id,
                        FinanceRecord.created_at >= month_start,
                    )
                    .order_by(FinanceRecord.created_at),
                )
                records = result.scalars().all()
            await agent.complete_step(0)

            if not records:
                await agent.end_thinking("📊 این ماه تراکنشی نداری.", success=False)
                return

            # Step 2: Analysis
            await agent.start_step(1)
            income = sum(r.amount for r in records if r.amount > 0)
            expense = sum(r.amount for r in records if r.amount < 0)

            # Category breakdown.
            cats: dict[str, int] = {}
            for r in records:
                cats[r.category] = cats.get(r.category, 0) + r.amount
            await agent.complete_step(1)

            # Step 3: Final Output
            await agent.start_step(2)
            text = (
                f"📊 *گزارش ماهانه ({now.strftime('%Y-%m')}):*\n\n"
                f"📈 درآمد: *+{income:,.0f}*\n"
                f"📉 هزینه: *{expense:,.0f}*\n"
                f"📊 سود خالص: *{income + expense:,.0f}*\n"
                f"📝 تعداد تراکنش: *{len(records)}*\n\n"
                "*دسته‌بندی:*\n"
            )
            for cat, amt in cats.items():
                icon = "➕" if amt > 0 else "➖"
                text += f"{icon} {cat}: {amt:,.0f}\n"
            await agent.end_thinking(text)
        return

    # ── del ──
    if action in ("del", "حذف"):
        rest = cmd[1] if len(cmd) > 1 else ""
        try:
            rid = int(rest)
        except ValueError:
            await safe_reply(message, "❌ `/finance del [شماره]`")
            return
        async with get_session() as session:
            await session.execute(
                delete(FinanceRecord).where(
                    FinanceRecord.id == rid, FinanceRecord.user_id == user_id,
                ),
            )
        await message.answer(f"✅ تراکنش #{rid} حذف شد.")
        return

    await safe_reply(message, "❌ دستور نامعتبر. `/finance` بزن.")

_monitor_tasks: dict[int, asyncio.Task] = {}


@router.message(Command("monitor"))
async def cmd_monitor(message: Message) -> None:
    raw = extract_args(message.text or "", "/monitor")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw:
        await safe_reply(message, "🕷 *مانیتور وب — رصد تغییرات:*\n\n"
            "`/monitor add https://example.com/product`\n"
            "`/monitor list` — لیست مانیتورها\n"
            "`/monitor check` — بررسی الان\n"
            "`/monitor del 1` — حذف\n\n"
            "_صفحات رو رصد می‌کنه و تغییرات رو خبر می‌ده_")
        return

    cmd = raw.split(maxsplit=1)
    action = cmd[0].lower()
    rest = cmd[1] if len(cmd) > 1 else ""

    # ── add ──
    if action == "add" and rest.startswith("http"):
        url = rest.split()[0]
        label = " ".join(rest.split()[1:]) or url[:50]

        # Fetch initial snapshot.
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                _resp = await shielded_get(url, timeout=60.0, provider_name="web_monitor")
                initial_hash = hashlib.md5(_resp.text.encode()).hexdigest()
                content_len = len(_resp.text)
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    _raw = await client.get(url, follow_redirects=True)
                initial_hash = hashlib.md5(_raw.text.encode()).hexdigest()
                content_len = len(_raw.text)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(f"❌ دسترسی به URL ممکن نیست: {exc}")
            return

        async with get_session() as session:
            mon = WebMonitor(
                user_id=user_id,
                chat_id=message.chat.id,
                url=url,
                label=label,
                last_hash=initial_hash,
                last_size=content_len,
            )
            session.add(mon)
            await session.flush()
            mid = mon.id

        await safe_reply(message, f"✅ مانیتور #{mid} فعال شد!\n\n"
            f"🔗 {url}\n"
            f"📏 سایز: {content_len:,} bytes\n"
            f"🔑 Hash: `{initial_hash[:12]}...`\n\n"
            "_هر بار `/monitor check` بزنی چک می‌شه_")
        return

    # ── list ──
    if action in ("list", "لیست"):
        async with get_session() as session:
            result = await session.execute(
                select(WebMonitor)
                .where(WebMonitor.user_id == user_id)
                .order_by(WebMonitor.created_at.desc()),
            )
            monitors = result.scalars().all()

        if not monitors:
            await safe_reply(message, "🕷 مانیتوری نداری.\n`/monitor add https://...`")
            return

        text = "🕷 *مانیتورهای فعال:*\n\n"
        for m in monitors:
            dt = m.last_checked.strftime("%m-%d %H:%M") if m.last_checked else "—"
            text += f"*{m.id}.* {m.label}\n  🔗 `{m.url[:60]}`\n  📅 آخرین: {dt}\n\n"
        await safe_reply(message, text)
        return

    # ── check ──
    if action in ("check", "بررسی"):
        async with get_session() as session:
            result = await session.execute(
                select(WebMonitor).where(WebMonitor.user_id == user_id),
            )
            monitors = result.scalars().all()

        if not monitors:
            await message.answer("🕷 مانیتوری نداری.")
            return

        status_msg = await message.answer(f"🕷 بررسی {len(monitors)} سایت...")
        changes = []

        for mon in monitors:
            try:
                # v10.1: TITANIUM shielded check
                if _TITANIUM_ACTIVE:
                    _ti = await shielded_get(mon.url, timeout=60.0, provider_name="web_monitor")
                    resp_text = _ti.text
                else:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        _raw = await client.get(mon.url, follow_redirects=True)
                        resp_text = _raw.text
                new_hash = hashlib.md5(resp_text.encode()).hexdigest()
                new_size = len(resp_text)

                if new_hash != mon.last_hash:
                    size_diff = new_size - (mon.last_size or 0)
                    changes.append(
                        f"🔔 *{mon.label}* (#{mon.id})\n"
                        f"  📏 سایز: {mon.last_size:,} → {new_size:,} ({size_diff:+,})\n"
                        f"  🔗 {mon.url[:60]}"
                    )

                # Update in DB.
                async with get_session() as session:
                    result = await session.execute(
                        select(WebMonitor).where(WebMonitor.id == mon.id),
                    )
                    db_mon = result.scalar_one_or_none()
                    if db_mon:
                        db_mon.last_hash = new_hash
                        db_mon.last_size = new_size
                        db_mon.last_checked = datetime.now(timezone.utc)
                        db_mon.check_count += 1
                        await session.flush()

            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                changes.append(f"❌ *{mon.label}* — خطا: {exc}")

        await status_msg.delete()

        if changes:
            text = "🔔 *تغییرات شناسایی شد:*\n\n" + "\n\n".join(changes)
        else:
            text = "✅ *هیچ تغییری شناسایی نشد.* همه سایت‌ها بدون تغییر."

        await safe_reply(message, text)
        return

    # ── del ──
    if action in ("del", "حذف"):
        try:
            mid = int(rest)
        except ValueError:
            await safe_reply(message, "❌ `/monitor del [شماره]`")
            return
        async with get_session() as session:
            await session.execute(
                delete(WebMonitor).where(
                    WebMonitor.id == mid, WebMonitor.user_id == user_id,
                ),
            )
        await message.answer(f"✅ مانیتور #{mid} حذف شد.")
        return


# ════════════════════════════════════════
# 5. /autoreply — Keyword Auto-Responder
# ════════════════════════════════════════

@router.message(Command("autoreply"))
async def cmd_autoreply(message: Message) -> None:
    raw = extract_args(message.text or "", "/autoreply")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw:
        await safe_reply(message, "⚡ *پاسخ‌گوی خودکار:*\n\n"
            "`/autoreply add کلمه | پاسخ`\n"
            "`/autoreply list` — لیست قوانین\n"
            "`/autoreply del 1` — حذف\n"
            "`/autoreply on` / `/autoreply off`\n\n"
            "_وقتی یه پیام شامل کلمه کلیدی باشه، خودکار جواب می‌ده_")
        return

    cmd = raw.split(maxsplit=1)
    action = cmd[0].lower()
    rest = cmd[1] if len(cmd) > 1 else ""

    # ── add ──
    if action == "add":
        parts = [p.strip() for p in rest.split("|", 1)]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            await safe_reply(message, "❌ `/autoreply add کلمه | پاسخ`")
            return

        async with get_session() as session:
            rule = AutoReply(
                user_id=user_id,
                trigger=parts[0],
                response=parts[1],
                is_active=True,
            )
            session.add(rule)
            await session.flush()
            rid = rule.id

        await safe_reply(message, f"✅ قانون #{rid} ثبت شد!\n\n"
            f"🔑 کلمه: «{parts[0]}»\n"
            f"💬 پاسخ: {parts[1][:100]}")
        return

    # ── list ──
    if action in ("list", "لیست"):
        async with get_session() as session:
            result = await session.execute(
                select(AutoReply)
                .where(AutoReply.user_id == user_id)
                .order_by(AutoReply.id),
            )
            rules = result.scalars().all()

        if not rules:
            await safe_reply(message, "⚡ قانونی نداری.\n`/autoreply add کلمه | پاسخ`")
            return

        text = "⚡ *قوانین پاسخ خودکار:*\n\n"
        for r in rules:
            status = "✅" if r.is_active else "❌"
            text += f"{status} *{r.id}.* «{r.trigger}» → {r.response[:50]}...\n"
        await safe_reply(message, text)
        return

    # ── on / off ──
    if action in ("on", "فعال"):
        async with get_session() as session:
            result = await session.execute(
                select(AutoReply).where(AutoReply.user_id == user_id),
            )
            for r in result.scalars().all():
                r.is_active = True
            await session.flush()
        await message.answer("✅ همه قوانین فعال شدند.")
        return

    if action in ("of", "غیرفعال"):
        async with get_session() as session:
            result = await session.execute(
                select(AutoReply).where(AutoReply.user_id == user_id),
            )
            for r in result.scalars().all():
                r.is_active = False
            await session.flush()
        await message.answer("❌ همه قوانین غیرفعال شدند.")
        return

    # ── del ──
    if action in ("del", "حذف"):
        try:
            rid = int(rest)
        except ValueError:
            await safe_reply(message, "❌ `/autoreply del [شماره]`")
            return
        async with get_session() as session:
            await session.execute(
                delete(AutoReply).where(
                    AutoReply.id == rid, AutoReply.user_id == user_id,
                ),
            )
        await message.answer(f"✅ قانون #{rid} حذف شد.")
        return


# ════════════════════════════════════════
# 6. /plan — AI Content Calendar
# ════════════════════════════════════════

@router.message(Command("plan"))
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
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        mode_names = {"week": "هفتگی", "month": "ماهانه", "idea": "ایده‌ها"}
        header = f"📅 *برنامه {mode_names[mode]} — {topic}:*\n\n"

        for chunk in split_for_telegram(header + answer):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
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
                        except Exception as e:
                            logger.debug("Suppressed: %s", e)
                except Exception as exc:
                    logger.warning("Monitor #%d check failed: %s", mon.id, exc)

        except Exception as exc:
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
        except Exception:
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
        except Exception as e:
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
            except Exception:
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Agent failed: %s", exc, exc_info=True)
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await message.answer(user_friendly_error(exc))


