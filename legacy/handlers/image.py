
from __future__ import annotations
"""
tg_bot/handlers/image.py
────────────────────────
Image & Visual Design Hub:

  /image       — AI image generation (Flux model)
  /design      — 3 design variations from a prompt
  /banner      — Social media banner generator (6 sizes)
  /infographic — AI-powered infographic generator
  /photoedit   — Product photo enhancement prompts + tips
"""


import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.image_gen import generate_image, generate_design_variations
from arki_project.utils.token_tracker import track_tokens as _track_tokens
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args, brand_ctx
from arki_project.utils.v7_core import (
    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)
# v9.2: Media storage integration

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

router = Router(name="image")


@router.message(Command("image"))
async def cmd_image(message: Message) -> None:
    """Generate a single image from a text prompt."""
    prompt = extract_args(message.text or "", "/image")
    if not prompt:
        await safe_reply(message, "🎨 *تولید تصویر با AI:*\n\n"
            "Usage: `/image [توضیح تصویر]`\n\n"
            "*مثال‌ها:*\n"
            "`/image a sunset over mountains`\n"
            "`/image شمع دست‌ساز روی میز چوبی`\n"
            "`/image لوگو مینیمال شمع`\n"
            "`/image product photo of handmade candle, studio lighting`\n\n"
            "_AI خودکار پرامپت رو بهینه‌سازی می‌کنه!_")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
    )
    status = await message.answer("🎨 دارم تصویر می‌سازم...")

    try:
        image_bytes = await generate_image(prompt)
        await _track_tokens(message.from_user.id if message.from_user else 0, prompt, extra_tokens=1000)  # v9.7: Image gen tokens
        photo = BufferedInputFile(image_bytes, filename="generated.png")

        # Offer variations button
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 ۳ نسخه دیگه", callback_data=f"img_var:{prompt[:60]}"),
                InlineKeyboardButton(text="📐 بنر", callback_data=f"img_banner:{prompt[:50]}"),
            ],
        ])
        await message.answer_photo(
            photo=photo,
            caption=f"🎨 *{prompt[:100]}*",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as e:
        logger.error("Image generation failed: %s", e)
        await safe_edit_text(status, f"⚠️ خطا:\n`{str(e)[:200]}`")


@router.callback_query(F.data.startswith("img_var:"))
async def cb_img_variations(callback: CallbackQuery) -> None:
    await callback.answer("🎨 در حال ساخت ۳ نسخه...")
    prompt = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    try:
        images = await generate_design_variations(prompt, count=3)
        for i, img_bytes in enumerate(images, 1):
            photo = BufferedInputFile(img_bytes, filename=f"variation_{i}.png")
            await callback.message.answer_photo(
                photo=photo,
                caption=f"🎨 نسخه {i}/3",
                parse_mode="Markdown",
            )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]


@router.message(Command("design"))
async def cmd_design(message: Message) -> None:
    """Generate 3 design variations from a prompt."""
    prompt = extract_args(message.text or "", "/design")
    if not prompt:
        await safe_reply(message, "🎨 *Design Mode — ۳ نسخه مختلف:*\n\n"
            "Usage: `/design [توضیح طرح]`\n\n"
            "*مثال‌ها:*\n"
            "`/design modern candle shop logo`\n"
            "`/design پوستر تبلیغاتی شمع`\n"
            "`/design instagram story template autumn candles`\n\n"
            "_۳ نسخه متفاوت تولید می‌شه!_")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
    )
    status = await message.answer("🎨 دارم ۳ طرح مختلف می‌سازم...")

    try:
        images = await generate_design_variations(prompt, count=3)
        for i, img_bytes in enumerate(images, 1):
            photo = BufferedInputFile(img_bytes, filename=f"design_{i}.png")
            await message.answer_photo(
                photo=photo,
                caption=f"🎨 نسخه {i}/3: *{prompt[:80]}*",
                parse_mode="Markdown",
            )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as e:
        logger.error("Design generation failed: %s", e)
        await safe_edit_text(status, f"⚠️ خطا:\n`{str(e)[:200]}`")


# ═══════════════════════════════════════
# /banner — Social Media Banner Generator
# ═══════════════════════════════════════

