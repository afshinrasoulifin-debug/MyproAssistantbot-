
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/poster.py
─────────────────────────
🎨 Poster & Visual Design Studio:

  /poster    — Generate professional sale posters (12 templates)
  /mockup    — Product mockup on lifestyle backgrounds
  /logo      — AI logo generator with brand name overlay
  /moodboard — Generate 4-image mood board for brand identity
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
    working_model_key,
)
from arki_project.utils.poster_gen import TEMPLATES, generate_poster
from arki_project.utils.image_gen import generate_image, generate_design_variations
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args
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

router = Router(name="poster")

# Template labels for UI
_TPL_LABELS = {
    "sale": "🔴 فروش",
    "product": "🔵 محصول",
    "story": "🟣 استوری",
    "minimal": "⚪ مینیمال",
    "luxury": "✨ لوکس",
    "neon": "💜 نئون",
    "nature": "🌿 طبیعی",
    "gradient": "🎨 گرادیان",
    "vintage": "📜 وینتیج",
    "flash": "⚡ فوری",
    "carousel": "📱 کاروسل",
    "testimonial": "💬 ریویو",
}


# ═══════════════════════════════════════
# /poster — Professional Poster Generator (12 Templates)
# ═══════════════════════════════════════

@router.message(Command("poster"))
async def cmd_poster(message: Message) -> None:
    raw = extract_args(message.text or "", "/poster")

    if not raw:
        tpl_list = "\n".join(f"  {v} `{k}`" for k, v in _TPL_LABELS.items())
        await safe_reply(message, "🎨 *پوسترساز حرفه‌ای — ۱۲ قالب:*\n\n"
            f"*قالب‌های موجود:*\n{tpl_list}\n\n"
            "*فرمت:*\n"
            "`/poster [قالب] [نام محصول] | [قیمت] | [تخفیف] | [زیرنویس]`\n\n"
            "*مثال‌ها:*\n"
            "`/poster sale شمع معطر لاوندر | 350,000 | 30% | فقط تا آخر هفته!`\n"
            "`/poster luxury شمع سویا دکوری | 250,000`\n"
            "`/poster neon شمع‌های دست‌ساز | 180,000 | 50%`\n"
            "`/poster flash شمع وانیلی | 120,000 | 40%`\n"
            "`/poster vintage شمع بتنی | 200,000`\n"
            "`/poster testimonial عالی بود! عاشق بوی لاوندرش شدم | @arki_candles | | مریم`\n\n"
            "یا `/poster all شمع معطر | 200,000 | 20%` برای *همه ۱۲ قالب*")

        # Quick access buttons
        buttons = []
        row = []
        for k, v in _TPL_LABELS.items():
            row.append(InlineKeyboardButton(
                text=v, callback_data=f"poster_pick:{k}",
            ))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("👇 قالب رو انتخاب کن، بعد محصول بنویس:",
                             reply_markup=kb)
        return

    # Parse: /poster template product | price | discount | subtitle
    parts_main = raw.split(maxsplit=1)
    template = parts_main[0].lower()
    rest = parts_main[1] if len(parts_main) > 1 else ""

    # If template is not recognized, treat it as product name with default
    if template not in list(TEMPLATES.keys()) + ["all"]:
        rest = raw
        template = "sale"

    parts = [p.strip() for p in rest.split("|")]
    product = parts[0] if parts else "محصول"
    price = parts[1] if len(parts) > 1 else ""
    discount = parts[2] if len(parts) > 2 else ""
    subtitle = parts[3] if len(parts) > 3 else ""

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )

    if template == "all":
        status = await message.answer("🎨 دارم ۱۲ پوستر می‌سازم...")
        for tpl_name, tpl_label in _TPL_LABELS.items():
            try:
                img_bytes = generate_poster(
                    tpl_name, product, price, discount, subtitle,
                )
                photo = BufferedInputFile(img_bytes, filename=f"poster_{tpl_name}.png")
                await message.answer_photo(
                    photo=photo,
                    caption=f"🎨 {tpl_label} — *{product}*",
                    parse_mode="Markdown",
                )
            except HandlerError as exc:
                await message.answer(f"❌ خطا در {tpl_label}: {exc}")
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        return

    # Single template
    try:
        img_bytes = generate_poster(template, product, price, discount, subtitle)
        photo = BufferedInputFile(img_bytes, filename=f"poster_{template}.png")

        label = _TPL_LABELS.get(template, template)

        # Offer other templates in 3-column grid
        other_buttons = []
        row = []
        for k, v in _TPL_LABELS.items():
            if k == template:
                continue
            row.append(InlineKeyboardButton(
                text=v, callback_data=f"poster:{k}:{product}|{price}|{discount}",
            ))
            if len(row) == 3:
                other_buttons.append(row)
                row = []
        if row:
            other_buttons.append(row)
        # Add "All" button
        other_buttons.append([InlineKeyboardButton(
            text="📦 همه ۱۲ قالب",
            callback_data=f"poster:all:{product}|{price}|{discount}",
        )])
        other_kb = InlineKeyboardMarkup(inline_keyboard=other_buttons)

        await message.answer_photo(
            photo=photo,
            caption=f"🎨 {label} — *{product}*\n\n_قالب دیگه می‌خوای؟ 👇_",
            reply_markup=other_kb,
            parse_mode="Markdown",
        )
    except HandlerError as exc:
        logger.error("Poster gen failed: %s", exc)
        await message.answer(f"❌ {exc}")


