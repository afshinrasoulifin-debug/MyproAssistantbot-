
from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError
"""
tg_bot/handlers/platforms.py
─────────────────────────────
🌐 Multi-Platform E-Commerce Hub — Finland + Europe + International

Covers 12+ platforms with credential management, auto-formatted listings,
and automation pipeline.

Commands:
  /platforms  — Main dashboard: see all platforms & status
  /connect    — Add/manage platform credentials & shop info
  /publish    — One product → formatted listings for ALL platforms
  /multilist  — Quick multi-platform listing (text only)
  /shopmanage — Shop management: orders, inventory, analytics tips
  /euromarket — European marketplace guide & optimizer
"""


import json
import logging
from typing import Any

from aiogram import F, Router
from aiogram.enums import ChatAction
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
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import brand_ctx, extract_args
from arki_project.utils.data_store import store
from arki_project.utils.v7_core import (


# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

    enhance_system_prompt, store_result,
)

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
logger = logging.getLogger(__name__)
router = Router(name="platforms")


# ═══════════════════════════════════════════
# Platform Registry — all supported platforms
# ═══════════════════════════════════════════

PLATFORMS: dict[str, dict[str, Any]] = {
    # ── Finland ──
    "tori": {
        "name": "Tori.fi",
        "flag": "🇫🇮",
        "region": "Finland",
        "type": "Classifieds",
        "url": "https://www.tori.fi",
        "lang": "fi",
        "listing_format": "title_fi, description_fi, price_eur, location, category, shipping",
        "tips": "Finnish only. Friendly tone. Include location. Free to list.",
    },
    "huuto": {
        "name": "Huuto.net",
        "flag": "🇫🇮",
        "region": "Finland",
        "type": "Auction/Marketplace",
        "url": "https://www.huuto.net",
        "lang": "fi",
        "listing_format": "title_fi, description_fi, starting_price, buy_now_price, category, shipping_cost",
        "tips": "Auction or buy-now. Finnish. Good for unique/handmade items.",
    },
    # ── Nordic ──
    "tradera": {
        "name": "Tradera",
        "flag": "🇸🇪",
        "region": "Sweden/Nordic",
        "type": "Auction/Marketplace",
        "url": "https://www.tradera.com",
        "lang": "sv",
        "listing_format": "title_sv, description_sv, price_sek, category, shipping",
        "tips": "Sweden's largest auction site. Swedish language. Convert €→SEK.",
    },
    "dba": {
        "name": "DBA.dk",
        "flag": "🇩🇰",
        "region": "Denmark",
        "type": "Classifieds",
        "url": "https://www.dba.dk",
        "lang": "da",
        "listing_format": "title_da, description_da, price_dkk, location, category",
        "tips": "Denmark classifieds. Danish language. Convert €→DKK.",
    },
    "finn": {
        "name": "FINN.no",
        "flag": "🇳🇴",
        "region": "Norway",
        "type": "Classifieds",
        "url": "https://www.finn.no",
        "lang": "no",
        "listing_format": "title_no, description_no, price_nok, location, category",
        "tips": "Norway's #1 marketplace. Norwegian. Convert €→NOK.",
    },
    "cdon": {
        "name": "CDON",
        "flag": "🇸🇪",
        "region": "Nordics (SE/FI/NO/DK)",
        "type": "Marketplace",
        "url": "https://www.cdon.com",
        "lang": "en/sv/fi/no/da",
        "listing_format": "title_en, description_en, price_eur, ean_code, category, images",
        "tips": "Pan-Nordic marketplace. Seller account needed. Good for reaching all Nordics.",
    },
    # ── International ──
    "etsy": {
        "name": "Etsy",
        "flag": "🌍",
        "region": "International",
        "type": "Handmade Marketplace",
        "url": "https://www.etsy.com",
        "lang": "en",
        "listing_format": "title_140ch, description_3para, 13_tags_20ch, materials, shipping, photos",
        "tips": "SEO is KING. Long-tail keywords. 13 tags max 20 chars each. Free+paid shipping strategy.",
    },
    "amazon_handmade": {
        "name": "Amazon Handmade",
        "flag": "🌍",
        "region": "EU (DE/FR/IT/ES/NL)",
        "type": "Handmade Marketplace",
        "url": "https://www.amazon.com/handmade",
        "lang": "en/de/fr",
        "listing_format": "title, bullet_points_5, description, search_terms, price_eur",
        "tips": "Apply as artisan. 5 bullet points crucial. Amazon SEO = backend keywords.",
    },
    "ebay": {
        "name": "eBay",
        "flag": "🌍",
        "region": "International",
        "type": "Auction/Marketplace",
        "url": "https://www.ebay.com",
        "lang": "en/de",
        "listing_format": "title_80ch, description_html, price, item_specifics, shipping, returns",
        "tips": "Fixed price or auction. Item specifics important. eBay.de for German market.",
    },
    "faire": {
        "name": "Faire",
        "flag": "🌍",
        "region": "International (Wholesale)",
        "type": "Wholesale Marketplace",
        "url": "https://www.faire.com",
        "lang": "en",
        "listing_format": "title, description, wholesale_price, retail_price, min_order, lead_time",
        "tips": "Wholesale to boutiques/shops. Net 60 terms. Minimum order quantities. Great for scaling.",
    },
    "notonthehighstreet": {
        "name": "Not On The High Street",
        "flag": "🇬🇧",
        "region": "UK",
        "type": "Handmade/Unique",
        "url": "https://www.notonthehighstreet.com",
        "lang": "en",
        "listing_format": "title, description, price_gbp, personalisation_options, delivery",
        "tips": "UK market. Apply as partner. Personalization = higher sales. GBP pricing.",
    },
    "fruugo": {
        "name": "Fruugo",
        "flag": "🇪🇺",
        "region": "Pan-European (46 countries)",
        "type": "Marketplace",
        "url": "https://www.fruugo.com",
        "lang": "auto-translated",
        "listing_format": "title_en, description_en, price_eur, ean, category, images",
        "tips": "Auto-translates to 30+ languages. One listing = 46 countries. Low competition for handmade.",
    },
    # ── Social Commerce ──
    "instagram_shop": {
        "name": "Instagram Shop",
        "flag": "📸",
        "region": "International",
        "type": "Social Commerce",
        "url": "https://www.instagram.com",
        "lang": "en/fi",
        "listing_format": "product_name, description, price_eur, category, tags, photos",
        "tips": "Link to Shopify/Etsy catalog. Product tags in posts. Shopping stickers in stories.",
    },
    "facebook_shop": {
        "name": "Facebook Marketplace/Shop",
        "flag": "📘",
        "region": "Finland/EU",
        "type": "Social Commerce",
        "url": "https://www.facebook.com/marketplace",
        "lang": "fi/en",
        "listing_format": "title, description, price_eur, category, location, condition, photos",
        "tips": "Free to list. Local buyers. Finnish + English. Great for Finland market.",
    },
    "pinterest_shop": {
        "name": "Pinterest Shopping",
        "flag": "📌",
        "region": "International",
        "type": "Social Commerce / Discovery",
        "url": "https://www.pinterest.com",
        "lang": "en",
        "listing_format": "pin_title, pin_description, price, product_link, board, keywords",
        "tips": "Visual search engine. Rich pins. Boards = categories. Long shelf life for pins.",
    },
    "tiktok_shop": {
        "name": "TikTok Shop",
        "flag": "🎵",
        "region": "EU (expanding)",
        "type": "Social Commerce",
        "url": "https://shop.tiktok.com",
        "lang": "en",
        "listing_format": "product_name, description, price, video_showcase, category",
        "tips": "Video-first. Product demos. Trending sounds. Younger audience. Growing fast in EU.",
    },
}


