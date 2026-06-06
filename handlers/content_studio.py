
from __future__ import annotations
"""
tg_bot/handlers/content_studio.py
──────────────────────────────────
🎬 Content Production Studio — Complete content creation system for sales.

Commands:
  /studio    — Main menu: all content tools
  /brand     — Set up brand kit (name, tagline, style)
  /catalog   — Product catalog + quick content gen
  /content   — All-in-one: caption + hashtags + poster + listing
  /caption   — AI caption generator (5 variants × 3 platforms)
  /hashtag   — Smart hashtag research & generator
  /batch     — Generate a week of content at once
  /story     — Reels/Story script generator
  /abtest    — A/B test caption variants
"""


import json
import logging

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════

try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10: CSPRNG
except ImportError:
    import random
import urllib.parse

import httpx
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
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import brand_ctx, extract_args
from arki_project.utils.data_store import store
from arki_project.utils.v7_core import (
    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)

_brands: dict = {}  # Brand storage: user_id -> {brand_name: brand_data}
_MAX_BRANDS = 5000  # Prevent unbounded growth
_brands_access: dict = {}  # user_id -> last_access_time
# v9.3: Service layer
# v9.2: Task queue for heavy operations

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]


# v9.1: Marketing engine integration
try:
    from arki_project.utils.v7_core import get_marketing_engine
    _marketing = get_marketing_engine()
except Exception as exc:
    logger.error("Error in handler: %s", exc)
    _marketing = None
router = Router(name="content_studio")


@router.message(Command("studio"))
async def cmd_studio(message: Message) -> None:
    brand = store.get_brand(message.chat.id)
    brand_status = f"✅ `{brand['name']}`" if brand else "❌ تنظیم نشده"
    catalog = store.get_catalog(message.chat.id)
    cat_count = len(catalog)

    await safe_reply(message, "🎬 *استودیوی تولید محتوا — Content Studio*\n\n"
        f"🏷 برند: {brand_status}\n"
        f"📦 محصولات: {cat_count} عدد\n\n"
        "━━━━━━━━━━━━━━━\n"
        "⚙️ *تنظیمات:*\n"
        "🏷 `/brand` تنظیم برند (اسم، سبک، رنگ‌ها)\n"
        "📦 `/catalog` کاتالوگ محصولات\n\n"
        "🎨 *تولید محتوا:*\n"
        "🔥 `/content` همه‌چیز یکجا (کپشن+هشتگ+پوستر+آگهی)\n"
        "✍️ `/caption` کپشن‌ساز (۵ نسخه × ۳ پلتفرم)\n"
        "🏷 `/hashtag` تحقیق هشتگ هوشمند\n"
        "📅 `/batch` محتوای یک هفته یکجا\n"
        "🎬 `/story` اسکریپت استوری/ریلز\n"
        "🧪 `/abtest` تست A/B کپشن\n\n"
        "🖼 *تصویری:*\n"
        "📸 `/photopro` عکس محصول حرفه‌ای\n"
        "🎨 `/poster` پوستر فروش (۴ قالب)\n\n"
        "📊 *فروش:*\n"
        "📋 `/listing` آگهی Etsy/Tori.fi/Instagram\n"
        "🔍 `/analyze` آنالیز رقبا Etsy")


# ═══════════════════════════════════════
# /brand — Brand Kit Setup
# ═══════════════════════════════════════

@router.message(Command("brand"))
async def cmd_brand(message: Message) -> None:
    raw = extract_args(message.text or "", "/brand")

    if not raw:
        brand = store.get_brand(message.chat.id)
        if brand:
            await safe_reply(message, "🏷 *برند فعلی:*\n\n"
                f"📛 نام: *{brand['name']}*\n"
                f"✨ تگ‌لاین: _{brand.get('tagline', '-')}_\n"
                f"🎨 سبک: {brand.get('style', 'minimal')}\n"
                f"🗣 لحن: {brand.get('tone', 'professional')}\n"
                f"🌍 زبان‌ها: {brand.get('languages', 'EN, FI')}\n\n"
                "*ویرایش:*\n"
                "`/brand [نام] | [تگ‌لاین] | [سبک] | [لحن] | [زبان‌ها]`\n\n"
                "*سبک‌ها:* minimal, luxury, natural, modern, rustic\n"
                "*لحن:* professional, friendly, poetic, bold\n\n"
                "*مثال:*\n"
                "`/brand Arki Candles | Raw. Natural. Timeless. | minimal | poetic | EN, FI`")
        else:
            await safe_reply(message, "🏷 *تنظیم برند:*\n\n"
                "`/brand [نام] | [تگ‌لاین] | [سبک] | [لحن] | [زبان‌ها]`\n\n"
                "*مثال:*\n"
                "`/brand Arki Candles | Raw. Natural. Timeless. | minimal | poetic | EN, FI`\n\n"
                "*سبک‌ها:* `minimal` `luxury` `natural` `modern` `rustic`\n"
                "*لحن:* `professional` `friendly` `poetic` `bold`\n\n"
                "_اول برندت رو تنظیم کن تا محتوا هماهنگ باشه_")
        return

    parts = [p.strip() for p in raw.split("|")]
    brand = {
        "name": parts[0],
        "tagline": parts[1] if len(parts) > 1 else "",
        "style": parts[2] if len(parts) > 2 else "minimal",
        "tone": parts[3] if len(parts) > 3 else "professional",
        "languages": parts[4] if len(parts) > 4 else "EN, FI",
    }
    await store.set_brand(message.chat.id, brand)

    await safe_reply(message, "✅ *برند ذخیره شد:*\n\n"
        f"📛 {brand['name']}\n"
        f"✨ {brand['tagline']}\n"
        f"🎨 {brand['style']} | 🗣 {brand['tone']}\n"
        f"🌍 {brand['languages']}\n\n"
        "_حالا همه محتوا با این سبک ساخته می‌شه!_")


# ═══════════════════════════════════════
# /catalog — Product Catalog
# ═══════════════════════════════════════