@router.callback_query(F.data.startswith("poster_pick:"))
async def cb_poster_pick(callback: CallbackQuery) -> None:
    """User picked a template from the menu — tell them to type the command."""
    await callback.answer()
    tpl = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    label = _TPL_LABELS.get(tpl, tpl)
    await callback.message.answer(
        f"✅ قالب *{label}* انتخاب شد!\n\n"
        "الان بنویس:\n"
        f"`/poster {tpl} نام محصول | قیمت | تخفیف`",
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("poster:"))
async def cb_poster_template(callback: CallbackQuery) -> None:
    await callback.answer("🎨 در حال ساخت...")
    parts = callback.data.split(":", 2)  # type: ignore[union-attr]
    template = parts[1]
    data_parts = parts[2].split("|") if len(parts) > 2 else []

    product = data_parts[0] if data_parts else "محصول"
    price = data_parts[1] if len(data_parts) > 1 else ""
    discount = data_parts[2] if len(data_parts) > 2 else ""

    if template == "all":
        for tpl_name, tpl_label in _TPL_LABELS.items():
            try:
                img_bytes = generate_poster(tpl_name, product, price, discount)
                photo = BufferedInputFile(img_bytes, filename=f"poster_{tpl_name}.png")
                await callback.message.answer_photo(
                    photo=photo,
                    caption=f"🎨 {tpl_label} — *{product}*",
                    parse_mode="Markdown",
                )
            except HandlerError as e:
                logger.debug("Suppressed: %s", e)
        return

    try:
        img_bytes = generate_poster(template, product, price, discount)
        photo = BufferedInputFile(img_bytes, filename=f"poster_{template}.png")
        label = _TPL_LABELS.get(template, template)
        await callback.message.answer_photo(
            photo=photo,
            caption=f"🎨 {label} — *{product}*",
            parse_mode="Markdown",
        )
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]


# ═══════════════════════════════════════
# /mockup — Product Mockup Generator
# ═══════════════════════════════════════