@router.message(Command("platforms"))
async def cmd_platforms(message: Message) -> None:
    profiles = store.get_shop_profiles(message.chat.id)

    # Group by region
    regions: dict[str, list[str]] = {}
    for key, p in PLATFORMS.items():
        r = p["region"].split("/")[0].split("(")[0].strip()
        regions.setdefault(r, []).append(key)

    lines = []
    for region, keys in regions.items():
        rline = f"\n*{region}:*\n"
        for k in keys:
            p = PLATFORMS[k]
            connected = "✅" if k in profiles else "⬜"
            rline += f"  {connected} {p['flag']} *{p['name']}* — {p['type']}\n"
        lines.append(rline)

    connected_count = len(profiles)
    total = len(PLATFORMS)

    text = (
        f"🌐 *پلتفرم‌های آنلاین شاپ — {connected_count}/{total} متصل:*\n"
        + "".join(lines)
        + "\n━━━━━━━━━━━━━━━\n"
        "🔗 `/connect [platform]` — اتصال/تنظیم اکانت\n"
        "📋 `/publish [product]` — انتشار در *همه* پلتفرم‌ها\n"
        "📊 `/shopmanage` — مدیریت فروشگاه\n"
        "🇪🇺 `/euromarket` — راهنمای بازار اروپا\n"
    )

    # Inline keyboard for quick connect
    buttons = []
    row = []
    for k, p in PLATFORMS.items():
        status = "✅" if k in profiles else "➕"
        row.append(InlineKeyboardButton(
            text=f"{status} {p['flag']} {p['name'][:12]}",
            callback_data=f"plat:info:{k}",
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await safe_reply(message, text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


# Platform info callback
@router.callback_query(F.data.startswith("plat:info:"))
async def cb_platform_info(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        key = callback.data.split(":")[2]
        p = PLATFORMS.get(key)
        if not p:
            return

        profiles = store.get_shop_profiles(callback.message.chat.id)
        profile = profiles.get(key)

        status_text = ""
        if profile:
            status_text = "\n\n✅ *متصل:*\n"
            for pk, pv in profile.items():
                if pk not in ("api_key", "api_secret", "token"):
                    status_text += f"  • {pk}: `{pv}`\n"
                else:
                    status_text += f"  • {pk}: `{'*' * 8}...`\n"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔗 اتصال / ویرایش",
                callback_data=f"plat:connect:{key}",
            )],
            [InlineKeyboardButton(text="🔙 برگشت", callback_data="plat:back")],
        ])

        await safe_edit_text(callback.message, f"{p['flag']} *{p['name']}*\n\n"
            f"🌍 منطقه: {p['region']}\n"
            f"🏷 نوع: {p['type']}\n"
            f"🔗 {p['url']}\n"
            f"🗣 زبان: {p['lang']}\n\n"
            f"📋 *فرمت آگهی:*\n`{p['listing_format']}`\n\n"
            f"💡 *نکات:*\n_{p['tips']}_"
            f"{status_text}\n\n"
            f"اتصال: `/connect {key} [اطلاعات]`",
            reply_markup=kb)

    except HandlerError as exc:
        logger.error("cb_platform_info error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except CallbackError as e:
            logger.debug("Suppressed: %s", e)
@router.callback_query(F.data == "plat:back")
async def cb_plat_back(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        await callback.message.delete()

    except HandlerError as exc:
        logger.error("cb_plat_back error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except CallbackError as e:
            logger.debug("Suppressed: %s", e)
@router.callback_query(F.data.startswith("plat:connect:"))
async def cb_plat_connect(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        key = callback.data.split(":")[2]
        p = PLATFORMS.get(key)
        if not p:
            return

        # Show connection instructions
        connect_guides = {
            "etsy": (
                "🔗 *اتصال Etsy:*\n\n"
                "`/connect etsy shop_name=[نام شاپ] | shop_url=[لینک] | api_key=[کلید API]`\n\n"
                "*یا ساده:*\n"
                "`/connect etsy shop_name=MyCandles | shop_url=etsy.com/shop/MyCandles`\n\n"
                "_API key اختیاریه — بدونش هم آگهی آماده تولید می‌شه._"
            ),
            "tori": (
                "🔗 *اتصال Tori.fi:*\n\n"
                "`/connect tori username=[نام کاربری] | location=[شهر] | phone=[شماره]`\n\n"
                "*مثال:*\n"
                "`/connect tori username=ArkiCandles | location=Helsinki | phone=+358...`"
            ),
        }

        default_guide = (
            f"🔗 *اتصال {p['name']}:*\n\n"
            f"`/connect {key} shop_name=[نام] | shop_url=[لینک] | username=[کاربری]`\n\n"
            "_هر اطلاعاتی که داری اضافه کن — موقع تولید آگهی استفاده می‌شه._"
        )

        await safe_edit_text(callback.message, connect_guides.get(key, default_guide))

    except HandlerError as exc:
        logger.error("cb_plat_connect error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except CallbackError as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /connect — Add/Manage Platform Credentials
# ═══════════════════════════════════════

@router.message(Command("connect"))
async def cmd_connect(message: Message) -> None:
    raw = extract_args(message.text or "", "/connect")

    if not raw:
        await safe_reply(message, "🔗 *اتصال پلتفرم:*\n\n"
            "`/connect [platform] [key=value | key=value | ...]`\n\n"
            "*پلتفرم‌ها:*\n"
            + "\n".join(f"  `{k}` — {p['flag']} {p['name']}" for k, p in PLATFORMS.items())
            + "\n\n*مثال‌ها:*\n"
            "`/connect etsy shop_name=ArkiCandles | shop_url=etsy.com/shop/ArkiCandles`\n"
            "`/connect tori username=Afshin | location=Helsinki`\n"
            "`/connect instagram_shop username=arki.candles`\n"
            "`/connect shopify store_url=arki-candles.myshopify.com | api_key=xxx`\n\n"
            "*مشاهده:*\n"
            "`/connect list` — لیست همه اتصالات\n"
            "`/connect remove [platform]` — حذف")
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()

    # /connect list
    if action == "list":
        profiles = store.get_shop_profiles(message.chat.id)
        if not profiles:
            await message.answer("⬜ هنوز هیچ پلتفرمی متصل نشده.\n`/connect [platform] ...`")
            return
        lines = []
        for k, prof in profiles.items():
            p = PLATFORMS.get(k, {"flag": "❓", "name": k})
            info = " | ".join(f"{pk}={pv}" for pk, pv in prof.items()
                              if pk not in ("api_key", "api_secret", "token"))
            lines.append(f"✅ {p['flag']} *{p['name']}*\n   {info}")
        await safe_reply(message, "🔗 *پلتفرم‌های متصل:*\n\n" + "\n\n".join(lines))
        return

    # /connect remove [platform]
    if action == "remove":
        plat = parts[1].lower() if len(parts) > 1 else ""
        profiles = store.get_shop_profiles(message.chat.id)
        if plat in profiles:
            del profiles[plat]
            p = PLATFORMS.get(plat, {"name": plat})
            await message.answer(f"🗑 {p.get('flag', '')} {p['name']} حذف شد.")
        else:
            await message.answer("❌ این پلتفرم متصل نیست.")
        return

    # /connect [platform] key=value | key=value
    platform_key = action
    if platform_key not in PLATFORMS:
        # Try fuzzy match
        for k in PLATFORMS:
            if k.startswith(platform_key) or platform_key in k:
                platform_key = k
                break
        else:
            await message.answer(
                f"❌ پلتفرم `{action}` شناخته نشد.\n\n"
                "پلتفرم‌های معتبر:\n"
                + "\n".join(f"  `{k}`" for k in PLATFORMS),
            )
            return

    # Parse key=value pairs
    data_str = parts[1] if len(parts) > 1 else ""
    profile: dict[str, str] = {}
    for pair in data_str.replace("|", "\n").split("\n"):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            profile[k.strip()] = v.strip()

    if not profile:
        p = PLATFORMS[platform_key]
        await safe_reply(message, "❌ اطلاعاتی وارد نشد.\n\n"
            f"*فرمت {p['name']}:*\n"
            f"`/connect {platform_key} shop_name=[نام] | shop_url=[لینک]`")
        return

    # Save
    await store.set_shop_profile(message.chat.id, platform_key, profile)
    p = PLATFORMS[platform_key]

    safe_info = " | ".join(f"{k}={v}" for k, v in profile.items()
                            if k not in ("api_key", "api_secret", "token"))

    await safe_reply(message, f"✅ {p['flag']} *{p['name']}* متصل شد!\n\n"
        f"📋 {safe_info}\n\n"
        "_حالا `/publish` آگهی‌های بهینه برای این پلتفرم هم تولید می‌کنه._")


# ═══════════════════════════════════════
# /publish — One Product → ALL Platforms
# ═══════════════════════════════════════

@router.message(Command("publish"))
async def cmd_publish(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/publish")

    if not raw:
        await safe_reply(message, "📋 *انتشار در همه پلتفرم‌ها:*\n\n"
            "`/publish [محصول] | [قیمت €] | [توضیحات]`\n\n"
            "*مثال:*\n"
            "`/publish Concrete Candle | 35 | Soy wax, lavender, 40h burn`\n\n"
            "_یه دستور = آگهی بهینه برای ۱۶ پلتفرم!_\n"
            "_هر آگهی با فرمت، زبان و SEO مخصوص همون پلتفرم._\n\n"
            "💡 اول پلتفرم‌هات رو وصل کن: `/connect`")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    price = parts[1] if len(parts) > 1 else ""
    desc = parts[2] if len(parts) > 2 else ""

    profiles = store.get_shop_profiles(message.chat.id)

    # Determine which platforms to generate for
    # Always include: etsy, tori, instagram_shop (core platforms)
    # Plus all connected platforms
    target_platforms = {"etsy", "tori", "instagram_shop"}
    target_platforms.update(profiles.keys())

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer(
        f"📋 دارم آگهی بهینه برای *{len(target_platforms)} پلتفرم* تولید می‌کنم..."
    )

    # Build platform-specific instructions
    platform_sections = []
    for key in sorted(target_platforms):
        p = PLATFORMS.get(key)
        if not p:
            continue
        profile = profiles.get(key, {})
        profile_info = ""
        if profile:
            profile_info = f"\nSeller info: {json.dumps(profile, ensure_ascii=False)}"

        platform_sections.append(
            f"═══ {p['flag']} {p['name']} ({p['region']}) ═══\n"
            f"Language: {p['lang']}\n"
            f"Format needed: {p['listing_format']}\n"
            f"Tips: {p['tips']}{profile_info}\n"
            "Create a COMPLETE, ready-to-paste listing for this platform.\n"
        )

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        # Get brand context
        brand_ctx = ""
        try:
            from arki_project.handlers.content_studio import _brands
            brand = _brands.get(message.chat.id, {})
            if brand:
                brand_ctx = (
                    f"\nBrand: {brand.get('name', '')}\n"
                    f"Tagline: {brand.get('tagline', '')}\n"
                    f"Style: {brand.get('style', 'minimal')}\n"
                )
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)

        prompt = (
            "Create OPTIMIZED LISTINGS for this product on MULTIPLE platforms:\n\n"
            f"Product: {product}\n"
            f"Price: €{price}\n"
            f"Description: {desc}\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{brand_ctx}\n\n"
            "Generate a COMPLETE, READY-TO-PASTE listing for EACH platform below.\n"
            "Each listing must be:\n"
            "- In the CORRECT LANGUAGE for that platform\n"
            "- Following the EXACT FORMAT that platform requires\n"
            "- SEO-optimized for that platform's search algorithm\n"
            "- Include platform-specific hashtags/tags/keywords\n"
            "- Include correct currency conversion (€1 ≈ SEK 11.5, DKK 7.5, NOK 11.8, GBP 0.86)\n\n"
            + "\n\n".join(platform_sections)
            + "\n\nMake every listing PROFESSIONAL and READY TO COPY-PASTE directly."
        )

        import time as _t; _t0 = _t.time()
        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt(
                    "You are the world's best multi-platform e-commerce listing specialist. "
                    "You know the exact format, SEO rules, and best practices for every online "
                    "marketplace in Finland, Nordics, and Europe. You write fluently in Finnish, "
                    "Swedish, Danish, Norwegian, English, German, and French. "
                    "Every listing you create is optimized for maximum visibility and conversion "
                    "on its specific platform.",
                    user_text=message.text or "", user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.8, max_tokens=16384,
        )

        await safe_delete(status)

        header = f"📋 *آگهی «{product}» — {len(target_platforms)} پلتفرم:*"
        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:300], answer[:500] if answer else "", "platforms", duration_s=_t.time()-_t0)
        for chunk in split_for_telegram(f"{header}\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

        # Summary with action buttons
        connected_list = "\n".join(
            f"  ✅ {PLATFORMS[k]['flag']} {PLATFORMS[k]['name']}"
            for k in sorted(target_platforms) if k in PLATFORMS
        )
        await safe_reply(message, "📋 *خلاصه انتشار:*\n\n"
            f"{connected_list}\n\n"
            "💡 *گام بعدی:* هر آگهی رو کپی‌پیست کن در پلتفرم مربوطه.\n"
            "📌 پلتفرم بیشتر وصل کن: `/connect`\n"
            f"🔄 عکس حرفه‌ای: `/photopro {product}`")

    except HandlerError as exc:
        logger.error("Publish failed: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /shopmanage — Shop Management Hub
# ═══════════════════════════════════════

@router.message(Command("shopmanage"))
async def cmd_shopmanage(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/shopmanage")

    subcmds = {
        "inventory": "Inventory management strategy",
        "shipping": "Shipping optimization (Finland → EU/international)",
        "returns": "Returns & refund policy templates",
        "legal": "Legal requirements (EU consumer law, CE marking, GDPR)",
        "tax": "Tax guide (VAT, customs, EU selling from Finland)",
        "packaging": "Eco-friendly packaging & unboxing experience",
        "growth": "Growth roadmap: 0→100→1000 sales",
    }

    if not raw or raw.lower() not in subcmds:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📦 {k.title()}", callback_data=f"shop:{k}")]
            for k in subcmds
        ])
        await safe_reply(message, "🏪 *مدیریت فروشگاه:*\n\n"
            + "\n".join(f"📌 `/shopmanage {k}` — {v}" for k, v in subcmds.items())
            + "\n\n_یا از دکمه‌ها استفاده کن:_",
            reply_markup=kb)
        return

    topic = raw.lower()
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    profiles = store.get_shop_profiles(message.chat.id)
    platforms_ctx = ", ".join(PLATFORMS[k]["name"] for k in profiles if k in PLATFORMS) or "Etsy, Tori.fi"

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompts = {
            "inventory": (
                "Create a complete INVENTORY MANAGEMENT system for a handmade candle business:\n"
                "- Raw materials tracking (wax, wicks, fragrance oils, concrete)\n"
                "- Production batch tracking\n"
                "- Stock level alerts\n"
                "- Multi-platform inventory sync strategy\n"
                "- Seasonal demand forecasting\n"
                "- Reorder points and formulas\n"
                "- Simple spreadsheet template design"
            ),
            "shipping": (
                "Create a SHIPPING OPTIMIZATION guide for Finland-based handmade candle seller:\n"
                "- Posti (Finland) rates and options\n"
                "- Matkahuolto alternatives\n"
                "- EU shipping: cheapest options from Finland\n"
                "- International shipping (US, UK, Asia)\n"
                "- Packaging for fragile candles (safety, breakage prevention)\n"
                "- Free shipping threshold strategy\n"
                "- Shipping cost calculator approach\n"
                "- Customs declarations for candles (wax = not restricted)\n"
                "- Delivery time expectations per region"
            ),
            "returns": (
                "Create RETURNS & REFUND POLICY templates for handmade candle seller:\n"
                "- Etsy return policy (EN)\n"
                "- Tori.fi return policy (FI)\n"
                "- General EU consumer rights (14-day cooling off)\n"
                "- Damaged item handling process\n"
                "- Custom/personalized order policy\n"
                "- Refund email templates (EN + FI)\n"
                "- How to minimize returns"
            ),
            "legal": (
                "Create a LEGAL GUIDE for selling handmade candles from Finland in the EU:\n"
                "- Business registration (toiminimi / yritys)\n"
                "- CLP regulation for candles (classification, labelling, packaging)\n"
                "- Safety data sheets for candles\n"
                "- CE marking requirements\n"
                "- REACH compliance\n"
                "- GDPR for customer data\n"
                "- Consumer protection laws EU\n"
                "- Insurance recommendations\n"
                "- Tax registration (Y-tunnus)"
            ),
            "tax": (
                "Create a TAX GUIDE for Finnish-based online seller:\n"
                "- ALV/VAT registration threshold (€15,000)\n"
                "- VAT rates for candles in Finland (24%)\n"
                "- EU VAT: OSS (One-Stop-Shop) for cross-border B2C sales\n"
                "- When to register for VAT in other EU countries\n"
                "- Etsy VAT handling\n"
                "- Tax deductions for home-based business\n"
                "- Bookkeeping requirements\n"
                "- Veroilmoitus (tax return) basics\n"
                "- International sales outside EU (customs, duties)"
            ),
            "packaging": (
                "Create a PACKAGING & UNBOXING EXPERIENCE guide for handmade candles:\n"
                "- Eco-friendly packaging options available in Finland\n"
                "- Branded packaging on a budget\n"
                "- Unboxing experience design (creates social sharing!)\n"
                "- Insert card design (thank you, social media, review request)\n"
                "- Candle-safe shipping packaging\n"
                "- Seasonal packaging variations\n"
                "- Cost analysis per package\n"
                "- Supplier recommendations (EU)"
            ),
            "growth": (
                "Create a GROWTH ROADMAP for handmade candle business:\n\n"
                "Phase 1: 0→100 sales (foundation)\n"
                "Phase 2: 100→500 sales (scaling)\n"
                "Phase 3: 500→1000+ sales (automation & team)\n\n"
                "For each phase:\n"
                "- Revenue targets\n"
                "- Platform strategy\n"
                "- Marketing budget\n"
                "- Production capacity\n"
                "- Key milestones\n"
                "- Time to market considerations"
            ),
        }

        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are a senior e-commerce business consultant specializing in "
                    "handmade/artisan businesses in Finland and the EU. You know Finnish "
                    "business law, EU regulations, and practical selling on all major platforms. "
                    "Write in Persian with Finnish/English legal terms and practical details."},
                {"role": "user", "content":
                    f"{prompts[topic]}\n\n"
                    f"Active platforms: {platforms_ctx}\n"
                    "Location: Finland\n"
                    f"Product: {brand_ctx(message.chat.id)}"},
            ],
            model_key=mk, temperature=0.7, max_tokens=16384,
        )

        emoji_map = {
            "inventory": "📦", "shipping": "🚚", "returns": "🔄",
            "legal": "⚖️", "tax": "💶", "packaging": "🎁", "growth": "📈",
        }
        for chunk in split_for_telegram(
            f"{emoji_map.get(topic, '🏪')} *{subcmds[topic]}:*\n\n{body}"
        ):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


@router.callback_query(F.data.startswith("shop:"))
async def cb_shopmanage(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("⏳ در حال تولید...")
        topic = callback.data.split(":")[1]
        # Create a fake message to reuse the handler
        await safe_reply(callback.message, f"🏪 `/shopmanage {topic}` رو اجرا کن")

    except HandlerError as exc:
        logger.error("cb_shopmanage error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except CallbackError as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /euromarket — European Market Guide
# ═══════════════════════════════════════

@router.message(Command("euromarket"))
async def cmd_euromarket(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/euromarket")

    countries = {
        "finland": "🇫🇮 Finland (Tori.fi, Huuto.net, local markets)",
        "sweden": "🇸🇪 Sweden (Tradera, Blocket)",
        "denmark": "🇩🇰 Denmark (DBA.dk)",
        "norway": "🇳🇴 Norway (FINN.no)",
        "germany": "🇩🇪 Germany (eBay.de, Amazon.de, Etsy DE)",
        "uk": "🇬🇧 UK (Etsy UK, NOTHS, Amazon UK)",
        "france": "🇫🇷 France (Etsy FR, Amazon.fr, Le Bon Coin)",
        "netherlands": "🇳🇱 Netherlands (Bol.com, Marktplaats)",
        "all": "🌍 Full European expansion strategy",
    }

    if not raw or raw.lower() not in countries:
        lines = "\n".join(f"  `{k}` — {v}" for k, v in countries.items())
        await safe_reply(message, "🇪🇺 *راهنمای بازار اروپا:*\n\n"
            "`/euromarket [کشور]`\n\n"
            f"{lines}\n\n"
            "*مثال:*\n"
            "`/euromarket germany`\n"
            "`/euromarket all`")
        return

    country = raw.lower()
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer(f"🇪🇺 دارم تحلیل بازار {country} رو می‌سازم...")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        if country == "all":
            prompt = (
                "Create a COMPLETE European market expansion strategy for handmade candles from Finland:\n\n"
                "For each major market (Finland, Sweden, Denmark, Norway, Germany, UK, France, Netherlands):\n"
                "- Best platforms to sell on\n"
                "- Market size for handmade candles\n"
                "- Consumer preferences\n"
                "- Language requirements\n"
                "- Shipping from Finland: cost, time, best carrier\n"
                "- Legal/tax considerations\n"
                "- Entry difficulty: Easy/Medium/Hard\n"
                "- Recommended entry order (which market first?)\n\n"
                "Then provide:\n"
                "📅 12-MONTH EXPANSION TIMELINE\n"
                "💰 REVENUE PROJECTIONS per market\n"
                "🎯 PRIORITY RANKING of markets"
            )
        else:
            prompt = (
                f"Create a DEEP MARKET GUIDE for selling handmade candles in {country.upper()}:\n\n"
                "📊 Market Overview:\n"
                "- Market size for candles/home decor\n"
                "- Consumer behavior and preferences\n"
                "- Average spending on handmade items\n"
                "- Seasonal peaks\n\n"
                "🛒 Best Platforms:\n"
                "- Top 3 platforms ranked by potential\n"
                "- How to register on each\n"
                "- Fees comparison\n"
                "- Tips for each platform\n\n"
                "🗣 Language & Localization:\n"
                "- Listing language (translate or English OK?)\n"
                "- Key phrases in local language\n"
                "- Cultural notes for marketing\n\n"
                "🚚 Logistics:\n"
                "- Shipping from Finland: best carriers, cost, transit time\n"
                "- Returns handling\n"
                "- Currency conversion\n\n"
                "⚖️ Legal & Tax:\n"
                "- VAT requirements\n"
                "- Product regulations for candles\n"
                "- Consumer protection laws\n\n"
                "📈 Entry Strategy:\n"
                "- Step-by-step action plan\n"
                "- First 30 days checklist\n"
                "- Expected timeline to first sale\n"
                "- Budget needed"
            )

        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are a European e-commerce expansion consultant. "
                    "You know every marketplace, regulation, and consumer trend in Europe. "
                    "You help Finnish artisan brands expand internationally. "
                    "Write in Persian with local-language terms and practical details."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.7, max_tokens=16384,
        )

        await safe_delete(status)
        for chunk in split_for_telegram(f"🇪🇺 *بازار {country.title()}:*\n\n{body}"):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════