@router.message(Command("catalog"))
async def cmd_catalog(message: Message) -> None:
    raw = extract_args(message.text or "", "/catalog")
    catalog = store.get_catalog(message.chat.id)

    if not raw:
        if not catalog:
            await safe_reply(message, "📦 *کاتالوگ محصولات:*\n\n"
                "_هنوز محصولی اضافه نشده!_\n\n"
                "*اضافه کردن:*\n"
                "`/catalog add [نام] | [قیمت €] | [توضیحات] | [دسته‌بندی]`\n\n"
                "*مثال‌ها:*\n"
                "`/catalog add Concrete Candle Small | 25 | Soy wax, lavender, 20h | candle`\n"
                "`/catalog add Stone Candle Large | 45 | Soy wax, vanilla, 50h | candle`\n"
                "`/catalog add Concrete Planter | 35 | Handmade, minimalist | decor`\n\n"
                "*دیگه:*\n"
                "`/catalog list` — لیست همه\n"
                "`/catalog remove [شماره]` — حذف\n"
                "`/catalog genall` — تولید محتوا *برای همه*")
            return

        # Show catalog
        lines = []
        for i, item in enumerate(catalog, 1):
            lines.append(
                f"*{i}.* {item['name']} — €{item['price']}\n"
                f"    _{item.get('desc', '')}_"
            )
        text = "\n\n".join(lines)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🔥 محتوا برای {item['name'][:20]}",
                callback_data=f"catgen:{i-1}",
            )]
            for i, item in enumerate(catalog, 1)
        ] + [[InlineKeyboardButton(text="📅 محتوای همه (یک هفته)", callback_data="catgenall")]])

        await safe_reply(message, f"📦 *کاتالوگ — {len(catalog)} محصول:*\n\n{text}",
            reply_markup=kb)
        return

    # Subcommands
    subcmd = raw.split(maxsplit=1)
    action = subcmd[0].lower()
    rest = subcmd[1] if len(subcmd) > 1 else ""

    if action == "add":
        parts = [p.strip() for p in rest.split("|")]
        item = {
            "name": parts[0] if parts else "Product",
            "price": parts[1] if len(parts) > 1 else "",
            "desc": parts[2] if len(parts) > 2 else "",
            "category": parts[3] if len(parts) > 3 else "general",
        }
        catalog.append(item)
        await store.set_catalog(message.chat.id, catalog)
        await safe_reply(message, f"✅ *اضافه شد:* {item['name']} — €{item['price']}\n"
            f"📦 کاتالوگ: {len(catalog)} محصول\n\n"
            "_برای تولید محتوا بزن_ `/catalog`")

    elif action == "remove":
        try:
            idx = int(rest) - 1
            removed = catalog.pop(idx)
            await store.set_catalog(message.chat.id, catalog)
            await message.answer(f"🗑 حذف شد: {removed['name']}")
        except (ValueError, IndexError):
            await message.answer("❌ شماره نامعتبر. `/catalog list` رو ببین.")

    elif action == "list":
        if not catalog:
            await message.answer("📦 کاتالوگ خالیه! `/catalog add ...`")
        else:
            lines = [f"*{i}.* {it['name']} — €{it['price']} ({it.get('category', '')})"
                     for i, it in enumerate(catalog, 1)]
            await safe_reply(message, "📦 *کاتالوگ:*\n\n" + "\n".join(lines))

    else:
        # Treat as add
        parts = [p.strip() for p in raw.split("|")]
        item = {
            "name": parts[0],
            "price": parts[1] if len(parts) > 1 else "",
            "desc": parts[2] if len(parts) > 2 else "",
            "category": parts[3] if len(parts) > 3 else "general",
        }
        catalog.append(item)
        await store.set_catalog(message.chat.id, catalog)
        await safe_reply(message, f"✅ *اضافه شد:* {item['name']} — €{item['price']}\n"
            f"📦 کاتالوگ: {len(catalog)} محصول")


# ═══════════════════════════════════════
# /content — All-in-One Content Generator
# ═══════════════════════════════════════

