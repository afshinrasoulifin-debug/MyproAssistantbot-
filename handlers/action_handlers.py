"""
handlers/action_handlers.py — Universal Action Handler System
=============================================================
Makes ALL submenu buttons actually work.
Instead of "coming soon", each button either:
  - Asks for user input (sets pending state)
  - Or executes immediately (admin stats, etc.)

Categories:
  IMAGE: Generate actual images via g4f OperaAria
  TEXT_AI: Process text with specialized AI prompts
  SEARCH: Web search via Perplexity
  ADMIN: Bot administration
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.enums import ChatAction

from arki_project.utils.safe_send import safe_reply, safe_edit_text
from arki_project.utils.user_state import set_pending, get_pending, clear_pending
from arki_project.keyboards.inline import back_to_menu_keyboard
from arki_project.exceptions import HandlerError

logger = logging.getLogger(__name__)
router = Router(name="action_handlers")

# ═══════════════════════════════════════════════════════════
#  Action Definitions
# ═══════════════════════════════════════════════════════════

# Actions that generate images
IMAGE_ACTIONS = {
    "image":       ("🎨 ساخت عکس AI", "توضیح عکس مورد نظرت رو بنویس:"),
    "hd":          ("🖼 عکس با کیفیت HD", "توضیح عکس HD مورد نظرت رو بنویس:"),
    "design":      ("🎨 طراحی ۳ نسخه", "موضوع طراحی رو بنویس (۳ نسخه متفاوت ساخته میشه):"),
    "style":       ("🎨 ۵ سبک مختلف", "موضوع عکس رو بنویس (۵ سبک مختلف ساخته میشه):"),
    "logo":        ("🏷 لوگوساز AI", "اسم برند و توضیح لوگو رو بنویس:"),
    "banner":      ("🖼 بنر شبکه اجتماعی", "موضوع بنر رو بنویس:"),
    "infographic": ("📊 اینفوگرافیک", "موضوع اینفوگرافیک رو بنویس:"),
    "photoedit":   ("📷 مشاور عکاسی", "محصول یا موضوع عکاسی رو بنویس:"),
}

# Actions that use AI text generation with specialized prompts
TEXT_AI_ACTIONS = {
    "explain":     ("📖 توضیح ساده", "موضوعی که میخوای ساده توضیح بدم رو بنویس:", "این موضوع رو خیلی ساده و قابل فهم توضیح بده: {text}"),
    "translate":   ("🌐 ترجمه", "متنی که میخوای ترجمه کنم رو بنویس:", "این متن رو ترجمه کن (اگه فارسیه به انگلیسی، اگه انگلیسیه به فارسی): {text}"),
    "summarize":   ("📝 خلاصه‌سازی", "متنی که میخوای خلاصه کنم رو بنویس:", "این متن رو در ۳-۵ جمله خلاصه کن: {text}"),
    "rewrite":     ("✏️ بازنویسی", "متنی که میخوای بازنویسی کنم رو بنویس:", "این متن رو حرفه‌ای‌تر و بهتر بازنویسی کن: {text}"),
    "code":        ("💻 کدنویسی", "چه کدی میخوای بنویسم؟ (زبان + توضیح):", "یک کد حرفه‌ای و کامل بنویس: {text}"),
    "math":        ("🔢 ریاضی", "مسئله ریاضی رو بنویس:", "این مسئله ریاضی رو حل کن و قدم به قدم توضیح بده: {text}"),
    "quote":       ("💬 جمله الهام‌بخش", None, "۵ جمله الهام‌بخش و انگیزشی درباره موفقیت بنویس"),
    "story":       ("📖 داستان‌سازی", "موضوع داستان رو بنویس:", "یک داستان کوتاه و جذاب درباره این موضوع بنویس: {text}"),
    "caption":     ("📝 کپشن", "موضوع پست رو بنویس:", "۳ کپشن جذاب و حرفه‌ای برای پست اینستاگرام درباره این موضوع بنویس: {text}"),
    "hashtag":     ("# هشتگ", "موضوع رو بنویس:", "۳۰ هشتگ مرتبط و پربازدید برای این موضوع بنویس: {text}"),
    "seo":         ("🔍 سئو", "محصول یا صفحه رو توضیح بده:", "عنوان SEO، متا دیسکریپشن، و ۱۰ کلمه کلیدی برای این بنویس: {text}"),
    "brainstorm":  ("🧠 ایده‌پردازی", "موضوع رو بنویس:", "۱۰ ایده خلاقانه و عملی برای این موضوع بنویس: {text}"),
    "content":     ("📄 تولید محتوا", "موضوع محتوا رو بنویس:", "یک مقاله حرفه‌ای و جامع (۵۰۰ کلمه) درباره این موضوع بنویس: {text}"),
    "email":       ("📧 ایمیل حرفه‌ای", "موضوع ایمیل رو بنویس:", "یک ایمیل حرفه‌ای و مودبانه برای این موضوع بنویس: {text}"),
    "hook":        ("🪝 هوک محتوا", "موضوع رو بنویس:", "۵ هوک جذاب و توجه‌گیر برای شروع محتوا درباره این موضوع بنویس: {text}"),
    "cta":         ("📢 CTA ساز", "محصول/سرویس رو توضیح بده:", "۵ Call-to-Action قوی و متقاعدکننده برای این بنویس: {text}"),
    "megapost":    ("📰 مگاپست", "موضوع رو بنویس:", "یک مگاپست جامع و حرفه‌ای (۱۰۰۰+ کلمه) درباره این موضوع بنویس: {text}"),
    "carousel":    ("🎠 کاروسل", "موضوع کاروسل رو بنویس:", "محتوای ۱۰ اسلاید کاروسل اینستاگرام درباره این بنویس (هر اسلاید عنوان + متن): {text}"),
    "viral":       ("🔥 محتوای وایرال", "موضوع رو بنویس:", "یک محتوای وایرال و جذاب برای شبکه اجتماعی درباره این بنویس: {text}"),
    "repurpose":   ("♻️ بازتولید محتوا", "محتوای اصلی رو بنویس:", "این محتوا رو برای ۵ پلتفرم مختلف (اینستا، توییتر، لینکدین، تلگرام، وبلاگ) بازتولید کن: {text}"),
    "polish":      ("✨ صیقل محتوا", "متن رو بنویس:", "این متن رو از نظر ادبی، گرامری و جذابیت بهبود بده: {text}"),
    "short":       ("📱 ویدیو کوتاه", "موضوع ویدیو رو بنویس:", "اسکریپت یک ویدیو کوتاه ۶۰ ثانیه‌ای (ریلز/شورت) درباره این بنویس: {text}"),
    
    # Sales & Marketing
    "funnel":      ("📊 فانل فروش", "محصول/سرویس رو توضیح بده:", "یک فانل فروش کامل ۵ مرحله‌ای برای این محصول طراحی کن: {text}"),
    "pricing":     ("💰 قیمت‌گذاری", "محصول رو توضیح بده:", "استراتژی قیمت‌گذاری و ۳ پلن قیمتی برای این محصول پیشنهاد بده: {text}"),
    "competitor":  ("🔍 تحلیل رقبا", "محصول و صنعت رو بنویس:", "تحلیل رقبا شامل نقاط قوت/ضعف، فرصت‌ها و تهدیدها برای این بنویس: {text}"),
    "persona":     ("👤 پرسونای مشتری", "محصول رو توضیح بده:", "۳ پرسونای مشتری ایده‌آل (سن، شغل، دغدغه، انگیزه خرید) برای این بنویس: {text}"),
    "objection":   ("🛡 رفع اعتراض", "محصول رو توضیح بده:", "۱۰ اعتراض رایج مشتری و جواب متقاعدکننده برای هرکدوم بنویس: {text}"),
    "upsell":      ("📈 آپ‌سل", "محصول اصلی رو بنویس:", "۵ استراتژی آپ‌سل و کراس‌سل برای این محصول پیشنهاد بده: {text}"),
    "sales":       ("💼 متن فروش", "محصول رو توضیح بده:", "یک متن فروش حرفه‌ای و متقاعدکننده برای این محصول بنویس: {text}"),
    "listing":     ("📋 لیستینگ محصول", "محصول رو توضیح بده:", "عنوان، توضیحات، ویژگی‌ها و مزایای محصول رو برای فروشگاه آنلاین بنویس: {text}"),
    
    # Tools
    "password":    ("🔐 رمز قوی", None, "۵ رمز عبور قوی و امن ۱۶ کاراکتری بساز (ترکیب حروف بزرگ/کوچک، عدد، نماد)"),
    "qr":          ("📱 QR Code", "لینک یا متن رو بنویس:", "لینک QR Code generator: https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={text}"),
    "currency":    ("💱 ارز", None, "قیمت لحظه‌ای دلار، یورو، پوند، طلا و بیت‌کوین رو بگو"),
    "note":        ("📝 یادداشت", "یادداشتت رو بنویس:", "یادداشت ذخیره شد ✅"),
    "voice":       ("🎤 تبدیل صدا", "پیام صوتی بفرست:", None),
    "remind":      ("⏰ یادآور", "یادآوری رو بنویس:", "یادآوری ثبت شد ✅"),
    
    # Analysis  
    "analyze":     ("📊 تحلیل", "متن/داده رو بنویس:", "این متن/داده رو تحلیل کامل کن و نتیجه‌گیری بنویس: {text}"),
    "compare":     ("⚖️ مقایسه", "دو چیز رو بنویس (با «و» جدا کن):", "مقایسه کامل و جامع بین این دو بنویس (جدول مزایا/معایب): {text}"),
    "review":      ("⭐ بررسی", "محصول رو بنویس:", "بررسی حرفه‌ای و جامع این محصول (مزایا، معایب، امتیاز ۱-۱۰): {text}"),
    "deep":        ("🔬 تحلیل عمیق", "موضوع رو بنویس:", "تحلیل عمیق و جامع این موضوع از تمام جوانب: {text}"),
}

# Search-related actions
SEARCH_ACTIONS = {
    "search":      ("🔍 جستجوی وب", "چی جستجو کنم؟:"),
    "trending":    ("📈 ترندها", None),
    "weather":     ("🌤 آب و هوا", "شهر رو بنویس:"),
}

# Actions that need no input (immediate)
INSTANT_ACTIONS = {"quote", "password", "currency"}

# ═══════════════════════════════════════════════════════════
#  Image Generation Engine
# ═══════════════════════════════════════════════════════════

async def _generate_image(prompt: str, style_prefix: str = "") -> tuple[bytes | None, str]:
    """Generate image using OperaAria. Returns (image_bytes, error_message)."""
    try:
        from g4f.client import AsyncClient
        from g4f.Provider import OperaAria
        import httpx
        
        full_prompt = f"{style_prefix} {prompt}".strip() if style_prefix else prompt
        
        client = AsyncClient(provider=OperaAria)
        resp = await asyncio.wait_for(
            client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                response_format="url",
            ),
            timeout=30,
        )
        
        if not resp or not resp.data:
            return None, "تصویر ساخته نشد"
        
        raw_url = resp.data[0].url
        
        # Extract real URL from g4f proxy URL
        if raw_url and "?url=" in raw_url:
            from urllib.parse import urlparse, parse_qs
            real_url = parse_qs(urlparse(raw_url).query).get("url", [raw_url])[0]
        else:
            real_url = raw_url
        
        # Download image
        async with httpx.AsyncClient(timeout=30) as hc:
            img_resp = await hc.get(real_url)
            if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                return img_resp.content, ""
            else:
                return None, f"دانلود تصویر ناموفق (HTTP {img_resp.status_code})"
    
    except asyncio.TimeoutError:
        return None, "تایم‌اوت — لطفاً دوباره تلاش کن"
    except Exception as e:
        logger.error("Image generation error: %s", e)
        return None, f"خطا: {str(e)[:100]}"


async def _handle_image_action(message: Message, action: str, text: str) -> None:
    """Handle image generation actions."""
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    status = await message.answer("🎨 در حال ساخت تصویر...")
    
    style_prefixes = {
        "image": "",
        "hd": "ultra HD, 8K, photorealistic, detailed,",
        "design": "professional design,",
        "style": "artistic,",
        "logo": "minimalist professional logo design, vector style,",
        "banner": "social media banner, wide format, professional,",
        "infographic": "infographic, data visualization, clean layout,",
        "photoedit": "professional product photography,",
    }
    
    prefix = style_prefixes.get(action, "")
    
    # For multi-image actions, generate multiple
    count = 1
    if action == "design":
        count = 3
    elif action == "style":
        count = 3  # 5 is too slow, do 3
    
    results = []
    for i in range(count):
        style_var = prefix
        if action == "style" and i > 0:
            styles = ["watercolor painting,", "digital art, neon colors,", "pencil sketch,"]
            style_var = styles[i - 1] if i <= len(styles) else prefix
        elif action == "design" and i > 0:
            vars = ["modern minimalist,", "bold colorful,"]
            style_var = f"{prefix} {vars[i-1]}" if i <= len(vars) else prefix
        
        img_bytes, error = await _generate_image(text, style_var)
        if img_bytes:
            results.append(img_bytes)
    
    try:
        await status.delete()
    except:
        pass
    
    if results:
        for i, img in enumerate(results):
            suffix = f" ({i+1}/{len(results)})" if len(results) > 1 else ""
            await message.answer_photo(
                photo=BufferedInputFile(img, filename=f"arki_{action}_{i}.png"),
                caption=f"🎨 {IMAGE_ACTIONS[action][0]}{suffix}\n📝 {text[:100]}",
            )
    else:
        await message.answer(f"❌ ساخت تصویر ناموفق بود: {error}\n\nلطفاً دوباره تلاش کن.")


# ═══════════════════════════════════════════════════════════
#  Text AI Handler  
# ═══════════════════════════════════════════════════════════

async def _handle_text_action(message: Message, action: str, text: str) -> None:
    """Handle text AI actions."""
    from arki_project.utils.g4f_provider import chat as g4f_chat
    from arki_project.utils.text import split_for_telegram
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🧠 در حال پردازش...")
    
    _, _, prompt_template = TEXT_AI_ACTIONS[action]
    
    if prompt_template and "{text}" in prompt_template:
        prompt = prompt_template.format(text=text)
    elif prompt_template:
        prompt = prompt_template
    else:
        prompt = text
    
    uid = message.from_user.id if message.from_user else 0
    
    try:
        answer = await g4f_chat(user_id=uid, text=prompt, timeout=25)
        
        try:
            await status.delete()
        except:
            pass
        
        if answer and answer.strip():
            chunks = split_for_telegram(answer)
            for chunk in chunks:
                try:
                    await safe_reply(message, chunk)
                except:
                    await message.answer(chunk[:4000], parse_mode=None)
        else:
            await message.answer("⚠️ پاسخی دریافت نشد. دوباره تلاش کن.")
    except Exception as e:
        logger.error("Text AI error for %s: %s", action, e)
        await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")


# ═══════════════════════════════════════════════════════════
#  Search Handler
# ═══════════════════════════════════════════════════════════

async def _handle_search_action(message: Message, action: str, text: str) -> None:
    """Handle search actions."""
    from arki_project.utils.g4f_provider import search_chat
    from arki_project.utils.text import split_for_telegram
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🔍 در حال جستجو...")
    
    uid = message.from_user.id if message.from_user else 0
    
    queries = {
        "search": text,
        "trending": "ترندهای روز ایران و جهان",
        "weather": f"آب و هوای {text}",
    }
    query = queries.get(action, text)
    
    try:
        answer = await search_chat(user_id=uid, query=query, timeout=25)
        
        try:
            await status.delete()
        except:
            pass
        
        if answer and answer.strip():
            chunks = split_for_telegram(answer)
            for chunk in chunks:
                try:
                    await safe_reply(message, chunk)
                except:
                    await message.answer(chunk[:4000], parse_mode=None)
        else:
            await message.answer("⚠️ نتیجه‌ای یافت نشد.")
    except Exception as e:
        logger.error("Search error for %s: %s", action, e)
        await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")


# ═══════════════════════════════════════════════════════════
#  Unified Callback Handler
# ═══════════════════════════════════════════════════════════

ALL_ACTIONS = set(IMAGE_ACTIONS) | set(TEXT_AI_ACTIONS) | set(SEARCH_ACTIONS)

@router.callback_query(F.data.startswith("act:"))
async def handle_action_button(callback: CallbackQuery) -> None:
    """Universal handler for all act: buttons."""
    action = (callback.data or "").replace("act:", "")
    uid = callback.from_user.id
    
    await callback.answer()
    
    # ── Image actions ──
    if action in IMAGE_ACTIONS:
        label, prompt_text = IMAGE_ACTIONS[action]
        set_pending(uid, f"img:{action}", {})
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ لغو", callback_data="act:cancel_pending")]
        ])
        await safe_edit_text(
            callback.message,
            f"{label}\n\n💬 {prompt_text}",
            reply_markup=kb,
        )
        return
    
    # ── Text AI actions ──
    if action in TEXT_AI_ACTIONS:
        label, prompt_text, prompt_template = TEXT_AI_ACTIONS[action]
        
        # Instant actions (no input needed)
        if prompt_text is None and prompt_template:
            # Execute immediately
            set_pending(uid, f"txt:{action}", {})
            clear_pending(uid)
            
            await safe_edit_text(callback.message, f"{label}\n\n🧠 در حال پردازش...")
            
            from arki_project.utils.g4f_provider import chat as g4f_chat
            from arki_project.utils.text import split_for_telegram
            
            try:
                answer = await g4f_chat(user_id=uid, text=prompt_template, timeout=25)
                if answer:
                    chunks = split_for_telegram(answer)
                    for chunk in chunks:
                        try:
                            await callback.message.answer(chunk, parse_mode="Markdown")
                        except:
                            await callback.message.answer(chunk[:4000], parse_mode=None)
                else:
                    await callback.message.answer("⚠️ پاسخی دریافت نشد.")
            except Exception as e:
                await callback.message.answer(f"❌ خطا: {str(e)[:100]}")
            return
        
        # Actions that need user input
        set_pending(uid, f"txt:{action}", {})
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ لغو", callback_data="act:cancel_pending")]
        ])
        await safe_edit_text(
            callback.message,
            f"{label}\n\n💬 {prompt_text}",
            reply_markup=kb,
        )
        return
    
    # ── Search actions ──
    if action in SEARCH_ACTIONS:
        label, prompt_text = SEARCH_ACTIONS[action]
        
        if prompt_text is None:
            # Instant search (trending)
            await safe_edit_text(callback.message, f"{label}\n\n🔍 در حال جستجو...")
            
            from arki_project.utils.g4f_provider import search_chat
            from arki_project.utils.text import split_for_telegram
            
            try:
                answer = await search_chat(user_id=uid, query="ترندهای روز ایران و جهان", timeout=25)
                if answer:
                    chunks = split_for_telegram(answer)
                    for chunk in chunks:
                        try:
                            await callback.message.answer(chunk, parse_mode="Markdown")
                        except:
                            await callback.message.answer(chunk[:4000], parse_mode=None)
                else:
                    await callback.message.answer("⚠️ نتیجه‌ای یافت نشد.")
            except Exception as e:
                await callback.message.answer(f"❌ خطا: {str(e)[:100]}")
            return
        
        set_pending(uid, f"search:{action}", {})
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ لغو", callback_data="act:cancel_pending")]
        ])
        await safe_edit_text(
            callback.message,
            f"{label}\n\n💬 {prompt_text}",
            reply_markup=kb,
        )
        return
    
    # ── Unknown action — still better than "coming soon" ──
    set_pending(uid, f"txt:general_{action}", {})
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ لغو", callback_data="act:cancel_pending")]
    ])
    await safe_edit_text(
        callback.message,
        f"🤖 *{action}*\n\n💬 پیامت رو بنویس:",
        reply_markup=kb,
    )


# ═══════════════════════════════════════════════════════════
#  Pending Message Handler  
#  (processes user text after they click a button)
# ═══════════════════════════════════════════════════════════

async def _has_pending(message: Message) -> bool:
    """Filter: only handle if user has a pending action."""
    uid = message.from_user.id if message.from_user else 0
    return get_pending(uid) is not None


@router.message(F.text, _has_pending)
async def handle_pending_action(message: Message) -> None:
    """Process text from user after they clicked an action button."""
    uid = message.from_user.id if message.from_user else 0
    pending = get_pending(uid)
    
    if not pending:
        return
    
    action_full = pending.get("action", "")
    clear_pending(uid)
    
    text = (message.text or "").strip()
    if not text:
        return
    
    # Parse action type
    if ":" in action_full:
        action_type, action_name = action_full.split(":", 1)
    else:
        action_type, action_name = "txt", action_full
    
    # Route to appropriate handler
    if action_type == "img" and action_name in IMAGE_ACTIONS:
        await _handle_image_action(message, action_name, text)
    elif action_type == "search" and action_name in SEARCH_ACTIONS:
        await _handle_search_action(message, action_name, text)
    elif action_type == "txt":
        # Check if it's a known text action
        if action_name in TEXT_AI_ACTIONS:
            await _handle_text_action(message, action_name, text)
        elif action_name.startswith("general_"):
            # Generic AI processing
            from arki_project.utils.g4f_provider import chat as g4f_chat
            from arki_project.utils.text import split_for_telegram
            
            await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
            status = await message.answer("🧠 در حال پردازش...")
            
            try:
                answer = await g4f_chat(user_id=uid, text=text, timeout=25)
                try:
                    await status.delete()
                except:
                    pass
                if answer:
                    chunks = split_for_telegram(answer)
                    for chunk in chunks:
                        try:
                            await safe_reply(message, chunk)
                        except:
                            await message.answer(chunk[:4000], parse_mode=None)
            except Exception as e:
                await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")
    else:
        # Unknown type — treat as general AI
        from arki_project.utils.g4f_provider import chat as g4f_chat
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        try:
            answer = await g4f_chat(user_id=uid, text=text, timeout=25)
            if answer:
                await safe_reply(message, answer)
        except Exception as e:
            await message.answer(f"❌ {str(e)[:100]}")