_BANNER_SIZES = {
    "instagram": (1080, 1080, "📱 اینستا پست"),
    "story": (1080, 1920, "📱 استوری"),
    "facebook": (1200, 630, "📘 فیسبوک کاور"),
    "twitter": (1500, 500, "🐦 توییتر هدر"),
    "youtube": (2560, 1440, "🎬 یوتیوب بنر"),
    "linkedin": (1584, 396, "💼 لینکدین"),
}


@router.message(Command("banner"))
async def cmd_banner(message: Message) -> None:
    """Generate banners in multiple social media sizes."""
    raw = extract_args(message.text or "", "/banner")

    if not raw:
        sizes_text = "\n".join(
            f"  `{k}` — {v[2]} ({v[0]}×{v[1]})"
            for k, v in _BANNER_SIZES.items()
        )
        await safe_reply(message, "🖼 *بنرساز چند سایز:*\n\n"
            "`/banner [موضوع] | [سایز]`\n\n"
            f"*سایزها:*\n{sizes_text}\n\n"
            "*مثال:*\n"
            "`/banner شمع دست‌ساز ارکی | instagram`\n"
            "`/banner Arki Candles holiday sale | story`\n"
            "`/banner all شمع ارکی` برای *همه ۶ سایز*")
        return

    parts = [p.strip() for p in raw.split("|")]
    topic = parts[0]
    size_key = parts[1].lower().strip() if len(parts) > 1 else "instagram"

    gen_all = topic.lower().startswith("all ")
    if gen_all:
        topic = topic[4:].strip()

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )

    if gen_all:
        status = await message.answer("🖼 دارم ۶ بنر می‌سازم...")
        for sk, (bw, bh, label) in _BANNER_SIZES.items():
            try:
                prompt = (
                    f"Professional {sk} banner for '{topic}', clean modern design, "
                    "beautiful gradient, negative space for text, commercial quality"
                )
                img = await generate_image(prompt, width=bw, height=bh, enhance=False)
                photo = BufferedInputFile(img, filename=f"banner_{sk}.png")
                await message.answer_photo(
                    photo=photo,
                    caption=f"🖼 {label} ({bw}×{bh}) — *{topic}*",
                    parse_mode="Markdown",
                )
            except Exception as exc:
                await message.answer(f"❌ {label}: {exc}")
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        return

    bw, bh, label = _BANNER_SIZES.get(size_key, _BANNER_SIZES["instagram"])
    status = await message.answer(f"🖼 ساخت بنر {label}...")

    try:
        prompt = (
            f"Professional {size_key} banner for '{topic}', clean modern design, "
            "beautiful gradient, negative space for text, commercial quality"
        )
        img = await generate_image(prompt, width=bw, height=bh, enhance=False)
        photo = BufferedInputFile(img, filename=f"banner_{size_key}.png")

        # Other size buttons
        buttons = []
        row = []
        for k, (_, _, lbl) in _BANNER_SIZES.items():
            if k == size_key:
                continue
            row.append(InlineKeyboardButton(
                text=lbl.split()[0] + " " + k,
                callback_data=f"banner:{k}:{topic[:40]}",
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer_photo(
            photo=photo,
            caption=f"🖼 {label} ({bw}×{bh}) — *{topic}*\n_سایز دیگه؟ 👇_",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, f"❌ {exc}")


@router.callback_query(F.data.startswith("banner:"))
async def cb_banner(callback: CallbackQuery) -> None:
    await callback.answer("🖼 در حال ساخت...")
    parts = callback.data.split(":", 2)  # type: ignore[union-attr]
    size_key = parts[1]
    topic = parts[2] if len(parts) > 2 else "product"
    bw, bh, label = _BANNER_SIZES.get(size_key, _BANNER_SIZES["instagram"])
    try:
        prompt = (
            f"Professional {size_key} banner for '{topic}', clean modern design, "
            "beautiful gradient, commercial quality"
        )
        img = await generate_image(prompt, width=bw, height=bh, enhance=False)
        photo = BufferedInputFile(img, filename=f"banner_{size_key}.png")
        await callback.message.answer_photo(
            photo=photo,
            caption=f"🖼 {label} ({bw}×{bh}) — *{topic}*",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]


@router.callback_query(F.data.startswith("img_banner:"))
async def cb_img_to_banner(callback: CallbackQuery) -> None:
    await callback.answer("🖼 ساخت بنر اینستا...")
    prompt = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    try:
        img = await generate_image(prompt, width=1080, height=1080, enhance=True)
        photo = BufferedInputFile(img, filename="banner_ig.png")
        await callback.message.answer_photo(
            photo=photo,
            caption="🖼 *بنر اینستاگرام*",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]


# ═══════════════════════════════════════
# /infographic — AI Infographic Generator
# ═══════════════════════════════════════

@router.message(Command("infographic"))
async def cmd_infographic(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate infographic content with AI + visual."""
    raw = extract_args(message.text or "", "/infographic")

    if not raw:
        await safe_reply(message, "📊 *اینفوگرافیک‌ساز AI:*\n\n"
            "`/infographic [موضوع]`\n\n"
            "*مثال:*\n"
            "`/infographic 5 فایده شمع سویا`\n"
            "`/infographic مراحل ساخت شمع دست‌ساز`\n"
            "`/infographic مقایسه شمع سویا و پارافین`\n\n"
            "تصویر + محتوای آماده پست تولید می‌شه!")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer("📊 دارم اینفوگرافیک می‌سازم...")

    try:
        # Step 1: Generate content with AI
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        import time as _t; _t0 = _t.time()
        content = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt(
                    "You are an infographic content specialist. Write in Persian. "
                    "Create clear, concise infographic content with: "
                    "- A catchy title, - 5-7 key points with icons/emojis, "
                    "- Each point as 1 short sentence, - A concluding CTA. "
                    "Format it beautifully for Telegram with emojis.",
                    user_text=message.text or "", user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": f"Create infographic content about: {raw}\n{brand_ctx(message.chat.id)}"},
            ],
            model_key=mk, temperature=0.8, max_tokens=16384,
        )

        # Step 2: Generate a visual
        img_prompt = (
            f"Clean infographic design about {raw}, "
            "modern flat illustration, icons, data visualization, "
            "pastel colors, professional, 4K"
        )
        try:
            img = await generate_image(img_prompt, enhance=False, width=1080, height=1350)
            photo = BufferedInputFile(img, filename="infographic.png")
            await message.answer_photo(
                photo=photo,
                caption=f"📊 *اینفوگرافیک — {raw[:60]}*",
                parse_mode="Markdown",
            )
        except Exception as _e:
            logger.debug("Suppressed: %s", _e)  # Image failed but text content still works

        # Step 3: Send content
        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:300], content[:500] if content else "", "image", duration_s=_t.time()-_t0)
        for chunk in split_for_telegram(f"📊 *اینفوگرافیک — {raw}:*\n\n{content}"):
            await safe_reply(message, chunk)

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /photoedit — Product Photo Enhancement Tips
# ═══════════════════════════════════════

@router.message(Command("photoedit"))
async def cmd_photoedit(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Get AI-powered product photo enhancement tips."""
    raw = extract_args(message.text or "", "/photoedit")

    if not raw:
        await safe_reply(message, "📷 *مشاور عکاسی محصول:*\n\n"
            "`/photoedit [نوع محصول] | [مشکل]`\n\n"
            "*مثال:*\n"
            "`/photoedit شمع | نور بد`\n"
            "`/photoedit candle | background looks messy`\n"
            "`/photoedit شمع بتنی | عکس حرفه‌ای با گوشی`\n\n"
            "نکات حرفه‌ای + تنظیمات دقیق دوربین/موبایل!")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        tips = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a professional product photographer and photo editor. "
                    "Write in Persian. Give SPECIFIC, ACTIONABLE tips including: "
                    "- Exact phone camera settings (ISO, exposure), "
                    "- Lightroom/Snapseed editing steps, "
                    "- Composition rules, "
                    "- DIY lighting setups, "
                    "- Background ideas with items they already have at home. "
                    "Be practical for someone using just a phone."
                )},
                {"role": "user", "content": f"Product photo tips for: {raw}"},
            ],
            model_key=mk, temperature=0.7, max_tokens=16384,
        )

        for chunk in split_for_telegram(f"📷 *نکات عکاسی — {raw}:*\n\n{tips}"):
            await safe_reply(message, chunk)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