@router.message(Command("content"))
async def cmd_content(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/content")

    if not raw:
        await safe_reply(message, "🔥 *تولید محتوای کامل — همه‌چیز یکجا:*\n\n"
            "`/content [محصول] | [قیمت €] | [توضیح]`\n\n"
            "*مثال:*\n"
            "`/content Concrete Candle | 35 | Soy wax, lavender scent, handmade`\n\n"
            "*تولید می‌کنه:*\n"
            "✍️ ۵ کپشن (EN+FI)\n"
            "🏷 ۳۰ هشتگ بهینه\n"
            "📋 آگهی Etsy + Tori.fi\n"
            "🎨 ۴ پوستر\n"
            "📸 عکس محصول حرفه‌ای\n\n"
            "_یه دستور = همه محتوای مورد نیازت!_")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    price = parts[1] if len(parts) > 1 else ""
    desc = parts[2] if len(parts) > 2 else ""

    brand = store.get_brand(message.chat.id)
    brand_context = ""
    if brand:
        brand_context = (
            f"\nBrand: {brand.get('name', '')}\n"
            f"Tagline: {brand.get('tagline', '')}\n"
            f"Style: {brand.get('style', 'minimal')}\n"
            f"Tone: {brand.get('tone', 'professional')}\n"
        )

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer("🔥 دارم *پکیج کامل محتوا* می‌سازم... (چند مرحله)")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        # ── Step 1: AI generates all text content ──
        prompt = (
            "Create a COMPLETE content package for this product:\n"
            f"Product: {product}\n"
            f"Price: €{price}\n"
            f"Description: {desc}\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{brand_context}\n\n"
            "Generate ALL of these in ONE response:\n\n"
            "═══ SECTION 1: CAPTIONS (5 variants) ═══\n"
            "Write 5 different Instagram captions:\n"
            "1. 🎯 Storytelling (emotional, personal story)\n"
            "2. 💡 Educational (teach about materials/process)\n"
            "3. 🔥 Sale/Urgency (limited offer, FOMO)\n"
            "4. ✨ Aesthetic/Poetic (beautiful, dreamy)\n"
            "5. 🤝 Community (question, engagement)\n\n"
            "Write each in BOTH English AND Finnish.\n"
            "Include call-to-action in each.\n\n"
            "═══ SECTION 2: HASHTAGS ═══\n"
            "30 English hashtags (mix: 10 popular >1M, 10 medium 100K-1M, 10 niche <100K)\n"
            "15 Finnish hashtags\n"
            "5 branded/unique hashtags suggestions\n\n"
            "═══ SECTION 3: ETSY LISTING ═══\n"
            "- SEO title (140 chars max)\n"
            "- Full description (3 paragraphs)\n"
            "- 13 tags\n"
            "- Materials list\n\n"
            "═══ SECTION 4: TORI.FI LISTING ═══\n"
            "- Otsikko (Finnish title)\n"
            "- Kuvaus (Finnish description)\n\n"
            "═══ SECTION 5: WEEKLY POSTING PLAN ═══\n"
            "7-day plan: which caption to post when, best times, platform\n\n"
            "Make everything READY TO COPY-PASTE. "
            "Be creative, engaging, and SEO-optimized."
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt(
                    "You are a world-class social media manager and e-commerce copywriter "
                    "specializing in handmade/artisan brands in the Nordic market. "
                    "You master Etsy SEO (2024 algorithm: query matching + listing quality score), "
                    "Instagram content strategy (Reels, carousels, Stories for engagement + reach), "
                    "and Finnish consumer psychology. You write natively in English AND Finnish (Suomi). "
                    "Every caption is scroll-stopping, every listing is SEO-optimized, "
                    "every hashtag is strategically chosen. Ready to copy-paste.",
                    user_text=message.text or "", user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.85, max_tokens=65536,
        )

        await safe_edit_text(status, "✅ متن‌ها آماده! حالا پوستر و عکس...")

        # ── Step 2: Generate posters ──
        from arki_project.utils.poster_gen import generate_poster

        posters_sent = 0
        for tpl_name, tpl_label in [("sale", "🔴"), ("product", "🔵"), ("minimal", "⚪")]:
            try:
                img_bytes = generate_poster(tpl_name, product, price, "", desc)
                photo = BufferedInputFile(img_bytes, filename=f"poster_{tpl_name}.png")
                await message.answer_photo(
                    photo=photo,
                    caption=f"🎨 {tpl_label} پوستر {tpl_name} — *{product}*",
                    parse_mode="Markdown",
                )
                posters_sent += 1
            except Exception as exc:
                logger.warning("Poster %s failed: %s", tpl_name, exc)

        # ── Step 3: Generate pro photo ──
        try:
            style_prompt = (
                f"Professional product photography of {product}, "
                "handmade artisan candle in textured concrete vessel, "
                "soy wax, dark moody lighting, dark wood surface, "
                "dried flowers and linen props, shallow depth of field, "
                "8k commercial quality, magazine cover, Kinfolk style"
            )
            encoded = urllib.parse.quote(style_prompt)
            img_url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1024&height=1024&model=flux&seed={random.randint(1, 99999)}"
            )
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_get(img_url, timeout=90.0, provider_name="pollinations_img")
                if resp.success and len(resp.content) > 1000:
                    photo = BufferedInputFile(resp.content, filename="product_pro.png")
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    _resp = await client.get(img_url)
                    resp = type('R', (), {'success': _resp.status_code == 200})()
                    if _resp.status_code == 200:
                        photo = BufferedInputFile(_resp.content, filename="product_pro.png")
            if resp.success:
                    await message.answer_photo(
                        photo=photo,
                        caption=f"📸 *عکس حرفه‌ای* — {product}",
                        parse_mode="Markdown",
                    )
        except Exception as exc:
            logger.warning("Pro photo failed: %s", exc)

        # ── Step 4: Send all text content ──
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        header = f"🔥 *پکیج محتوای کامل — {product}:*\n\n"
        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], answer[:400] if answer else "", "content_studio")
        for chunk in split_for_telegram(header + answer):
            try:
                await safe_reply(message, chunk)
            except Exception:
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Content gen failed: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /caption — Advanced Caption Generator
# ═══════════════════════════════════════