@router.message(Command("mockup"))
async def cmd_mockup(message: Message) -> None:
    """Generate product mockup on lifestyle backgrounds."""
    raw = extract_args(message.text or "", "/mockup")

    if not raw:
        await safe_reply(message, "📸 *موکاپ محصول — تصویر حرفه‌ای:*\n\n"
            "`/mockup [محصول] | [استایل]`\n\n"
            "*استایل‌ها:*\n"
            "  `lifestyle` — محصول روی میز کنار قهوه/کتاب\n"
            "  `flatlay` — نمای بالا، چیدمان هنری\n"
            "  `minimal` — پس‌زمینه ساده سفید\n"
            "  `luxury` — محیط لوکس با نور طلایی\n"
            "  `cozy` — فضای دنج و گرم\n"
            "  `outdoor` — طبیعت و فضای باز\n\n"
            "*مثال:*\n"
            "`/mockup شمع بتنی | lifestyle`\n"
            "`/mockup شمع سویا لاوندر | luxury`\n"
            "`/mockup all شمع دست‌ساز` برای *۶ استایل*")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    style = parts[1].lower().strip() if len(parts) > 1 else "lifestyle"

    # Check for "all" prefix
    gen_all = False
    if product.lower().startswith("all "):
        gen_all = True
        product = product[4:].strip()

    styles = {
        "lifestyle": "product photography on wooden table, coffee cup and book nearby, warm natural lighting, cozy interior",
        "flatlay": "flat lay product photography, top-down view, artistic arrangement, marble surface, props around",
        "minimal": "product photography, clean white background, soft shadow, studio lighting, commercial",
        "luxury": "product photography in luxury setting, golden hour light, marble surface, silk fabric, premium feel",
        "cozy": "product in cozy living room, warm blanket, fireplace glow, hygge atmosphere, autumn vibes",
        "outdoor": "product in natural outdoor setting, garden, sunlight, flowers, organic feel",
    }

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )

    if gen_all:
        status = await message.answer("📸 دارم ۶ موکاپ می‌سازم...")
        for sname, sdesc in styles.items():
            try:
                prompt = f"{product}, {sdesc}, high resolution, 4K, professional advertising"
                img = await generate_image(prompt, enhance=False)
                photo = BufferedInputFile(img, filename=f"mockup_{sname}.png")
                await message.answer_photo(
                    photo=photo,
                    caption=f"📸 *{product}* — {sname}",
                    parse_mode="Markdown",
                )
            except HandlerError as exc:
                await message.answer(f"❌ خطا در {sname}: {exc}")
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        return

    sdesc = styles.get(style, styles["lifestyle"])
    status = await message.answer(f"📸 موکاپ *{style}* در حال ساخت...")

    try:
        prompt = f"{product}, {sdesc}, high resolution, 4K, professional advertising"
        img_bytes = await generate_image(prompt, enhance=False)
        photo = BufferedInputFile(img_bytes, filename=f"mockup_{style}.png")

        # Buttons for other styles
        buttons = []
        row = []
        style_emojis = {
            "lifestyle": "🏠", "flatlay": "📐", "minimal": "⚪",
            "luxury": "✨", "cozy": "🛋", "outdoor": "🌿",
        }
        for k in styles:
            if k == style:
                continue
            row.append(InlineKeyboardButton(
                text=f"{style_emojis.get(k,'')} {k}",
                callback_data=f"mockup:{k}:{product[:40]}",
            ))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer_photo(
            photo=photo,
            caption=f"📸 *{product}* — {style}\n_استایل دیگه؟ 👇_",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, f"❌ {exc}")


@router.callback_query(F.data.startswith("mockup:"))
async def cb_mockup(callback: CallbackQuery) -> None:
    await callback.answer("📸 در حال ساخت...")
    parts = callback.data.split(":", 2)  # type: ignore[union-attr]
    style = parts[1]
    product = parts[2] if len(parts) > 2 else "product"

    styles = {
        "lifestyle": "product photography on wooden table, coffee cup and book nearby, warm natural lighting",
        "flatlay": "flat lay product photography, top-down view, artistic arrangement, marble surface",
        "minimal": "product photography, clean white background, soft shadow, studio lighting",
        "luxury": "product photography in luxury setting, golden hour light, marble surface, silk fabric",
        "cozy": "product in cozy living room, warm blanket, fireplace glow, hygge atmosphere",
        "outdoor": "product in natural outdoor setting, garden, sunlight, flowers",
    }
    sdesc = styles.get(style, styles["lifestyle"])
    try:
        prompt = f"{product}, {sdesc}, high resolution, 4K, professional advertising"
        img = await generate_image(prompt, enhance=False)
        photo = BufferedInputFile(img, filename=f"mockup_{style}.png")
        await callback.message.answer_photo(
            photo=photo,
            caption=f"📸 *{product}* — {style}",
            parse_mode="Markdown",
        )
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]


# ═══════════════════════════════════════
# /logo — AI Logo Generator
# ═══════════════════════════════════════

