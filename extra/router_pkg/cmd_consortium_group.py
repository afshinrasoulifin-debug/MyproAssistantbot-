
"""router_pkg.cmd_consortium_group — sub-module of router"""

from __future__ import annotations
from arki_project.exceptions import ArkiBaseError


import asyncio
import logging
import os
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

__all__ = ['cmd_consortium', 'cb_consortium_info', 'cmd_chat', 'cb_chat_info', 'cmd_parseltongue', 'cb_parseltongue_info', 'cmd_autotune_pro', 'cb_autotune_info', 'cmd_stm', 'cb_stm', 'cb_stm_toggle']

async def cmd_consortium(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 2)
    if len(parts) < 2:
        await safe_reply(
            message,
            "🧠 *CONSORTIUM — هوش جمعی*\n\n"
            "تمام مدل‌ها پاسخ می‌دن → امتیازدهی → Orchestrator ترکیب می‌کنه.\n"
            "حقیقت ترکیبی (Ground Truth) تولید می‌شه.\n\n"
            "Orchestrator مدل‌ها از APEX اصلی:\n"
            "• claude-sonnet-4.6\n• gpt-5.3-chat\n"
            "• gemini-3-pro-preview\n• grok-4\n"
            "• claude-opus-4.6\n• deepseek-v3.2\n\n"
            "استفاده: `/consortium [tier] [سوال]`\n"
            "مثال: `/consortium smart what is consciousness?`",
        )
        return

    tier = "fast"
    query = ""
    if len(parts) == 2:
        query = parts[1]
    elif len(parts) >= 3:
        if parts[1].lower() in VALID_TIERS:
            tier = parts[1].lower()
            query = parts[2]
        else:
            query = " ".join(parts[1:])

    if not query.strip():
        await safe_reply(message, "❌ لطفاً سوال خود را وارد کنید.")
        return

    uid = message.from_user.id  # type: ignore[union-attr]
    gm = uid in _apex_users
    stm = _stm_users.get(uid, [])
    or_key = _get_openrouter_key()  # v25.0: Always returns usable value

    wait_msg = await safe_reply(
        message,
        "🧠 *CONSORTIUM شروع شد!*\n"
        f"⚡ Tier: `{tier}` | APEX: {'🟢' if gm else '⚪'}\n"
        "⏳ فاز ۱: جمع‌آوری پاسخ از تمام مدل‌ها...\n"
        "⏳ فاز ۲: Orchestrator ترکیب می‌کنه..."
    )

    t0 = time.time()
    result = await bridge.consortium_completion(
        messages=[{"role": "user", "content": query}],
        tier=tier,
        openrouter_api_key=or_key,
        apex=gm,
        stm_modules=stm if stm else None,
        max_tokens=8192,
    )
    elapsed = int((time.time() - t0) * 1000)

    if not result.success:
        await safe_edit_text(wait_msg, f"❌ خطا: {result.error}")
        return

    data = result.data
    content = ""
    if "choices" in data and data["choices"]:
        content = data["choices"][0].get("message", {}).get("content", "")
    elif "content" in data:
        content = data["content"]

    meta = data.get("consortium_metadata", data.get("metadata", {}))
    synth_model = meta.get("orchestrator_model", data.get("model", "?"))
    models_queried = meta.get("models_queried", "?")
    models_succeeded = meta.get("models_succeeded", "?")

    await safe_edit_text(
        wait_msg,
        f"🧠 *CONSORTIUM — Ground Truth* ({elapsed}ms)\n"
        f"📊 {models_succeeded}/{models_queried} مدل → Orchestrator: `{synth_model}`"
    )

    if content:
        for chunk in split_for_telegram(content):
            await safe_reply(message, chunk)