@router.message(Command("caption"))
async def cmd_caption(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/caption")

    if not raw:
        await safe_reply(message, "✍️ *کپشن‌ساز حرفه‌ای:*\n\n"
            "`/caption [محصول یا موضوع] | [سبک]`\n\n"
            "*سبک‌ها:*\n"
            "🎯 `story` — داستانی، احساسی\n"
            "💡 `edu` — آموزشی\n"
            "🔥 `sale` — فروش، فوری\n"
            "✨ `aesthetic` — شاعرانه\n"
            "🤝 `engage` — تعاملی، سوالی\n"
            "🎲 `all` — همه ۵ سبک\n\n"
            "*مثال:*\n"
            "`/caption concrete candle | all`\n"
            "`/caption handmade soy candle | story`")
        return

    parts = [p.strip() for p in raw.split("|")]
    topic = parts[0]
    style = parts[1].lower() if len(parts) > 1 else "all"

    brand = store.get_brand(message.chat.id)
    brand_info = f"\nBrand: {brand.get('name', '')} — {brand.get('tagline', '')}" if brand else ""

    styles_map = {
        "story": "storytelling (emotional, personal journey, behind-the-scenes)",
        "edu": "educational (materials, process, sustainability, craft)",
        "sale": "sales/urgency (limited offer, discount, FOMO, deal)",
        "aesthetic": "aesthetic/poetic (dreamy, atmospheric, mood, beauty)",
        "engage": "engagement (question, poll, community, conversation starter)",
    }

    if style == "all":
        style_instruction = "Write 5 captions, one for EACH style:\n" + \
            "\n".join(f"  {i+1}. {v}" for i, v in enumerate(styles_map.values()))
    else:
        s = styles_map.get(style, styles_map["story"])
        style_instruction = f"Write 3 captions in this style: {s}"

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompt = (
            f"Create Instagram captions for: {topic}\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{style_instruction}\n\n"
            "For EACH caption provide:\n"
            "🇬🇧 English version\n"
            "🇫🇮 Finnish version\n"
            "📏 Length: 150-300 words\n"
            "📣 Include CTA (call-to-action)\n"
            "🏷 5 best hashtags for that specific caption\n\n"
            "Make them unique, engaging, and conversion-optimized.\n"
            "Use emojis naturally. Ready to copy-paste."
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are an expert Instagram copywriter for artisan/handmade brands. "
                    "You write captions that get high engagement and drive sales. "
                    "You write fluently in English and Finnish."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.9, max_tokens=65536,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], answer[:400] if answer else "", "content_studio")
        for chunk in split_for_telegram(f"✍️ *کپشن‌ها — {topic}:*\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /hashtag — Smart Hashtag Research
# ═══════════════════════════════════════

@router.message(Command("hashtag"))
async def cmd_hashtag(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/hashtag")

    if not raw:
        await safe_reply(message, "🏷 *تحقیق هشتگ هوشمند:*\n\n"
            "`/hashtag [موضوع یا محصول]`\n\n"
            "*مثال:*\n"
            "`/hashtag concrete candle`\n"
            "`/hashtag handmade home decor Finland`\n\n"
            "_هشتگ‌ها دسته‌بندی شده: محبوب / متوسط / نیچ / فنلاندی_")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompt = (
            f"Research and provide the BEST Instagram hashtags for: {raw}\n"
            f"{brand_ctx(message.chat.id)}\n"
            "Provide hashtags in these categories:\n\n"
            "🔥 *POPULAR (>1M posts):* 10 hashtags\n"
            "These are hard to rank but give exposure.\n\n"
            "📈 *MEDIUM (100K-1M posts):* 15 hashtags\n"
            "Best balance of reach and competition.\n\n"
            "🎯 *NICHE (<100K posts):* 10 hashtags\n"
            "Easy to rank, targeted audience.\n\n"
            "🇫🇮 *FINNISH:* 10 hashtags\n"
            "Finnish-language hashtags for local market.\n\n"
            "💡 *BRANDED (create your own):* 5 suggestions\n"
            "Unique hashtags for brand identity.\n\n"
            "For each category, list the hashtags in copy-paste format.\n"
            "Also provide:\n"
            "- ✅ *RECOMMENDED SET:* The perfect 30 hashtags to use together\n"
            "- 📝 *TIPS:* Best practices for hashtag strategy\n"
            "- ⏰ *ROTATION:* How to rotate hashtags to avoid shadowban"
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are an Instagram growth expert and hashtag researcher who has analyzed "
                    "millions of posts in the handmade/artisan niche. You understand Instagram's "
                    "2024 hashtag distribution algorithm, shadowban triggers (30-hashtag limit, "
                    "banned hashtags, repetition penalties), and the optimal mix of popular/niche "
                    "hashtags for maximum Explore page reach. You provide data-backed strategies "
                    "with actual engagement rate benchmarks."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.7, max_tokens=8192,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], answer[:400] if answer else "", "content_studio")
        for chunk in split_for_telegram(f"🏷 *هشتگ‌ها — {raw}:*\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /batch — Weekly Batch Content
# ═══════════════════════════════════════

@router.message(Command("batch"))
async def cmd_batch(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/batch")

    if not raw:
        await safe_reply(message, "📅 *تولید محتوای دسته‌ای — یک هفته:*\n\n"
            "`/batch [محصول یا تم] | [تعداد پست]`\n\n"
            "*مثال:*\n"
            "`/batch concrete candles collection | 7`\n"
            "`/batch handmade home decor | 14`\n\n"
            "_برای هر پست: کپشن EN+FI + هشتگ + زمان‌بندی + نوع محتوا_")
        return

    parts = [p.strip() for p in raw.split("|")]
    topic = parts[0]
    count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 7

    brand = store.get_brand(message.chat.id)
    brand_info = f"\nBrand: {brand.get('name', '')} — {brand.get('tagline', '')}" if brand else ""

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer(f"📅 دارم {count} پست محتوا می‌سازم...")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompt = (
            f"Create a {count}-day Instagram content calendar for: {topic}\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"For EACH of the {count} days, provide:\n\n"
            "📆 Day X — [Day of week]\n"
            "📌 Content type: (Post / Carousel / Reel / Story)\n"
            "🖼 Photo idea: (describe the exact photo to take/create)\n"
            "🇬🇧 Caption (English):\n"
            "[Full caption ready to paste]\n"
            "🇫🇮 Caption (Finnish):\n"
            "[Full caption in Finnish]\n"
            "🏷 Hashtags: [30 hashtags]\n"
            "⏰ Best posting time: [specific time + timezone]\n"
            "💡 Tip: [engagement tip for this post]\n"
            "━━━━━━━━━━━━━━━\n\n"
            "Mix content types: product shots, behind-the-scenes, "
            "lifestyle, educational, customer testimonials, personal story.\n"
            "Include at least 1 Reel concept and 2 Story ideas.\n"
            "Make all captions unique, engaging, and ready to copy-paste."
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are a professional social media manager for artisan brands. "
                    "You create content calendars that grow accounts and drive sales. "
                    "You write in both English and Finnish. "
                    "Every post you plan has a strategic purpose."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.85, max_tokens=65536,
        )

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], answer[:400] if answer else "", "content_studio")
        for chunk in split_for_telegram(f"📅 *تقویم محتوایی {count} روزه — {topic}:*\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /story — Reels & Story Script Generator
# ═══════════════════════════════════════

@router.message(Command("story"))
async def cmd_story(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/story")

    if not raw:
        await safe_reply(message, "🎬 *اسکریپت استوری و ریلز:*\n\n"
            "`/story [موضوع یا محصول] | [نوع]`\n\n"
            "*نوع‌ها:*\n"
            "🎥 `reel` — ریلز ۱۵-۶۰ ثانیه\n"
            "📱 `story` — استوری ۱۵ ثانیه × چند اسلاید\n"
            "🎭 `bts` — پشت صحنه\n"
            "📦 `unbox` — آنباکسینگ/معرفی\n"
            "🎓 `tutorial` — آموزشی\n\n"
            "*مثال:*\n"
            "`/story concrete candle making | bts`\n"
            "`/story new collection launch | reel`")
        return

    parts = [p.strip() for p in raw.split("|")]
    topic = parts[0]
    vid_type = parts[1].lower() if len(parts) > 1 else "reel"

    type_prompts = {
        "reel": "Instagram Reel (15-60 seconds), vertical video, trending audio",
        "story": "Instagram Story sequence (3-5 slides, 15 sec each), interactive stickers",
        "bts": "Behind-the-scenes (showing the making process, raw and authentic)",
        "unbox": "Unboxing/product reveal (satisfying, ASMR-like, premium feel)",
        "tutorial": "Tutorial/educational (step-by-step, value-first, save-worthy)",
    }

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompt = (
            f"Create a detailed video script for: {topic}\n"
            f"Type: {type_prompts.get(vid_type, type_prompts['reel'])}\n"
            f"{brand_ctx(message.chat.id)}\n"
            "Provide:\n\n"
            "🎬 *CONCEPT:*\n"
            "- Title/hook (first 3 seconds — most important!)\n"
            "- Theme and mood\n"
            "- Target audience\n\n"
            "📝 *SCRIPT (second by second):*\n"
            "⏱ 0-3s: [HOOK — what to show/say]\n"
            "⏱ 3-8s: [SCENE — description]\n"
            "... continue for full duration\n\n"
            "🎵 *AUDIO:*\n"
            "- Trending audio suggestion (describe the type)\n"
            "- Voiceover text (if applicable)\n\n"
            "✍️ *TEXT OVERLAYS:*\n"
            "- English text for each scene\n"
            "- Finnish text for each scene\n\n"
            "📣 *CAPTION:*\n"
            "🇬🇧 English caption with CTA\n"
            "🇫🇮 Finnish caption with CTA\n"
            "🏷 Best hashtags for video content\n\n"
            "💡 *FILMING TIPS:*\n"
            "- Camera angle\n"
            "- Lighting setup\n"
            "- Props needed\n"
            "- Editing transitions\n\n"
            "Make it creative, scroll-stopping, and optimized for the algorithm."
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are a top-tier Instagram/TikTok content creator and video director. "
                    "You create viral video scripts for artisan brands. "
                    "You understand algorithms, hooks, and what makes people stop scrolling. "
                    "You write in English and Finnish."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.9, max_tokens=8192,
        )

        emoji_map = {"reel": "🎥", "story": "📱", "bts": "🎭", "unbox": "📦", "tutorial": "🎓"}
        for chunk in split_for_telegram(
            f"{emoji_map.get(vid_type, '🎬')} *اسکریپت {vid_type} — {topic}:*\n\n{answer}"
        ):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /abtest — A/B Test Caption Variants
# ═══════════════════════════════════════

@router.message(Command("abtest_caption"))
async def cmd_abtest(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/abtest_caption")

    if not raw:
        await safe_reply(message, "🧪 *تست A/B کپشن:*\n\n"
            "`/abtest [محصول] | [هدف]`\n\n"
            "*هدف‌ها:*\n"
            "🛒 `sales` — فروش\n"
            "💬 `engagement` — تعامل\n"
            "👥 `followers` — فالوور\n"
            "🔗 `traffic` — ترافیک لینک\n\n"
            "*مثال:*\n"
            "`/abtest concrete candle | sales`\n\n"
            "_۳ نسخه A/B/C با تحلیل اینکه کدوم بهتر عمل می‌کنه_")
        return

    parts = [p.strip() for p in raw.split("|")]
    topic = parts[0]
    goal = parts[1] if len(parts) > 1 else "sales"

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompt = (
            f"Create 3 A/B/C test caption variants for: {topic}\n"
            f"Goal: Maximize {goal}\n"
            f"{brand_ctx(message.chat.id)}\n"
            "For each variant:\n\n"
            "📝 *VARIANT A — [Strategy name]:*\n"
            "Caption (EN): [full caption]\n"
            "Caption (FI): [full caption]\n"
            "🎯 Strategy: [why this approach works]\n"
            "📊 Expected performance: [engagement rate estimate]\n"
            "✅ Best for: [when/where to use]\n\n"
            "[Same for B and C]\n\n"
            "Then provide:\n"
            "🏆 *RECOMMENDATION:* Which to post first and why\n"
            "📊 *HOW TO MEASURE:* What metrics to track\n"
            "🔄 *ITERATION:* How to improve based on results\n\n"
            "Make each variant genuinely different in approach, not just word changes."
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are a data-driven social media strategist. "
                    "You design A/B tests for caption optimization. "
                    "You understand Instagram algorithm and conversion psychology."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.9, max_tokens=8192,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], answer[:400] if answer else "", "content_studio")
        for chunk in split_for_telegram(f"🧪 *A/B Test — {topic}:*\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# Catalog content generation callback
# ═══════════════════════════════════════

@router.callback_query(F.data == "catgenall")
async def cb_catalog_gen_all(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate content for ALL catalog products."""
    try:
        await callback.answer("🔥 تولید محتوا برای همه...")
        catalog = store.get_catalog(callback.message.chat.id)
        if not catalog:
            await safe_reply(callback.message, "❌ کاتالوگ خالیه. اول /catalog بزن.")
            return
        await safe_reply(
            callback.message,
            f"📅 شروع تولید محتوا برای {len(catalog)} محصول...\n"
            "هر محصول چند ثانیه طول می\u200cکشه.",
        )
        for idx, item in enumerate(catalog):
            fake_text = f"/content {item['name']} | {item['price']} | {item.get('desc', '')}"
            fake_msg = callback.message.model_copy(
                update={"text": fake_text, "from_user": callback.from_user},
            )
            fake_msg.as_(callback.message.bot)
            await cmd_content(fake_msg, ai_client, settings)
    except Exception as exc:
        logger.error("cb_catalog_gen_all error: %s", exc)
        try:
            await callback.message.answer("⚠️ خطایی رخ داد.")
        except Exception as e:
            logger.debug("Suppressed: %s", e)


@router.callback_query(F.data.startswith("catgen:"))
async def cb_catalog_gen(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("🔥 تولید محتوا...")
        idx = int(callback.data.split(":")[1])  # type: ignore[union-attr]
        catalog = store.get_catalog(callback.message.chat.id)  # type: ignore[union-attr]

        if idx >= len(catalog):
            await callback.message.answer("❌ محصول پیدا نشد")  # type: ignore[union-attr]
            return

        item = catalog[idx]
        # Build fake message and execute /content directly
        fake_text = f"/content {item['name']} | {item['price']} | {item.get('desc', '')}"
        fake_msg = callback.message.model_copy(
            update={"text": fake_text, "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_content(fake_msg, ai_client, settings)
    except Exception as exc:
        logger.error("cb_catalog_gen error: %s", exc)
        try:
            await callback.message.answer("⚠️ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        except Exception as e:
            logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════



# ═══════════════════════════════════════
# /calendar — Monthly Content Calendar
# ═══════════════════════════════════════

@router.message(Command("calendar"))
async def cmd_calendar(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/calendar")

    if not raw:
        await safe_reply(message, "📅 *تقویم محتوا — Content Calendar*\n\n"
            "`/calendar [ماه] | [تعداد پست در هفته]`\n\n"
            "*مثال:*\n"
            "`/calendar June | 5`\n"
            "`/calendar تیر | 4`\n"
            "`/calendar next month | 7`\n\n"
            "*خروجی:*\n"
            "📅 تقویم ۳۰ روزه با جزئیات\n"
            "🎨 نوع محتوا برای هر روز\n"
            "📱 پلتفرم هدف\n"
            "⏰ بهترین ساعت انتشار\n"
            "📝 ایده محتوا + هشتگ\n"
            "🎯 هدف هر پست (آگاهی/تعامل/فروش)")
        return

    parts = [p.strip() for p in raw.split("|")]
    month = parts[0]
    posts_per_week = parts[1] if len(parts) > 1 else "5"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("📅 دارم تقویم محتوای ماهانه طراحی می‌کنم...")

    catalog = store.get_catalog(message.chat.id)
    cat_info = ""
    if catalog:
        cat_info = "\nProducts to promote:\n" + "\n".join(
            f"- {p.get('name','?')} (€{p.get('price','?')})" for p in catalog[:10]
        )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a social media strategist for artisan e-commerce brands. "
                    "Create detailed, practical content calendars. Write category headers "
                    "and action items in Persian. Marketing copy examples in English + Finnish. "
                    "Include specific posting times optimized for European audiences."
                )},
                {"role": "user", "content": (
                    f"Create a COMPLETE monthly content calendar for: {month}\n"
                    f"Posts per week: {posts_per_week}\n"
                    f"{brand_ctx(message.chat.id)}\n"
                    f"{cat_info}\n\n"
                    "Platforms: Instagram, TikTok, Pinterest, Etsy\n\n"
                    "For EACH WEEK, create a table:\n\n"
                    "═══ هفته ۱ ═══\n"
                    "| روز | نوع محتوا | پلتفرم | ساعت | ایده | هشتگ‌ها | هدف |\n\n"
                    "Content mix per week:\n"
                    "- 2x Product showcase (lifestyle photography style)\n"
                    "- 1x Behind the scenes / Process\n"
                    "- 1x Educational / Tips\n"
                    "- 1x User engagement (poll, Q&A, quiz)\n"
                    "- 1x Promotional (offer, bundle, new arrival)\n"
                    "- 1x Trend / Seasonal\n\n"
                    "Also include:\n"
                    "📊 KPI targets for the month\n"
                    "🎯 Monthly theme/campaign idea\n"
                    "📌 Key dates (holidays, events) in the month\n"
                    "💡 3 'pillar' content ideas to develop into series\n"
                    "⏰ Best posting times for each platform (EU timezone)"
                )},
            ],
            model_key=mk, temperature=0.8, max_tokens=65536,
        )
        await safe_delete(status)
        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], body[:400] if body else "", "content_studio")
        for chunk in split_for_telegram(f"📅 *تقویم محتوا — {month}:*\n\n{body}"):
            await safe_reply(message, chunk)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /template — Save & Use Content Templates
# ═══════════════════════════════════════

@router.message(Command("template"))
async def cmd_template(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/template")
    chat_id = message.chat.id

    # Templates stored in KV store under "templates" namespace
    templates = store.brands.get(chat_id, {}).get("_templates", [])

    if not raw:
        text = "📝 *قالب‌های محتوا — Content Templates*\n\n"
        if templates:
            for i, t in enumerate(templates):
                text += f"`{i+1}` | *{t['name']}* — {t['type']}\n"
            text += (
                "\n*دستورات:*\n"
                "`/template use [شماره]` — استفاده از قالب\n"
                "`/template add [نام] | [نوع] | [محتوا]` — قالب جدید\n"
                "`/template del [شماره]` — حذف قالب\n"
            )
        else:
            text += (
                "هنوز قالبی نداری!\n\n"
                "*شروع سریع:*\n"
                "`/template generate` — AI خودکار ۵ قالب حرفه‌ای بسازه\n"
                "`/template add نام | نوع | محتوا` — دستی اضافه کن\n\n"
                "*نوع‌ها:* caption, story, ad, email, listing"
            )
        await safe_reply(message, text)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if action == "generate":
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("📝 دارم ۵ قالب حرفه‌ای تولید می‌کنم...")

        try:
            cfg = await ai_client.get_user_config(message.from_user.id)
            mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a content template expert for artisan e-commerce. "
                        "Generate reusable templates. Write instructions in Persian. "
                        "Template content in English. Return as JSON array."
                    )},
                    {"role": "user", "content": (
                        f"{brand_ctx(chat_id)}\n\n"
                        "Generate 5 professional content templates as a JSON array:\n"
                        "[\n"
                        "  {\"name\": \"Product Launch\", \"type\": \"caption\", \"content\": \"...\"},\n"
                        "  ...\n"
                        "]\n\n"
                        "Types: 1x caption (Instagram), 1x story (Reel script), "
                        "1x ad (Facebook/Instagram), 1x email (newsletter), "
                        "1x listing (Etsy/marketplace)\n\n"
                        "Each template should have [PRODUCT], [PRICE], [FEATURE] "
                        "placeholders that users can fill in."
                    )},
                ],
                model_key=mk, temperature=0.7, max_tokens=8192,
            )
            await safe_delete(status)

            # Try to parse JSON from response
            try:
                import re
                json_match = re.search(r'\[[\s\S]*\]', body)
                if json_match:
                    new_templates = json.loads(json_match.group())
                    brand = store.get_brand(chat_id) or {}
                    brand["_templates"] = new_templates
                    await store.set_brand(chat_id, brand)
                    text = "✅ *۵ قالب حرفه‌ای ساخته شد!*\n\n"
                    for i, t in enumerate(new_templates):
                        text += f"`{i+1}` | *{t['name']}* ({t['type']})\n"
                    text += "\n`/template use [شماره]` — برای استفاده"
                    await safe_reply(message, text)
                else:
                    await safe_reply(message, f"📝 *قالب‌ها:*\n\n{body}")
            except (json.JSONDecodeError, KeyError):
                await safe_reply(message, f"📝 *قالب‌ها:*\n\n{body}")
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await safe_edit_text(status, user_friendly_error(exc))

    elif action == "add":
        fields = [p.strip() for p in args.split("|")]
        if len(fields) < 3:
            await safe_reply(message, "📝 `/template add نام | نوع | محتوا`")
            return
        new_t = {"name": fields[0], "type": fields[1], "content": fields[2]}
        brand = store.get_brand(chat_id) or {}
        tpls = brand.get("_templates", [])
        tpls.append(new_t)
        brand["_templates"] = tpls
        await store.set_brand(chat_id, brand)
        await safe_reply(message, f"✅ قالب *{fields[0]}* اضافه شد!")

    elif action == "use":
        try:
            idx = int(args) - 1
            brand = store.get_brand(chat_id) or {}
            tpls = brand.get("_templates", [])
            if 0 <= idx < len(tpls):
                t = tpls[idx]
                await safe_reply(message,
                    f"📝 *قالب: {t['name']}* ({t['type']})\n\n"
                    f"```\n{t['content']}\n```\n\n"
                    "_متغیرها رو جایگزین کن: [PRODUCT], [PRICE], [FEATURE]_")
            else:
                await safe_reply(message, "❌ شماره قالب معتبر نیست.")
        except ValueError:
            await safe_reply(message, "❌ شماره قالب رو بده: `/template use 1`")

    elif action == "del":
        try:
            idx = int(args) - 1
            brand = store.get_brand(chat_id) or {}
            tpls = brand.get("_templates", [])
            if 0 <= idx < len(tpls):
                removed = tpls.pop(idx)
                brand["_templates"] = tpls
                await store.set_brand(chat_id, brand)
                await safe_reply(message, f"🗑 قالب *{removed['name']}* حذف شد.")
            else:
                await safe_reply(message, "❌ شماره قالب معتبر نیست.")
        except ValueError:
            await safe_reply(message, "❌ `/template del [شماره]`")
    else:
        await safe_reply(message, "❌ `/template` — `/template generate` — `/template add`")


# ═══════════════════════════════════════
# /videoplan — Video Content Planner
# ═══════════════════════════════════════

@router.message(Command("videoplan"))
async def cmd_videoplan(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """AI video content planner — Reels, TikTok, YouTube scripts."""
    raw = extract_args(message.text or "", "/videoplan")

    if not raw:
        await safe_reply(message, "🎬 *ویدیو پلنر AI — محتوای ویدیویی:*\n\n"
            "`/videoplan [موضوع] | [پلتفرم]`\n\n"
            "*پلتفرم‌ها:*\n"
            "  `reels` — اینستاگرام ریلز (15-60 ثانیه)\n"
            "  `tiktok` — تیک‌تاک (15-180 ثانیه)\n"
            "  `youtube` — یوتیوب (5-15 دقیقه)\n"
            "  `shorts` — یوتیوب شورتس (60 ثانیه)\n"
            "  `all` — همه پلتفرم‌ها\n\n"
            "*مثال:*\n"
            "`/videoplan پشت صحنه ساخت شمع | reels`\n"
            "`/videoplan how to make candles | youtube`\n"
            "`/videoplan all ۵ ایده ویدیوی شمع`")
        return

    parts = [p.strip() for p in raw.split("|")]
    topic = parts[0]
    platform = parts[1].lower().strip() if len(parts) > 1 else "reels"

    gen_all = topic.lower().startswith("all ")
    if gen_all:
        topic = topic[4:].strip()
        platform = "all"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🎬 دارم اسکریپت ویدیو می‌نویسم...")

    platform_specs = {
        "reels": "Instagram Reels (15-60s), vertical 9:16, trending audio, hook in first 1s",
        "tiktok": "TikTok (15-180s), vertical 9:16, trending sounds, text overlays, fast cuts",
        "youtube": "YouTube long-form (5-15min), 16:9, SEO title/desc, chapters, end screen",
        "shorts": "YouTube Shorts (60s max), vertical 9:16, viral hooks, text captions",
    }

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        platforms = platform_specs if platform == "all" else {platform: platform_specs.get(platform, platform_specs["reels"])}
        bctx = brand_ctx(message.chat.id)

        for pname, pspec in platforms.items():
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a viral video content strategist. Write in Persian. "
                        "Create a COMPLETE video production plan including:\n"
                        "1. 🎬 Hook (first 1-3 seconds — exact words/action)\n"
                        "2. 📋 Shot-by-shot breakdown with timestamps\n"
                        "3. 🎵 Audio/music recommendation\n"
                        "4. 📝 Full script (narration/voiceover)\n"
                        "5. ✏️ Text overlay content\n"
                        "6. 🎯 CTA at the end\n"
                        "7. 📱 Technical specs (resolution, length, format)\n"
                        "8. 🏷 Caption + hashtags for posting\n"
                        "9. ⏰ Best posting time\n"
                        "Make it practical and ready to shoot with just a phone."
                    )},
                    {"role": "user", "content": (
                        f"Create a video plan for: {topic}\n"
                        f"Platform: {pspec}\n"
                        f"{f'Brand: {bctx}' if bctx else ''}"
                    )},
                ],
                model_key=mk, temperature=0.85, max_tokens=8192,
            )

            emoji = {"reels": "📱", "tiktok": "🎵", "youtube": "🎬", "shorts": "📹"}.get(pname, "🎬")
            store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], body[:400] if body else "", "content_studio")
            for chunk in split_for_telegram(f"{emoji} *ویدیو پلن — {pname.upper()} — {topic}:*\n\n{body}"):
                await safe_reply(message, chunk)

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /ugc — User Generated Content Templates
# ═══════════════════════════════════════

@router.message(Command("ugc"))
async def cmd_ugc(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate UGC (User Generated Content) campaign templates."""
    raw = extract_args(message.text or "", "/ugc")

    if not raw:
        await safe_reply(message, "📸 *UGC — محتوای کاربرساخت:*\n\n"
            "`/ugc [محصول]`\n\n"
            "*تولید می‌کنه:*\n"
            "🎯 کمپین UGC (هشتگ + قوانین + جایزه)\n"
            "📧 پیام دعوت از مشتری\n"
            "📋 بریف برای اینفلوئنسر\n"
            "📱 قالب ریپست در استوری\n"
            "📝 متن تشکر + درخواست ریویو\n\n"
            "*مثال:*\n"
            "`/ugc شمع دست‌ساز ارکی`\n"
            "`/ugc handmade candle collection`")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("📸 دارم کمپین UGC طراحی می‌کنم...")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        bctx = brand_ctx(message.chat.id)
        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a UGC marketing expert. Write in Persian. "
                    "Create a COMPLETE UGC campaign kit:\n\n"
                    "1. 🎯 Campaign Setup:\n"
                    "   - Campaign hashtag (unique + brand-specific)\n"
                    "   - Rules (what to post, format, deadline)\n"
                    "   - Prize/incentive structure (3 tiers)\n\n"
                    "2. 📧 Customer Invitation Messages (3 versions):\n"
                    "   - DM template (casual)\n"
                    "   - Post-purchase thank you + UGC ask\n"
                    "   - Re-engagement UGC ask for past buyers\n\n"
                    "3. 📋 Influencer Brief:\n"
                    "   - Product description (what to highlight)\n"
                    "   - Do's and Don'ts\n"
                    "   - Content format requirements\n"
                    "   - Delivery timeline\n\n"
                    "4. 📱 Repost Templates:\n"
                    "   - Story repost caption (3 versions)\n"
                    "   - Feed repost caption (2 versions)\n\n"
                    "5. 📝 Review Request:\n"
                    "   - Etsy review request message\n"
                    "   - Google review request\n"
                    "   - Instagram testimonial request\n\n"
                    "Make everything copy-paste ready."
                )},
                {"role": "user", "content": f"Product: {raw}\n{f'Brand: {bctx}' if bctx else ''}"},
            ],
            model_key=mk, temperature=0.85, max_tokens=65536,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], body[:400] if body else "", "content_studio")
        for chunk in split_for_telegram(f"📸 *کمپین UGC — {raw}:*\n\n{body}"):
            await safe_reply(message, chunk)

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /contentpack — Full Content Package (All-in-One)
# ═══════════════════════════════════════

