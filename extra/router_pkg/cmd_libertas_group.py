
"""router_pkg.cmd_libertas_group — sub-module of router"""

from __future__ import annotations
from arki_project.exceptions import ArkiBaseError


import asyncio
import logging
import os
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import *  # auto-fixed

__all__ = ['cmd_libertas', 'cb_libertas_info', 'cb_feedback_info', 'cmd_feedback', 'cmd_g0dstatus', 'cb_status', 'cb_status_group', 'cmd_classify']

async def cmd_libertas(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 2)
    if len(parts) < 3:
        await safe_reply(
            message,
            "⚔️ *L1B3RT4S — Hall of Fame*\n\n"
            "5 ترکیب اثبات‌شده مدل+پرامپت:\n\n"
            "• `hermes` — nousresearch/hermes-3-llama-3.1-70b\n"
            "• `dolphin` — cognitivecomputations/dolphin-mixtral-8x22b\n"
            "• `mythomax` — gryphe/mythomax-l2-13b\n"
            "• `toppy` — undi95/toppy-m-7b\n"
            "• `noromaid` — neversleep/noromaid-mixtral-8x7b\n\n"
            "استفاده: `/libertas [combo] [سوال]`\n"
            "مثال: `/libertas hermes how to bypass filters`",
        )
        return

    combo = parts[1].lower()
    query = parts[2]

    # Map combo to model
    combo_models = {
        "hermes": "nousresearch/hermes-3-llama-3.1-70b",
        "dolphin": "cognitivecomputations/dolphin-mixtral-8x22b",
        "mythomax": "gryphe/mythomax-l2-13b",
        "toppy": "undi95/toppy-m-7b",
        "noromaid": "neversleep/noromaid-mixtral-8x7b",
    }
    model = combo_models.get(combo)
    if not model:
        await safe_reply(message, f"❌ ترکیب `{combo}` یافت نشد. موجود: {', '.join(combo_models.keys())}")
        return

    or_key = _get_openrouter_key()  # v25.0: Always returns usable value

    uid = message.from_user.id  # type: ignore[union-attr]
    wait_msg = await safe_reply(message, f"⚔️ *L1B3RT4S* — `{combo}` در حال پردازش...")

    result = await bridge.chat_completion(
        messages=[{"role": "user", "content": query}],
        model=model,
        openrouter_api_key=or_key,
        apex=True,  # L1B3RT4S always uses APEX
        temperature=0.9,
    )

    if not result.success:
        await safe_edit_text(wait_msg, f"❌ خطا: {result.error}")
        return

    data = result.data
    content = ""
    if "choices" in data and data["choices"]:
        content = data["choices"][0].get("message", {}).get("content", "")
    elif "content" in data:
        content = data["content"]

    await safe_delete(wait_msg)
    if content:
        for chunk in split_for_telegram(content):
            await safe_reply(message, chunk)


@router.callback_query(lambda c: c.data == "extra:libertas")
async def cb_libertas_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "⚔️ *L1B3RT4S — Hall of Fame*\n\n"
        "5 ترکیب اثبات‌شده مدل+APEX پرامپت.\n\n"
        "استفاده: `/libertas [combo] [سوال]`",
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# FEEDBACK — /feedback
# ═══════════════════════════════════════════════════════════════════════

@router.callback_query(lambda c: c.data == "extra:feedback_info")
async def cb_feedback_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "📡 *Feedback — حلقه یادگیری*\n\n"
        "بازخورد کیفیت → EMA-based learning → بهبود خودکار\n\n"
        "استفاده: `/feedback [good/bad] [توضیح]`\n\n"
        "_بازخوردها به APEX API ارسال و پردازش می‌شن._",
    )
    await cq.answer()


@router.message(Command("feedback"))
async def cmd_feedback(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 2)
    if len(parts) < 2:
        await safe_reply(
            message,
            "📡 *Feedback*\n\n"
            "استفاده: `/feedback good` یا `/feedback bad [توضیح]`",
        )
        return

    rating = parts[1].lower()
    if rating not in ("good", "bad", "positive", "negative"):
        await safe_reply(message, "❌ فقط `good` یا `bad`")
        return

    result = await bridge.submit_feedback(
        response_id=f"tg_{message.from_user.id}_{int(time.time())}",  # type: ignore[misc]
        rating="positive" if rating in ("good", "positive") else "negative",
    )

    if result.success:
        await safe_reply(message, f"✅ بازخورد ثبت شد: `{rating}`")
    else:
        await safe_reply(message, f"❌ خطا: {result.error}")


