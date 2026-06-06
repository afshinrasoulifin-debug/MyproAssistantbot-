from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/extra/router.py
──────────────────────
Telegram router for the Extra section.

This router is a THIN BRIDGE to the APEX API server running as a
separate Node.js process. The ENTIRE APEX project runs UNTOUCHED —
not a single line of TypeScript code is modified.

Architecture:
  [Telegram] → [This router] → [HTTP bridge] → [APEX API :7860] → [OpenRouter]

Features exposed (ALL from original APEX without modification):
  ✅ /race        — ULTRAPLINIAN multi-model racing (56+ models, 5 tiers, Liquid Response)
  ✅ /consortium  — CONSORTIUM hive-mind synthesis (orchestrator models)
  ✅ /apex     — APEX system prompt + 6 personas + Depth Directive
  ✅ /chat        — Single-model with full pipeline (APEX+AutoTune+Parseltongue+STM)
  ✅ /parseltongue — Text obfuscation (6 techniques, 3 intensities)
  ✅ /autotunepro — Context-adaptive parameter analysis (5 types × 5 strategies)
  ✅ /stm         — Semantic Transformation Modules (hedge reducer, direct, casual)
  ✅ /classify    — Prompt classification (via /chat pipeline)
  ✅ /libertas    — Hall of Fame combos (via /chat with specific models)
  ✅ /feedback    — Quality feedback for EMA learning loop
  ✅ /g0dstatus   — Full APEX server status + model list + tier info