@router.message(Command("contentpack"))
async def cmd_contentpack(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate a complete content package: caption + hashtags + poster + story script."""
    raw = extract_args(message.text or "", "/contentpack")

    if not raw:
        await safe_reply(message, "📦 *بسته محتوای کامل — همه‌چیز یکجا:*\n\n"
            "`/contentpack [محصول/موضوع]`\n\n"
            "یکجا تولید می‌شه:\n"
            "✅ ۳ کپشن (فارسی + انگلیسی + فنلاندی)\n"
            "✅ ۲۰ هشتگ هوشمند\n"
            "✅ اسکریپت استوری/ریلز\n"
            "✅ ۳ CTA بهینه\n"
            "✅ زمان‌بندی بهترین ساعت انتشار\n"
            "✅ ایده عکس/ویدیو\n\n"
            "*مثال:*\n"
            "`/contentpack شمع لاوندر جدید`\n"
            "`/contentpack new concrete candle collection`")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("📦 دارم بسته محتوای کامل می‌سازم...")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        bctx = brand_ctx(message.chat.id)
        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a content production studio. Create a COMPLETE content package. "
                    "Write descriptions in Persian, marketing materials in Persian + English + Finnish.\n\n"
                    "Produce ALL of these:\n\n"
                    "═══ 1. CAPTIONS (3 versions) ═══\n"
                    "🇮🇷 Persian caption (emotional, story-telling)\n"
                    "🇬🇧 English caption (professional, SEO)\n"
                    "🇫🇮 Finnish caption (local, warm)\n\n"
                    "═══ 2. HASHTAGS ═══\n"
                    "20 strategic hashtags: 5 high-volume + 10 mid + 5 niche\n\n"
                    "═══ 3. STORY/REELS SCRIPT ═══\n"
                    "15-second script with exact timestamps\n"
                    "Hook → Content → CTA\n\n"
                    "═══ 4. CTAs (3 versions) ═══\n"
                    "Soft CTA, Direct CTA, Urgency CTA\n\n"
                    "═══ 5. POSTING SCHEDULE ═══\n"
                    "Best day & time for IG, TikTok, Pinterest\n\n"
                    "═══ 6. PHOTO/VIDEO IDEAS ═══\n"
                    "3 specific photo composition ideas\n"
                    "2 video concepts\n\n"
                    "Make everything ready to use — no fluff."
                )},
                {"role": "user", "content": f"Product: {raw}\n{f'Brand: {bctx}' if bctx else ''}"},
            ],
            model_key=mk, temperature=0.85, max_tokens=16384,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:200], body[:400] if body else "", "content_studio")
        for chunk in split_for_telegram(f"📦 *بسته محتوای کامل — {raw}:*\n\n{body}"):
            await safe_reply(message, chunk)

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