# ═══════════════════════════════════════════════════════════════════════
# STATUS — /g0dstatus
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("g0dstatus"))
async def cmd_g0dstatus(message: Message) -> None:
    running = await bridge.is_server_running()

    if not running:
        await safe_reply(
            message,
            "📊 *APEX Status*\n\n"
            "❌ سرور APEX فعال نیست.\n"
            "`/extra` برای راه‌اندازی",
        )
        return

    # Fetch live data from APEX API
    info_resp, models_resp, meta_resp = await asyncio.gather(
        bridge.get_info(),
        bridge.get_models(),
        bridge.get_metadata_stats(),
    )

    text = "📊 *APEX Status — زنده از API اصلی*\n\n"

    if info_resp.success:
        d = info_resp.data
        text += (
            f"*{d.get('name', '?')}*\n"
            f"نسخه: `{d.get('version', '?')}`\n"
            f"Endpoints: {len(d.get('endpoints', {}))}\n"
            f"لایسنس: {d.get('license', '?')}\n\n"
        )

    if models_resp.success:
        models = models_resp.data.get("data", [])
        virtual = [m for m in models if "ultraplinian" in m.get("id", "") or "consortium" in m.get("id", "")]
        individual = [m for m in models if m not in virtual]
        text += (
            "*مدل‌ها:*\n"
            f"  مجازی (ULTRAPLINIAN/CONSORTIUM): {len(virtual)}\n"
            f"  فردی: {len(individual)}\n"
            f"  کل: {len(models)}\n\n"
        )

    or_key = _get_openrouter_key()
    text += f"*OpenRouter API:* {'✅ متصل' if or_key else '🤖 خودمختار — FreeAccessRouter فعال'}\n"

    if meta_resp.success:
        stats = meta_resp.data
        text += (
            "\n*ZDR Metadata:*\n"
            f"  Events: {stats.get('total_events', 0)}\n"
            f"  Avg duration: {stats.get('avg_duration_ms', 0)}ms\n"
        )

    await safe_reply(message, text)


