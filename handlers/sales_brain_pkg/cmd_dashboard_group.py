
"""sales_brain_pkg.cmd_dashboard_group — sub-module of sales_brain"""

from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError


import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import *  # auto-fixed

__all__ = ['cmd_dashboard', 'cmd_pipeline', 'cmd_leadscoring', 'cmd_pricewatch']

async def cmd_dashboard(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    chat_id = message.chat.id

    from arki_project.database.connection import get_session
    from arki_project.database.models import Customer, FinanceRecord
    from sqlalchemy import select

    # Gather all data
    async with get_session() as session:
        cust_result = await session.execute(
            select(Customer).where(Customer.owner_id == user_id)
        )
        customers = cust_result.scalars().all()

        fin_result = await session.execute(
            select(FinanceRecord).where(FinanceRecord.user_id == user_id)
        )
        finances = fin_result.scalars().all()

    # CRM stats
    total_customers = len(customers)
    total_orders = sum(c.total_orders for c in customers)
    total_revenue = sum(c.total_spent for c in customers)
    avg_order = total_revenue / total_orders if total_orders else 0
    vip_count = sum(1 for c in customers if c.total_orders >= 3)
    top_customer = max(customers, key=lambda c: c.total_spent) if customers else None

    # Finance stats
    income = sum(f.amount for f in finances if f.amount > 0)
    expense = sum(abs(f.amount) for f in finances if f.amount < 0)
    profit = income - expense

    # Product stats
    products = store.get_products(chat_id)
    catalog = store.get_catalog(chat_id)
    sales_data = store.get_sales(chat_id)

    text = (
        "📊 *داشبورد فروش — Sales Dashboard*\n\n"
        "━━━ 👥 مشتریان ━━━\n"
        f"کل: *{total_customers}* | VIP: *{vip_count}*\n"
        f"سفارشات: *{total_orders}* | میانگین: *€{avg_order:.0f}*\n"
    )
    if top_customer:
        text += f"بهترین مشتری: *{top_customer.name}* (€{top_customer.total_spent})\n"

    text += (
        "\n━━━ 💰 مالی ━━━\n"
        f"درآمد: *€{income:,}* | هزینه: *€{expense:,}*\n"
        f"سود: *€{profit:,}*\n"
    )

    text += (
        "\n━━━ 📦 محصولات ━━━\n"
        f"کاتالوگ: *{len(catalog)}* محصول\n"
        f"فروش ثبت‌شده: *{len(sales_data)}*\n"
    )

    text += (
        "\n━━━ ⚡ اقدامات سریع ━━━\n"
        "📋 `/crm list` — لیست مشتریان\n"
        "📊 `/crm report` — گزارش AI\n"
        "📈 `/forecast` — پیش‌بینی فروش\n"
        "🎯 `/funnel` — طراحی فانل\n"
        "💡 `/upsell` — پیشنهاد upsell\n"
    )

    await safe_reply(message, text)


# ═══════════════════════════════════════
# /pipeline — Sales Pipeline Manager
# ═══════════════════════════════════════

@router.message(Command("pipeline"))
async def cmd_pipeline(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Visual sales pipeline with stage tracking."""
    raw = extract_args(message.text or "", "/pipeline")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw or raw == "help":
        await safe_reply(message, "📈 *پایپلاین فروش — مدیریت مراحل:*\n\n"
            "*دستورات:*\n"
            "`/pipeline add [نام مشتری] | [محصول] | [مبلغ]` — افزودن دیل\n"
            "`/pipeline view` — نمایش پایپلاین\n"
            "`/pipeline move [شماره] | [مرحله]` — جابجایی\n"
            "`/pipeline won [شماره]` — تبدیل به فروش\n"
            "`/pipeline lost [شماره]` — از دست رفته\n"
            "`/pipeline analyze` — تحلیل AI پایپلاین\n\n"
            "*مراحل:*\n"
            "  🔵 `lead` — سرنخ اولیه\n"
            "  🟡 `contact` — تماس گرفته شد\n"
            "  🟠 `proposal` — پیشنهاد ارسال شد\n"
            "  🔴 `negotiation` — مذاکره\n"
            "  🟢 `won` — فروش موفق ✅\n"
            "  ⚫ `lost` — از دست رفته ❌")
        return

    cmd = raw.split(maxsplit=1)
    action = cmd[0].lower()
    rest = cmd[1] if len(cmd) > 1 else ""

    # Get pipeline from KV store
    pipeline = store.get_kv(message.chat.id, "pipeline")
    if not pipeline:
        pipeline = {"deals": [], "next_id": 1}

    stage_emojis = {
        "lead": "🔵", "contact": "🟡", "proposal": "🟠",
        "negotiation": "🔴", "won": "🟢", "lost": "⚫",
    }

    if action == "add":
        parts = [p.strip() for p in rest.split("|")]
        if not parts or not parts[0]:
            await safe_reply(message, "❌ `/pipeline add نام | محصول | مبلغ`")
            return
        deal = {
            "id": pipeline["next_id"],
            "name": parts[0],
            "product": parts[1] if len(parts) > 1 else "",
            "amount": parts[2] if len(parts) > 2 else "0",
            "stage": "lead",
        }
        pipeline["deals"].append(deal)
        pipeline["next_id"] += 1
        await store.set_kv(message.chat.id, "pipeline", pipeline)
        await safe_reply(message,
            f"✅ دیل #{deal['id']} اضافه شد!\n\n"
            f"👤 *{deal['name']}*\n"
            f"📦 {deal['product']}\n"
            f"💰 {deal['amount']}\n"
            "🔵 مرحله: lead")
        return

    if action == "view":
        if not pipeline["deals"]:
            await safe_reply(message, "📈 پایپلاین خالیه!\n`/pipeline add نام | محصول | مبلغ`")
            return

        text = "📈 *پایپلاین فروش:*\n\n"
        for stage in ["lead", "contact", "proposal", "negotiation", "won", "lost"]:
            deals_in_stage = [d for d in pipeline["deals"] if d["stage"] == stage]
            if deals_in_stage:
                emoji = stage_emojis.get(stage, "⚪")
                text += f"━━━ {emoji} *{stage.upper()}* ({len(deals_in_stage)}) ━━━\n"
                for d in deals_in_stage:
                    text += f"  #{d['id']} {d['name']} — {d['product']} (💰{d['amount']})\n"
                text += "\n"

        total = sum(float(d.get("amount", "0").replace(",", "").replace("€", ""))
                     for d in pipeline["deals"] if d["stage"] not in ("lost",))
        won = sum(float(d.get("amount", "0").replace(",", "").replace("€", ""))
                   for d in pipeline["deals"] if d["stage"] == "won")
        text += f"💰 *ارزش کل:* €{total:,.0f} | ✅ *فروش موفق:* €{won:,.0f}"

        for chunk in split_for_telegram(text):
            await safe_reply(message, chunk)
        return

    if action == "move":
        parts = [p.strip() for p in rest.split("|")]
        if len(parts) < 2:
            await safe_reply(message, "❌ `/pipeline move شماره | مرحله`")
            return
        try:
            deal_id = int(parts[0])
        except ValueError:
            await safe_reply(message, "❌ شماره دیل نامعتبر")
            return
        new_stage = parts[1].lower()
        if new_stage not in stage_emojis:
            await safe_reply(message, f"❌ مرحله نامعتبر. انتخاب کن: {', '.join(stage_emojis.keys())}")
            return
        for d in pipeline["deals"]:
            if d["id"] == deal_id:
                old = d["stage"]
                d["stage"] = new_stage
                await store.set_kv(message.chat.id, "pipeline", pipeline)
                await safe_reply(message,
                    f"✅ دیل #{deal_id} جابجا شد!\n"
                    f"{stage_emojis[old]} {old} → {stage_emojis[new_stage]} {new_stage}")
                return
        await safe_reply(message, f"❌ دیل #{deal_id} پیدا نشد")
        return

    if action in ("won", "lost"):
        try:
            deal_id = int(rest.strip())
        except ValueError:
            await safe_reply(message, f"❌ `/pipeline {action} شماره`")
            return
        for d in pipeline["deals"]:
            if d["id"] == deal_id:
                d["stage"] = action
                await store.set_kv(message.chat.id, "pipeline", pipeline)
                emoji = "🎉" if action == "won" else "😔"
                await safe_reply(message,
                    f"{emoji} دیل #{deal_id} — *{d['name']}* → *{action.upper()}*")
                return
        await safe_reply(message, f"❌ دیل #{deal_id} پیدا نشد")
        return

    if action == "analyze":
        if not pipeline["deals"]:
            await safe_reply(message, "📈 پایپلاین خالیه!")
            return
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        try:
            cfg = await ai_client.get_user_config(user_id)
            mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
            deals_txt = "\n".join(
                f"#{d['id']} {d['name']} | {d['product']} | €{d['amount']} | stage: {d['stage']}"
                for d in pipeline["deals"]
            )
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a sales analyst. Analyze this pipeline in Persian. "
                        "Give: conversion rate estimate, bottleneck identification, "
                        "recommended actions for each deal, revenue forecast, "
                        "and priority ranking."
                    )},
                    {"role": "user", "content": f"Pipeline deals:\n{deals_txt}"},
                ],
                model_key=mk, temperature=0.7, max_tokens=32768,
            )
            for chunk in split_for_telegram(f"📈 *تحلیل پایپلاین:*\n\n{body}"):
                await safe_reply(message, chunk)
        except HandlerError as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(user_friendly_error(exc))
        return

    await safe_reply(message, "❌ دستور نامعتبر. `/pipeline help`")


# ═══════════════════════════════════════
# /leadscoring — AI Lead Scoring
# ═══════════════════════════════════════

@router.message(Command("leadscoring"))
async def cmd_leadscoring(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """AI-powered lead scoring for CRM contacts."""
    raw = extract_args(message.text or "", "/leadscoring")

    if not raw:
        await safe_reply(message, "🎯 *امتیازدهی سرنخ — Lead Scoring:*\n\n"
            "`/leadscoring [اطلاعات مشتری]`\n\n"
            "*مثال:*\n"
            "`/leadscoring مریم | ۳ بار سفارش داده | شمع لوکس | بودجه بالا`\n"
            "`/leadscoring Sara | asked about bulk orders | from Etsy`\n"
            "`/leadscoring auto` — امتیازدهی خودکار تمام مشتریان CRM\n\n"
            "AI امتیاز ۰-۱۰۰ + اولویت + اقدام پیشنهادی می‌ده!")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        if raw.lower().strip() == "auto":
            # Score all CRM contacts
            from arki_project.database.connection import get_session
            from arki_project.database.models import Customer
            from sqlalchemy import select

            async with get_session() as session:
                result = await session.execute(
                    select(Customer).where(
                        Customer.owner_id == message.from_user.id
                    ).limit(20)
                )
                customers = result.scalars().all()

            if not customers:
                await safe_reply(message, "📭 هنوز مشتری‌ای در CRM نیست.\n`/crm add نام | شماره`")
                return

            cust_txt = "\n".join(
                f"#{c.id} {c.name} | phone: {c.phone} | tags: {c.tags} | "
                f"orders: {c.total_orders} | spent: €{c.total_spent} | notes: {c.note}"
                for c in customers
            )
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a lead scoring AI. Score each customer 0-100 based on "
                        "their purchase history, engagement, and potential. "
                        "Write in Persian. For each customer give:\n"
                        "- Score (0-100) with color: 🟢 hot (80+), 🟡 warm (50-79), 🔴 cold (<50)\n"
                        "- Priority level (بالا/متوسط/پایین)\n"
                        "- Recommended action (1 specific sentence)\n"
                        "- Revenue potential estimate\n"
                        "Sort by score descending."
                    )},
                    {"role": "user", "content": f"Score these customers:\n{cust_txt}"},
                ],
                model_key=mk, temperature=0.6, max_tokens=16384,
            )
        else:
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a lead scoring AI expert. Analyze this lead and give:\n"
                        "- Score (0-100) with explanation\n"
                        "- 🟢 Hot / 🟡 Warm / 🔴 Cold classification\n"
                        "- Purchase probability %\n"
                        "- Recommended approach strategy\n"
                        "- Suggested follow-up message template\n"
                        "- Revenue potential estimate\n"
                        "Write in Persian. Be specific and actionable."
                    )},
                    {"role": "user", "content": f"Score this lead: {raw}"},
                ],
                model_key=mk, temperature=0.7, max_tokens=32768,
            )

        for chunk in split_for_telegram(f"🎯 *امتیازدهی سرنخ:*\n\n{body}"):
            await safe_reply(message, chunk)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /pricewatch — Competitor Price Monitoring
# ═══════════════════════════════════════

@router.message(Command("pricewatch"))
async def cmd_pricewatch(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """AI pricing intelligence — competitor price analysis & recommendations."""
    raw = extract_args(message.text or "", "/pricewatch")

    if not raw:
        await safe_reply(message, "💲 *رصد قیمت رقبا — Price Watch:*\n\n"
            "`/pricewatch [محصول] | [قیمت فعلی شما]`\n\n"
            "*مثال:*\n"
            "`/pricewatch شمع سویا بتنی | €25`\n"
            "`/pricewatch handmade candle | 35`\n\n"
            "AI تحلیل می‌کنه:\n"
            "📊 محدوده قیمت رقبا\n"
            "🎯 قیمت بهینه پیشنهادی\n"
            "📈 استراتژی قیمت‌گذاری\n"
            "💡 تاکتیک‌های افزایش ارزش درک‌شده")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    current_price = parts[1] if len(parts) > 1 else "unknown"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        bctx = brand_ctx(message.chat.id)
        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a pricing strategist for artisan/handmade products. "
                    "Analyze competitor pricing on platforms like Etsy, Amazon Handmade, "
                    "Tori.fi, and Instagram shops. Write in Persian. Give:\n"
                    "1. Estimated competitor price range (min/avg/max)\n"
                    "2. Your recommended price with justification\n"
                    "3. Price positioning strategy (premium/mid/budget)\n"
                    "4. Bundle pricing suggestions\n"
                    "5. Discount strategy (when/how much)\n"
                    "6. Value-add tactics to justify higher price\n"
                    "7. Seasonal pricing adjustments\n"
                    "Be specific with numbers and percentages."
                )},
                {"role": "user", "content": (
                    f"Product: {product}\n"
                    f"Current price: {current_price}\n"
                    f"{'Brand: ' + bctx if bctx else ''}"
                )},
            ],
            model_key=mk, temperature=0.7, max_tokens=32768,
        )

        for chunk in split_for_telegram(f"💲 *رصد قیمت — {product}:*\n\n{body}"):
            await safe_reply(message, chunk)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))