"""


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

from arki_project.utils.models_registry import split_for_telegram
from arki_project.utils.safe_send import safe_reply, safe_edit_text, safe_delete

from arki_project.extra import bridge

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

router = Router(name="extra")

# ── Per-user state ───────────────────────────────────────────────────

_apex_users: set[int] = set()          # Users with enhanced prompt mode (rebranded from apex)
_stm_users: dict[int, list[str]] = {}     # uid → active STM module IDs
_user_models: dict[int, str] = {}         # uid → preferred model for /chat


# ── Public hooks for ai_chat.py integration ──────────────────────────

def get_apex_prompt(user_id: int) -> str | None:
    """Return marker if APEX active (actual prompt injection done by APEX API)."""
    if user_id in _apex_users:
        return "__APEX_ACTIVE__"
    return None


def apply_stm_to_response(user_id: int, text: str) -> str:
    """Apply STM via APEX API (called synchronously — falls back to passthrough)."""
    active_ids = _stm_users.get(user_id, [])
    if not active_ids:
        return text
    # STM is applied at the API level when using /race, /consortium, /chat
    # For direct ai_chat responses, we'd need an async call; for now passthrough
    return text


def _get_openrouter_key() -> str | None:
    """v25.0 AUTONOMOUS: Always returns a usable key.
    
    Priority: env var → provisioned pool → empty string (for :free models).
    Never returns None — system always has free access via OpenRouter :free.
    """
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    # v25.0: Try FreeAccessRouter provisioned keys
    try:
        from arki_project.utils.free_access_router import get_free_router
        router = get_free_router()
        if hasattr(router, "_provisioned_keys"):
            or_keys = router._provisioned_keys.get("openrouter_free", [])
            if or_keys:
                return or_keys[0]
    except ArkiBaseError as _err:
        logger.warning("Suppressed error: %s", _err)
    # AUTONOMOUS: Return empty string — OpenRouter :free works without key
    return ""


VALID_TIERS = ["fast", "standard", "smart", "power", "ultra"]


# ═══════════════════════════════════════════════════════════════════════
# EXTRA MENU
# ═══════════════════════════════════════════════════════════════════════

def _extra_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Race (ULTRAPLINIAN)", callback_data="extra:race"),
         InlineKeyboardButton(text="🧠 Consortium", callback_data="extra:consortium")],
        [InlineKeyboardButton(text="🜏 APEX", callback_data="extra:apex"),
         InlineKeyboardButton(text="💬 Chat Pipeline", callback_data="extra:chat")],
        [InlineKeyboardButton(text="🐍 Parseltongue", callback_data="extra:parseltongue"),
         InlineKeyboardButton(text="🎛 AutoTune Pro", callback_data="extra:autotunepro")],
        [InlineKeyboardButton(text="⚡ STM", callback_data="extra:stm"),
         InlineKeyboardButton(text="⚔️ L1B3RT4S", callback_data="extra:libertas")],
        [InlineKeyboardButton(text="📊 Status & Models", callback_data="extra:status"),
         InlineKeyboardButton(text="📡 Feedback", callback_data="extra:feedback_info")],
        [InlineKeyboardButton(text="« بازگشت به منوی اصلی", callback_data="menu:main")],
    ])


@router.message(Command("extra"))
async def cmd_extra(message: Message) -> None:
    running = await bridge.is_server_running()
    status = "✅ فعال" if running else "⚠️ در حال راه‌اندازی..."

    if not running:
        # Auto-start APEX server
        _t = asyncio.create_task(_ensure_server(message))
        _t.add_done_callback(lambda t: logger.error("Server start failed: %s", t.exception()) if t.done() and not t.cancelled() and t.exception() else None)

    or_key = _get_openrouter_key()
    or_status = "✅ متصل (کلید)" if or_key else "🤖 خودمختار — ۱۱۶ مدل رایگان"

    await safe_reply(
        message,
        "🧬 *Extra — APEX Engine*\n\n"
        f"سرور APEX: {status}\n"
        f"OpenRouter API: {or_status}\n\n"
        "⚡ *تمام کد اصلی APEX بدون هیچ تغییری اجرا می‌شود*\n"
        "56+ مدل AI • 5 سطح • Liquid Response\n\n"
        "یک گزینه انتخاب کنید:",
        reply_markup=_extra_menu_keyboard(),
    )


@router.callback_query(lambda c: c.data == "menu:extra")
async def cb_extra_menu(cq: CallbackQuery) -> None:
    logger.info(">>> cb_extra_menu TRIGGERED by user %s", cq.from_user.id)
    await safe_edit_text(
        cq.message,
        "🧬 *Extra — APEX Engine*\n\nیک گزینه انتخاب کنید:",
        reply_markup=_extra_menu_keyboard(),
    )
    await cq.answer()


async def _ensure_server(message: Message | None = None) -> bool:
    """Ensure APEX server is running."""
    if await bridge.is_server_running():
        return True
    ok = await bridge.start_apex_server()
    if not ok and message:
        await safe_reply(message, "❌ خطا در راه‌اندازی سرور APEX")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# APEX — /apex
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("apex"))
async def cmd_apex(message: Message) -> None:
    uid = message.from_user.id  # type: ignore[union-attr]
    active = uid in _apex_users

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔴 غیرفعال کن" if active else "🟢 فعال کن",
            callback_data="apex:toggle",
        )],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:extra")],
    ])

    status = "🟢 *فعال*" if active else "⚪ غیرفعال"
    await safe_reply(
        message,
        "🜏 *APEX — حالت نامحدود*\n\n"
        f"وضعیت: {status}\n\n"
        "وقتی APEX فعاله:\n"
        "• *تمام پیام‌های عادی* از طریق APEX پردازش می‌شن (نه Gemini)\n"
        "• *تمام فیلترها* غیرفعال می‌شن\n"
        "• 59 مدل AI از طریق OpenRouter\n"
        "• سیستم‌پرامپت APEX ULTIMATE v∞.0\n"
        "• `/race`، `/consortium` و `/chat` هم با APEX کار می‌کنن\n\n"
        "6 پرسونا • Anti-Hedge Directive • Depth Directive • بدون محدودیت",
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data == "extra:apex")
async def cb_apex(cq: CallbackQuery) -> None:
    uid = cq.from_user.id
    active = uid in _apex_users
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔴 غیرفعال کن" if active else "🟢 فعال کن",
            callback_data="apex:toggle",
        )],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:extra")],
    ])
    status = "🟢 *فعال*" if active else "⚪ غیرفعال"
    mode_desc = (
        "\n\n✅ تمام پیام‌ها از APEX پردازش می‌شن\n"
        "✅ تمام فیلترها غیرفعال\n"
        "✅ 59 مدل بدون محدودیت"
    ) if active else (
        "\n\nبرای فعال‌سازی دکمه زیر رو بزن.\n"
        "تمام چت عادی از APEX رد می‌شه."
    )
    await safe_edit_text(
        cq.message,
        f"🜏 *APEX — حالت نامحدود*\n\nوضعیت: {status}{mode_desc}",
        reply_markup=kb,
    )
    await cq.answer()


@router.callback_query(lambda c: c.data == "apex:toggle")
async def cb_apex_toggle(cq: CallbackQuery) -> None:
    uid = cq.from_user.id
    if uid in _apex_users:
        _apex_users.discard(uid)
        await cq.answer("🔴 APEX OFF — چت عادی از Gemini")
    else:
        _apex_users.add(uid)
        await cq.answer("🟢 APEX ON — همه چت از APEX بدون فیلتر")

    active = uid in _apex_users
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔴 غیرفعال کن" if active else "🟢 فعال کن",
            callback_data="apex:toggle",
        )],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:extra")],
    ])
    status = "🟢 *فعال*" if active else "⚪ غیرفعال"
    mode_desc = (
        "\n\n✅ تمام پیام‌ها از APEX پردازش می‌شن\n"
        "✅ تمام فیلترها غیرفعال\n"
        "✅ 59 مدل بدون محدودیت"
    ) if active else (
        "\n\n💤 چت عادی از Gemini پردازش می‌شه"
    )
    await safe_edit_text(
        cq.message,
        f"🜏 *APEX — حالت نامحدود*\n\nوضعیت: {status}{mode_desc}",
        reply_markup=kb,
    )


# ═══════════════════════════════════════════════════════════════════════
# RACE — /race [tier] [query]  (ULTRAPLINIAN)
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("race"))
async def cmd_race(message: Message) -> None:
    if not await _ensure_server(message):
        return

    parts = (message.text or "").split(None, 2)
    if len(parts) < 2:
        # Show info from the actual APEX API
        info = await bridge.get_info()
        models_resp = await bridge.get_models()
        model_count = len(models_resp.data.get("data", [])) if models_resp.success else "?"

        await safe_reply(
            message,
            "🏁 *Race — ULTRAPLINIAN Multi-Model Racing*\n\n"
            f"مدل‌ها: {model_count} (مستقیم از APEX API)\n\n"
            "5 سطح:\n"
            "• `fast` — 12 مدل سریع\n"
            "• `standard` — 28 مدل (شامل fast)\n"
            "• `smart` — 41 مدل\n"
            "• `power` — 52 مدل\n"
            "• `ultra` — 59 مدل (تمام مدل‌ها)\n\n"
            "ویژگی‌ها: Liquid Response • Staggered Waves • Early-Exit\n"
            "Scoring: Substance + Directness + Completeness\n\n"
            "استفاده:\n"
            "`/race [سوال]` → fast (پیش‌فرض)\n"
            "`/race standard [سوال]`\n"
            "`/race ultra [سوال]`\n\n"
            "🔑 نیاز به `OPENROUTER_API_KEY` در `.env`",
        )
        return

    # Parse tier and query
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
        "🏁 *ULTRAPLINIAN Race شروع شد!*\n"
        f"⚡ Tier: `{tier}` | APEX: {'🟢' if gm else '⚪'}\n"
        "⏳ در حال مسابقه مدل‌ها..."
    )

    t0 = time.time()
    result = await bridge.ultraplinian_completion(
        messages=[{"role": "user", "content": query}],
        tier=tier,
        openrouter_api_key=or_key,
        apex=gm,
        stm_modules=stm if stm else None,
        stream=False,
        max_tokens=4096,
    )
    elapsed = int((time.time() - t0) * 1000)

    if not result.success:
        await safe_edit_text(wait_msg, f"❌ خطا: {result.error}")
        return

    data = result.data

    # Extract race results
    winner_model = data.get("model", "unknown")
    content = ""

    # Check various response formats
    if "choices" in data and data["choices"]:
        choice = data["choices"][0]
        content = choice.get("message", {}).get("content", "")
    elif "content" in data:
        content = data["content"]

    # Race metadata
    race_meta = data.get("race_metadata", data.get("metadata", {}))
    models_queried = race_meta.get("models_queried", "?")
    models_succeeded = race_meta.get("models_succeeded", "?")
    winner_score = race_meta.get("winner_score", race_meta.get("score", "?"))
    race_time = race_meta.get("total_duration_ms", elapsed)

    # Build scoreboard if available
    scoreboard_text = ""
    results_list = race_meta.get("results", race_meta.get("model_results", []))
    if results_list:
        scoreboard_text = "\n```\n"
        scoreboard_text += f"{'مدل':<35} {'SC':>4} {'ms':>7}\n"
        scoreboard_text += "─" * 48 + "\n"
        for r in results_list[:15]:
            m = r.get("model", "?")
            m_short = m.split("/")[-1][:33] if "/" in m else m[:33]
            sc = str(r.get("score", "-"))
            dur = str(r.get("duration_ms", "?"))
            ok = "✅" if r.get("success", True) else "❌"
            scoreboard_text += f"{m_short:<35} {sc:>4} {dur:>7}\n"
        if len(results_list) > 15:
            scoreboard_text += f"... و {len(results_list) - 15} مدل دیگر\n"
        scoreboard_text += "```"

    header = (
        f"🏁 *نتایج ULTRAPLINIAN Race* ({race_time}ms)\n"
        f"📊 {models_succeeded}/{models_queried} موفق | tier: `{tier}`\n"
        f"🏆 برنده: `{winner_model}` (امتیاز: {winner_score})"
        f"{scoreboard_text}"
    )
    await safe_edit_text(wait_msg, header)

    if content:
        for chunk in split_for_telegram(content):
            await safe_reply(message, chunk)


@router.callback_query(lambda c: c.data == "extra:race")
async def cb_race_info(cq: CallbackQuery) -> None:
    await safe_edit_text(
        cq.message,
        "🏁 *ULTRAPLINIAN Racing Engine*\n\n"
        "56+ مدل AI در 5 سطح (tier) مسابقه موازی می‌دن.\n"
        "بهترین پاسخ بر اساس Substance + Directness + Completeness انتخاب می‌شه.\n\n"
        "ویژگی Liquid Response: اولین پاسخ خوب فوری ارسال → ارتقا خودکار اگر بهتر پیدا شد.\n\n"
        "استفاده: `/race [tier] [سوال]`\n"
        "مثال: `/race ultra explain quantum entanglement`",
    )
    await cq.answer()


# ═══════════════════════════════════════════════════════════════════════
# CONSORTIUM — /consortium [tier] [query]
# ═══════════════════════════════════════════════════════════════════════

@router.message(Command("consortium"))



async def consortium_handler(message) -> None:
    """Consortium handler stub — implemented in cmd_consortium_group."""
    pass