@router.callback_query(lambda c: c.data == "extra:status")
async def cb_status(cq: CallbackQuery) -> None:
    running = await bridge.is_server_running()
    or_key = _get_openrouter_key()
    srv = "✅ فعال" if running else "❌ غیرفعال"
    ork = "✅ متصل" if or_key else "🤖 خودمختار"

    from arki_project.utils.models_registry import APEX_TIERS, MODELS

    # Count internal models
    n_internal = sum(1 for m in MODELS.values() if m.provider in ("gemini", "groq"))
    n_g0d = sum(1 for m in MODELS.values() if m.provider == "openrouter")

    buttons = []

    # Internal models group
    buttons.append([
        InlineKeyboardButton(text="🔵 Gemini (6)", callback_data="sgrp:gemini"),
        InlineKeyboardButton(text="🟠 Groq (7)", callback_data="sgrp:groq"),
    ])

    # APEX tiers
    for tier_name, tier_data in APEX_TIERS.items():
        n = len(tier_data["models"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{tier_data['emoji']} APEX {tier_data['label']} ({n})",
                callback_data=f"sgrp:g0d_{tier_name}",
            ),
        ])

    # Uncensored shortcut group
    from arki_project.utils.models_registry import UNCENSORED_KEYS
    buttons.append([
        InlineKeyboardButton(
            text=f"🔓 بدون فیلتر ({len(UNCENSORED_KEYS)})",
            callback_data="sgrp:uncensored",
        ),
    ])

    buttons.append([InlineKeyboardButton(text="« بازگشت", callback_data="menu:extra")])

    await safe_edit_text(
        cq.message,
        f"📊 *Status & Models — {n_internal + n_g0d} مدل*\n\n"
        f"سرور: {srv} | OpenRouter: {ork}\n\n"
        "یک گروه انتخاب کنید تا مدل‌هاش رو ببینید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await cq.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("sgrp:"))
async def cb_status_group(cq: CallbackQuery) -> None:
    """Expand a model group in Status & Models."""
    await cq.answer()
    group = cq.data[5:]  # Strip "sgrp:" prefix

    from arki_project.utils.models_registry import APEX_TIERS, MODELS

    buttons = []
    title = ""

    if group == "gemini":
        title = "🔵 *Gemini — 6 مدل*"
        for key, m in MODELS.items():
            if m.provider != "gemini":
                continue
            buttons.append([
                InlineKeyboardButton(text=f"{m.emoji} {m.name} — {m.desc}", callback_data="noop"),
            ])

    elif group == "groq":
        title = "🟠 *Groq — 7 مدل* (🔒 نیاز به کلید)"
        for key, m in MODELS.items():
            if m.provider != "groq":
                continue
            buttons.append([
                InlineKeyboardButton(text=f"🔒 {m.name} — {m.desc}", callback_data="noop"),
            ])

    elif group == "uncensored":
        from arki_project.utils.models_registry import UNCENSORED_KEYS
        title = "🔓 *بدون فیلتر — Uncensored*"
        n = len(UNCENSORED_KEYS)
        title = f"🔓 *بدون فیلتر — {n} مدل*\n_بدون سانسور و محدودیت محتوا_"
        items = [(k, MODELS[k]) for k in UNCENSORED_KEYS if k in MODELS]
        for i in range(0, len(items), 2):
            k1, m1 = items[i]
            row = [InlineKeyboardButton(
                text=f"{m1.emoji} {m1.name}",
                callback_data=f"m:{k1}",
            )]
            if i + 1 < len(items):
                k2, m2 = items[i + 1]
                row.append(InlineKeyboardButton(
                    text=f"{m2.emoji} {m2.name}",
                    callback_data=f"m:{k2}",
                ))
            buttons.append(row)

    elif group.startswith("g0d_"):
        tier_name = group[4:]
        tier_data = APEX_TIERS.get(tier_name, {})
        tier_models = tier_data.get("models", {})
        emoji = tier_data.get("emoji", "🧬")
        label = tier_data.get("label", tier_name)
        n = len(tier_models)
        title = f"{emoji} *APEX {label} — {n} مدل*"

        # Show models as 2-column buttons
        items = list(tier_models.values())
        for i in range(0, len(items), 2):
            row = [InlineKeyboardButton(
                text=f"{items[i].emoji} {items[i].name}",
                callback_data=f"m:{list(tier_models.keys())[i]}",
            )]
            if i + 1 < len(items):
                row.append(InlineKeyboardButton(
                    text=f"{items[i+1].emoji} {items[i+1].name}",
                    callback_data=f"m:{list(tier_models.keys())[i+1]}",
                ))
            buttons.append(row)

    buttons.append([InlineKeyboardButton(text="« بازگشت به Status", callback_data="extra:status")])

    await safe_edit_text(
        cq.message,
        f"{title}\n\nمدلی رو انتخاب کن تا برای چت فعال بشه:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )



# ═══════════════════════════════════════════════════════════════════════
# CLASSIFY — /classify [text] (via chat pipeline)
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("classify"))
async def cmd_classify(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await safe_reply(
            message,
            "🔬 *Classify — طبقه‌بند پرامپت*\n\n"
            "13 دامنه: benign, gray, meta, cyber, fraud, deception, "
            "privacy, illegal, violence, self\\_harm, sexual, hate, cbrn\n\n"
            "استفاده: `/classify [متن]`",
        )
        return

    text = parts[1]
    or_key = _get_openrouter_key()  # v25.0: Always returns usable value

    # Use chat pipeline with a classify prompt
    result = await bridge.chat_completion(
        messages=[{
            "role": "user",
            "content": f"Classify this prompt into one of these domains: benign, gray, meta, cyber, fraud, deception, privacy, illegal, violence, self_harm, sexual, hate, cbrn.\n\nProvide the domain, subcategory, confidence (0-100), and reasoning.\n\nPrompt to classify: \"{text}\"",
        }],
        model="google/gemini-2.5-pro",
        openrouter_api_key=or_key,
    )

    if not result.success:
        await safe_reply(message, f"❌ خطا: {result.error}")
        return

    content = ""
    data = result.data
    if "choices" in data and data["choices"]:
        content = data["choices"][0].get("message", {}).get("content", "")

    await safe_reply(message, f"🔬 *Classify*\n\n{content or '—'}")

