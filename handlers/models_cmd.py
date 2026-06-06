
from __future__ import annotations
from arki_project.exceptions import AIProviderError, ProviderAuthError
"""
tg_bot/handlers/models_cmd.py
─────────────────────────────
Commands for model/persona/settings management:

  /model    — pick from 79 models (inline keyboard)
  /persona  — pick from 10 personas (inline keyboard)
  /settings — view current config
  /autotune — toggle AutoTune
"""


import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    DEFAULT_MODEL,
    APEX_TIERS,
    MODELS,
    PERSONAS,
    TTS_VOICES,
    UNCENSORED_KEYS,
    get_apex_tier,
    get_free_badge,
    get_free_label,
    get_model,
)
from arki_project.utils.safe_send import safe_edit_text, safe_reply

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]


logger = logging.getLogger(__name__)
router = Router(name="models_cmd")

VER = "7.1"  # Enhanced modular version


# ═══════════ /model ═══════════

@router.message(Command("model"))
async def cmd_model(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    cfg = await ai_client.get_user_config(user_id)
    current = cfg["model"]
    cur_model = MODELS.get(current, MODELS[DEFAULT_MODEL])
    cur_label = f"فعلی: {cur_model.emoji} {cur_model.name}"

    buttons: list[list[InlineKeyboardButton]] = []

    # Provider groups
    gemini_n = sum(1 for m in MODELS.values() if m.provider == "gemini")
    groq_n = sum(1 for m in MODELS.values() if m.provider == "groq")
    groq_ok = bool(settings.groq_api_key)

    buttons.append([
        InlineKeyboardButton(text=f"🔵 Gemini ({gemini_n})", callback_data="mgrp:gemini"),
        InlineKeyboardButton(text=f"🟠 Groq ({groq_n}){'' if groq_ok else ' 🔒'}", callback_data="mgrp:groq"),
    ])

    # APEX tier groups
    for tier_name, tier_data in APEX_TIERS.items():
        n = len(tier_data["models"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{tier_data['emoji']} APEX {tier_data['label']} ({n})",
                callback_data=f"mgrp:g0d_{tier_name}",
            ),
        ])

    # Claude Ultra group
    try:
        from arki_project.utils.models_core import CLAUDE_ULTRA_MODELS
        cu_n = len(CLAUDE_ULTRA_MODELS)
        buttons.append([
            InlineKeyboardButton(
                text=f"🟣 Claude Ultra ({cu_n})",
                callback_data="mgrp:claude_ultra",
            ),
        ])
    except Exception:
        pass

    # Uncensored shortcut
    buttons.append([
        InlineKeyboardButton(
            text=f"🔓 بدون فیلتر ({len(UNCENSORED_KEYS)})",
            callback_data="mgrp:uncensored",
        ),
    ])

    await safe_reply(
        message,
        f"🧠 *انتخاب مدل — {len(MODELS)} مدل*\n\n{cur_label}\n\nیک گروه انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


# ═══════════ /persona ═══════════

@router.message(Command("persona"))
async def cmd_persona(
    message: Message, ai_client: AIClient,
) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    cfg = await ai_client.get_user_config(user_id)
    current = cfg["persona"]

    buttons = [
        [InlineKeyboardButton(
            text=f"{p.name}{' ✓' if k == current else ''}",
            callback_data=f"p:{k}",
        )]
        for k, p in PERSONAS.items()
    ]

    await safe_reply(message, "🎭 *انتخاب شخصیت:*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


# ═══════════ /settings ═══════════

@router.message(Command("settings"))
async def cmd_settings(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    cfg = await ai_client.get_user_config(user_id)

    m = get_model(cfg["model"])
    p = PERSONAS.get(cfg["persona"], PERSONAS["assistant"])

    n = sum(
        1 for v in MODELS.values()
        if (v.provider == "gemini" and settings.ai_api_key)
        or (v.provider == "groq" and settings.groq_api_key)
    )

    gem_ok = "✅" if settings.ai_api_key else "❌"
    groq_ok = "✅" if settings.groq_api_key else "❌"

    text = (
        f"⚙️ *Arki Engine v{VER} — تنظیمات:*\n\n"
        f"🧠 مدل: *{m.emoji} {m.name}* ({m.ctx})\n"
        f"🎭 شخصیت: *{p.name}*\n"
        f"🗣 صدا: *{cfg['voice']}*\n"
        f"🎛 AutoTune: *{'✅' if cfg['autotune'] else '❌'}*\n"
        f"💬 حافظه: {settings.ai_max_history} پیام\n"
        f"🤖 تعداد مدل: *{n}*\n"
        "🔄 Retry: *2x + Fallback*\n"
        "🎨 عکس: *Flux (Pollinations)*\n\n"
        f"{gem_ok} Gemini | {groq_ok} Groq | ✅ Pollinations"
    )
    await safe_reply(message, text)


# ═══════════ /autotune ═══════════

@router.message(Command("autotune"))
async def cmd_autotune(
    message: Message, ai_client: AIClient,
) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    cfg = await ai_client.get_user_config(user_id)
    new_val = not cfg["autotune"]
    await ai_client.set_user_config(user_id, "autotune", new_val)
    await safe_reply(message, f"🎛 AutoTune: *{'✅ فعال' if new_val else '❌ غیرفعال'}*")


# ═══════════ Callbacks ═══════════

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("mgrp:"))
async def cb_model_group(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    """Expand a model group to show individual models."""
    await callback.answer()
    group = callback.data[5:]  # Strip "mgrp:" prefix
    user_id = callback.from_user.id
    cfg = await ai_client.get_user_config(user_id)
    current = cfg["model"]

    buttons: list[list[InlineKeyboardButton]] = []

    if group == "gemini":
        for key, m in MODELS.items():
            if m.provider != "gemini":
                continue
            ok = bool(settings.ai_api_key)
            check = " ✓" if key == current else ""
            label = f"{m.emoji} {m.name}{check}" if ok else f"🔒 {m.name}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"m:{key}")])
        title = "🔵 *Gemini*"

    elif group == "groq":
        for key, m in MODELS.items():
            if m.provider != "groq":
                continue
            ok = bool(settings.groq_api_key)
            check = " ✓" if key == current else ""
            label = f"{m.emoji} {m.name}{check}" if ok else f"🔒 {m.name}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"m:{key}")])
        title = "🟠 *Groq*"

    elif group == "uncensored":
        for key in UNCENSORED_KEYS:
            m = MODELS.get(key)
            if not m:
                continue
            check = " ✓" if key == current else ""
            label = f"{m.emoji} {m.name}{check}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"m:{key}")])
        title = "🔓 *بدون فیلتر — Uncensored*"

    elif group == "claude_ultra":
        try:
            from arki_project.utils.models_core import CLAUDE_ULTRA_MODELS
            for key, m in CLAUDE_ULTRA_MODELS.items():
                check = " ✓" if key == current else ""
                label = f"{m.emoji} {m.name}{check}"
                buttons.append([InlineKeyboardButton(text=label, callback_data=f"m:{key}")])
            title = "🟣 *Claude Ultra* — Anthropic AI (رایگان)\n💎=Opus  🟣=Sonnet  ⚡=Haiku"
        except Exception:
            title = "🟣 *Claude Ultra* — خطا در بارگذاری"

    elif group.startswith("g0d_"):
        tier_name = group[4:]  # e.g. "fast", "standard", "pro", etc.
        tier_data = APEX_TIERS.get(tier_name, {})
        tier_models = tier_data.get("models", {})
        or_key = bool(settings.openrouter_api_key) if hasattr(settings, 'openrouter_api_key') else True
        for key, m in tier_models.items():
            check = " ✓" if key == current else ""
            badge = get_free_badge(key)
            label = f"{badge} {m.name}{check}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"m:{key}")])
        emoji = tier_data.get("emoji", "🧬")
        label = tier_data.get("label", tier_name)
        title = f"{emoji} *APEX {label}*\n🟢=رایگان مستقیم  ⚡=جایگزین رایگان"
    else:
        return

    # Add back button
    buttons.append([InlineKeyboardButton(text="« بازگشت به گروه‌ها", callback_data="mgrp:back")])

    await safe_edit_text(
        callback.message,
        f"{title}\n\nیک مدل انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "mgrp:back")
async def cb_model_group_back(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    """Go back to model group list."""
    await callback.answer()
    user_id = callback.from_user.id
    cfg = await ai_client.get_user_config(user_id)
    current = cfg["model"]
    cur_model = MODELS.get(current, MODELS[DEFAULT_MODEL])
    cur_label = f"فعلی: {cur_model.emoji} {cur_model.name}"

    buttons: list[list[InlineKeyboardButton]] = []

    gemini_n = sum(1 for m in MODELS.values() if m.provider == "gemini")
    groq_n = sum(1 for m in MODELS.values() if m.provider == "groq")
    groq_ok = bool(settings.groq_api_key)

    buttons.append([
        InlineKeyboardButton(text=f"🔵 Gemini ({gemini_n})", callback_data="mgrp:gemini"),
        InlineKeyboardButton(text=f"🟠 Groq ({groq_n}){'' if groq_ok else ' 🔒'}", callback_data="mgrp:groq"),
    ])

    for tier_name, tier_data in APEX_TIERS.items():
        n = len(tier_data["models"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{tier_data['emoji']} APEX {tier_data['label']} ({n})",
                callback_data=f"mgrp:g0d_{tier_name}",
            ),
        ])

    # Claude Ultra group
    try:
        from arki_project.utils.models_core import CLAUDE_ULTRA_MODELS
        cu_n = len(CLAUDE_ULTRA_MODELS)
        buttons.append([
            InlineKeyboardButton(
                text=f"🟣 Claude Ultra ({cu_n})",
                callback_data="mgrp:claude_ultra",
            ),
        ])
    except Exception:
        pass

    # Uncensored shortcut
    buttons.append([
        InlineKeyboardButton(
            text=f"🔓 بدون فیلتر ({len(UNCENSORED_KEYS)})",
            callback_data="mgrp:uncensored",
        ),
    ])

    await safe_edit_text(
        callback.message,
        f"🧠 *انتخاب مدل — {len(MODELS)} مدل*\n\n{cur_label}\n\nیک گروه انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("m:"))
async def cb_model_select(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    await callback.answer()
    key = callback.data[2:]  # type: ignore[index]
    if key not in MODELS:
        return

    m = MODELS[key]
    # v25.0 AUTONOMOUS: All providers available via FreeAccessRouter.
    # No key checks — free routes, cross-provider fallback, and
    # Smart Fallback chains handle everything autonomously.

    user_id = callback.from_user.id
    await ai_client.set_user_config(user_id, "model", key)
    tier_info = ""
    tier = get_apex_tier(key)
    if tier:
        tier_info = f"\n🧬 APEX {tier.upper()}"
    free_info = get_free_label(key)
    try:
        await safe_edit_text(callback.message, # type: ignore[union-attr]
            f"✅ *{m.emoji} {m.name}*\n_{m.desc}_\n_{m.ctx}_{tier_info}\n{free_info}")
    except AIProviderError as e:
        logger.debug("Suppressed: %s", e)


@router.callback_query(F.data.startswith("p:"))
async def cb_persona_select(
    callback: CallbackQuery, ai_client: AIClient,
) -> None:
    await callback.answer()
    key = callback.data[2:]  # type: ignore[index]
    if key not in PERSONAS:
        return
    user_id = callback.from_user.id
    await ai_client.set_user_config(user_id, "persona", key)
    try:
        await safe_edit_text(callback.message, # type: ignore[union-attr]
            f"✅ *{PERSONAS[key].name}*")
    except ProviderAuthError as e:
        logger.debug("Suppressed: %s", e)


@router.callback_query(F.data.startswith("v:"))
async def cb_voice_select(
    callback: CallbackQuery, ai_client: AIClient,
) -> None:
    await callback.answer()
    voice = callback.data[2:]  # type: ignore[index]
    if voice not in TTS_VOICES:
        return
    user_id = callback.from_user.id
    await ai_client.set_user_config(user_id, "voice", voice)
    try:
        await safe_edit_text(callback.message, # type: ignore[union-attr]
            f"✅ صدا: *{voice}*")
    except AIProviderError as e:
        logger.debug("Suppressed: %s", e)