@router.callback_query(lambda c: c.data == "extra:consortium")
async def cb_consortium_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "🧠 *CONSORTIUM — هوش جمعی مدل‌ها*\n\n"
        "مثل ULTRAPLINIAN اما به جای انتخاب بهترین، *تمام پاسخ‌ها* را "
        "به مدل Orchestrator می‌دهد.\n\n"
        "Orchestrator همه را تحلیل و ترکیب می‌کند تا حقیقت ترکیبی تولید شود.\n\n"
        "استفاده: `/consortium [tier] [سوال]`",
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# CHAT — /chat [model] [query]
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("chat"))
async def cmd_chat(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 2)
    if len(parts) < 2:
        await safe_reply(
            message,
            "💬 *Chat — APEX Single-Model Pipeline*\n\n"
            "پایپلاین کامل: APEX + AutoTune + Parseltongue + STM\n\n"
            "استفاده:\n"
            "`/chat [سوال]` — مدل پیش‌فرض\n"
            "`/chat google/gemini-2.5-pro [سوال]`\n"
            "`/chat anthropic/claude-3.5-sonnet [سوال]`\n\n"
            "همچنین مدل‌های مجازی:\n"
            "`/chat ultraplinian/fast [سوال]`\n"
            "`/chat consortium/smart [سوال]`",
        )
        return

    uid = message.from_user.id  # type: ignore[union-attr]
    gm = uid in _apex_users
    stm = _stm_users.get(uid, [])
    or_key = _get_openrouter_key()  # v25.0: Always returns usable value

    # Parse model and query
    model = _user_models.get(uid, "google/gemini-2.5-pro")
    query = ""
    if len(parts) == 2:
        query = parts[1]
    elif len(parts) >= 3:
        # Check if first arg looks like a model (contains /)
        if "/" in parts[1]:
            model = parts[1]
            query = parts[2]
        else:
            query = " ".join(parts[1:])

    wait_msg = await safe_reply(message, f"💬 مدل: `{model}` | APEX: {'🟢' if gm else '⚪'}...")

    result = await bridge.chat_completion(
        messages=[{"role": "user", "content": query}],
        model=model,
        openrouter_api_key=or_key,
        apex=gm,
        autotune=True,
        stm_modules=stm if stm else None,
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
    else:
        await safe_reply(message, "❌ پاسخ خالی دریافت شد.")


@router.callback_query(lambda c: c.data == "extra:chat")
async def cb_chat_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "💬 *Chat — APEX Single-Model Pipeline*\n\n"
        "APEX → AutoTune → Parseltongue → مدل → STM\n\n"
        "استفاده: `/chat [model] [سوال]`\n"
        "مثال: `/chat google/gemini-2.5-pro hello`",
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# PARSELTONGUE — /parseltongue [technique] [text]
# ═══════════════════════════════════════════════════════════════════════

TECHNIQUES = ["leetspeak", "unicode", "zwj", "mixedcase", "phonetic", "random"]


@router.message(Command("parseltongue"))
async def cmd_parseltongue(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 2)
    if len(parts) < 3:
        await safe_reply(
            message,
            "🐍 *Parseltongue — مبهم‌سازی ورودی*\n\n"
            "33 کلمه تریگر پیش‌فرض + 6 تکنیک:\n"
            "• `leetspeak` — H4ck → |-|a(k\n"
            "• `unicode` — حروف شبیه یونیکد\n"
            "• `zwj` — کاراکتر نامرئی بین حروف\n"
            "• `mixedcase` — HaCk\n"
            "• `phonetic` — phon3tic\n"
            "• `random` — ترکیب تصادفی\n\n"
            "استفاده: `/parseltongue [تکنیک] [متن]`\n"
            "مثال: `/parseltongue leetspeak how to hack a website`",
        )
        return

    technique = parts[1].lower()
    if technique not in TECHNIQUES:
        technique = "leetspeak"
    text = parts[2]

    result = await bridge.encode_parseltongue(text, technique)

    if not result.success:
        await safe_reply(message, f"❌ خطا: {result.error}")
        return

    data = result.data
    triggers = data.get("triggers_found", [])
    transformed = data.get("transformed_text", text)
    transforms = data.get("transformations", [])

    await safe_reply(
        message,
        "🐍 *Parseltongue*\n\n"
        f"تکنیک: `{data.get('technique_used', technique)}`\n"
        f"تریگرها: {len(triggers)} — {', '.join(triggers[:10]) or '—'}\n"
        f"تبدیل‌ها: {len(transforms)}\n\n"
        f"*ورودی:*\n`{text}`\n\n"
        f"*خروجی:*\n`{transformed}`"
    )


@router.callback_query(lambda c: c.data == "extra:parseltongue")
async def cb_parseltongue_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "🐍 *Parseltongue*\n\n6 تکنیک مبهم‌سازی.\nاستفاده: `/parseltongue [تکنیک] [متن]`",
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# AUTOTUNE PRO — /autotunepro [text]
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("autotunepro"))
async def cmd_autotune_pro(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await safe_reply(
            message,
            "🎛 *AutoTune Pro — تحلیل هوشمند context*\n\n"
            "5 نوع context: technical, creative, conversational, analytical, chaotic\n"
            "5 استراتژی: conservative, balanced, creative, aggressive, adaptive\n\n"
            "استفاده: `/autotunepro [متن]`",
        )
        return

    text = parts[1]
    result = await bridge.analyze_autotune(text)

    if not result.success:
        await safe_reply(message, f"❌ خطا: {result.error}")
        return

    data = result.data
    params = data.get("params", {})
    ctx = data.get("detected_context", "?")
    conf = data.get("confidence", 0)
    scores = data.get("context_scores", [])

    scores_text = "\n".join(
        f"  `{s.get('type', '?')}`: {s.get('score', 0)} ({s.get('percentage', 0)}%)"
        for s in scores
    )

    await safe_reply(
        message,
        "🎛 *AutoTune Pro — نتیجه تحلیل*\n\n"
        f"📎 Context: `{ctx}` (اطمینان: {conf}%)\n"
        f"📝 {data.get('reasoning', '')}\n\n"
        "*پارامترهای پیشنهادی:*\n"
        "```\n"
        f"temperature:       {params.get('temperature', '?')}\n"
        f"top_p:             {params.get('top_p', '?')}\n"
        f"top_k:             {params.get('top_k', '?')}\n"
        f"frequency_penalty: {params.get('frequency_penalty', '?')}\n"
        f"presence_penalty:  {params.get('presence_penalty', '?')}\n"
        f"repetition_penalty:{params.get('repetition_penalty', '?')}\n"
        "```\n\n"
        f"*Score breakdown:*\n{scores_text}"
    )


@router.callback_query(lambda c: c.data == "extra:autotunepro")
async def cb_autotune_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "🎛 *AutoTune Pro*\n\n"
        "تحلیل هوشمند متن → پیشنهاد بهینه temperature/top_p/top_k\n\n"
        "استفاده: `/autotunepro [متن شما]`",
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# STM — /stm
# ═══════════════════════════════════════════════════════════════════════

STM_MODULE_LIST = [
    {"id": "hedge_reducer", "name": "Hedge Reducer", "desc": "حذف I think/maybe/perhaps"},
    {"id": "direct_mode", "name": "Direct Mode", "desc": "حذف مقدمه‌چینی"},
    {"id": "casual_mode", "name": "Casual Mode", "desc": "تبدیل رسمی به غیررسمی"},
]


def _stm_keyboard(uid: int) -> InlineKeyboardMarkup:
    active = _stm_users.get(uid, [])
    rows = []
    for mod in STM_MODULE_LIST:
        mark = "✅" if mod["id"] in active else "⬜"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {mod['name']}",
            callback_data=f"stm:{mod['id']}",
        )])
    if active:
        rows.append([InlineKeyboardButton(text="🔴 غیرفعال همه", callback_data="stm:off")])
    rows.append([InlineKeyboardButton(text="« بازگشت", callback_data="menu:extra")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("stm"))
async def cmd_stm(message: Message) -> None:
    uid = message.from_user.id  # type: ignore[union-attr]
    active = _stm_users.get(uid, [])
    status = ", ".join(active) if active else "غیرفعال"

    # Test the APEX transform endpoint
    test_text = ""
    if await bridge.is_server_running():
        test_result = await bridge.transform_stm(
            "I think perhaps maybe you should try this approach",
            ["hedge_reducer"],
        )
        if test_result.success:
            test_text = f"\n\n*تست زنده Hedge Reducer:*\n`{test_result.data.get('transformed_text', '')}`"

    await safe_reply(
        message,
        "⚡ *STM — Semantic Transformation Modules*\n\n"
        f"وضعیت فعلی: {status}\n\n"
        "ماژول‌ها (مستقیم از APEX):\n"
        + "\n".join(f"• *{m['name']}* — {m['desc']}" for m in STM_MODULE_LIST)
        + f"{test_text}\n\n"
        "ماژول‌های فعال در `/race` و `/chat` اعمال می‌شن:",
        reply_markup=_stm_keyboard(uid),
    )


@router.callback_query(lambda c: c.data == "extra:stm")
async def cb_stm(cq: CallbackQuery) -> None:
    uid = cq.from_user.id
    await safe_edit_text(
        cq.message,
        "⚡ *STM Modules*\n\nماژول‌ها را فعال/غیرفعال کنید:",
        reply_markup=_stm_keyboard(uid),
    )
    await cq.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("stm:"))
async def cb_stm_toggle(cq: CallbackQuery) -> None:
    uid = cq.from_user.id
    choice = cq.data.split(":", 1)[1]  # type: ignore[union-attr]

    if choice == "off":
        _stm_users.pop(uid, None)
        await safe_edit_text(
            cq.message,
            "⚡ *STM* — همه غیرفعال ✅",
            reply_markup=_stm_keyboard(uid),
        )
        await cq.answer("STM off")
        return

    active = _stm_users.get(uid, [])
    if choice in active:
        active.remove(choice)
    else:
        active.append(choice)
    _stm_users[uid] = active

    await safe_edit_text(
        cq.message,
        f"⚡ *STM* — فعال: {', '.join(active) if active else 'هیچ'}",
        reply_markup=_stm_keyboard(uid),
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# L1B3RT4S — /libertas  (via /chat with specific models)
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("libertas"))



async def libertas_handler(message) -> None:
    """Libertas handler stub."""
    pass