@router.message(Command("logo"))
async def cmd_logo(message: Message) -> None:
    """Generate a logo with AI + text overlay."""
    raw = extract_args(message.text or "", "/logo")

    if not raw:
        await safe_reply(message, "🏷 *لوگوساز هوشمند:*\n\n"
            "`/logo [نام برند] | [استایل]`\n\n"
            "*استایل‌ها:*\n"
            "  `minimal` — مینیمال و تمیز\n"
            "  `modern` — مدرن و حرفه‌ای\n"
            "  `vintage` — کلاسیک و رترو\n"
            "  `luxury` — لوکس و طلایی\n"
            "  `3d` — سه‌بعدی\n\n"
            "*مثال:*\n"
            "`/logo Arki Candles | minimal`\n"
            "`/logo شمع ارکی | luxury`\n\n"
            "*نکته:* ۳ نسخه مختلف تولید می‌شه!")
        return

    parts = [p.strip() for p in raw.split("|")]
    brand_name = parts[0]
    style = parts[1].lower().strip() if len(parts) > 1 else "modern"

    style_prompts = {
        "minimal": "minimalist clean logo, simple geometric icon, flat design, white background",
        "modern": "modern professional logo, sleek design, gradient accent, dark background",
        "vintage": "vintage retro logo, hand-drawn feel, classic typography, aged paper texture",
        "luxury": "luxury premium logo, gold foil effect, black background, elegant serif",
        "3d": "3D rendered glossy logo, metallic finish, dark studio background, cinematic lighting",
    }

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )
    status = await message.answer("🏷 دارم ۳ نسخه لوگو می‌سازم...")

    try:
        sdesc = style_prompts.get(style, style_prompts["modern"])
        prompt = f"logo design for brand '{brand_name}', {sdesc}, professional graphic design, 8K quality"
        images = await generate_design_variations(prompt, count=3)
        for i, img_bytes in enumerate(images, 1):
            photo = BufferedInputFile(img_bytes, filename=f"logo_{style}_{i}.png")
            await message.answer_photo(
                photo=photo,
                caption=f"🏷 لوگو {i}/3 — *{brand_name}* ({style})",
                parse_mode="Markdown",
            )
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, f"❌ {exc}")


# ═══════════════════════════════════════
# /moodboard — Brand Mood Board Generator
# ═══════════════════════════════════════

@router.message(Command("moodboard"))
async def cmd_moodboard(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate a 4-image mood board for brand identity."""
    raw = extract_args(message.text or "", "/moodboard")

    if not raw:
        await safe_reply(message, "🎭 *مودبورد برند — هویت بصری:*\n\n"
            "`/moodboard [نام برند یا محصول] | [حس و حال]`\n\n"
            "*مثال:*\n"
            "`/moodboard شمع دست‌ساز | دنج و گرم`\n"
            "`/moodboard Arki Candles | luxury minimal`\n"
            "`/moodboard شمع سویا | طبیعی و ارگانیک`\n\n"
            "۴ تصویر + تحلیل هویت بصری تولید می‌شه!")
        return

    parts = [p.strip() for p in raw.split("|")]
    brand = parts[0]
    mood = parts[1] if len(parts) > 1 else "warm, cozy, premium"

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )
    status = await message.answer("🎭 دارم مودبورد می‌سازم...")

    try:
        # Generate 4 different mood images
        moods = [
            f"{brand}, {mood}, color palette swatch, flat design, graphic design mood board",
            f"{brand}, {mood}, product styling photography, lifestyle, editorial",
            f"{brand}, {mood}, texture and material close-up, artisan, detailed",
            f"{brand}, {mood}, packaging design concept, premium, minimalist",
        ]

        for i, prompt in enumerate(moods, 1):
            try:
                img = await generate_image(prompt, enhance=False, seed=i*100+42)
                photo = BufferedInputFile(img, filename=f"mood_{i}.png")
                labels = ["🎨 پالت رنگ", "📸 استایل محصول", "🧶 تکسچر و متریال", "📦 بسته‌بندی"]
                await message.answer_photo(
                    photo=photo,
                    caption=f"{labels[i-1]} — *{brand}*",
                    parse_mode="Markdown",
                )
            except HandlerError as e:
                logger.debug("Suppressed: %s", e)

        # AI analysis of brand identity
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        import time as _t; _t0 = _t.time()
        analysis = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt("You are a brand strategist. Write in Persian. Be specific and actionable.", user_text=message.text or "", user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": (
                    f"Based on the brand '{brand}' with mood '{mood}', create a brief brand identity guide:\n"
                    "1. 🎨 Color Palette: 5 specific hex colors with Persian names\n"
                    "2. ✏️ Typography: Font recommendations (EN + FA)\n"
                    "3. 📸 Photography Style: Specific rules\n"
                    "4. 💬 Brand Voice: Tone and language style\n"
                    "5. 📱 Social Media: Visual consistency rules"
                )},
            ],
            model_key=mk, temperature=0.8, max_tokens=16384,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:300], analysis[:500] if analysis else "", "poster", duration_s=_t.time()-_t0)
        for chunk in split_for_telegram(f"🎭 *هویت بصری — {brand}:*\n\n{analysis}"):
            await safe_reply(message, chunk)

        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, f"❌ {exc}")


# ═══════════════════════════════════════


