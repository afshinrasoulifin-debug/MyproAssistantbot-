
"""sales_engine_pkg.cmd_ads_group — sub-module of sales_engine"""

from __future__ import annotations
from arki_project.exceptions import HandlerError

# ═══ TITANIUM v29.0 Integration ═══

__all__ = ['cmd_ads', 'cmd_social', 'cmd_swipe', 'cmd_competitor', 'cmd_megapost']

async def cmd_ads(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/ads")

    if not raw:
        await safe_reply(message, "📣 *تبلیغ‌ساز حرفه‌ای — Ad Copy:*\n\n"
            "`/ads [محصول] | [هدف] | [بودجه €]`\n\n"
            "*مثال:*\n"
            "`/ads concrete candle | sales | 50`\n"
            "`/ads new collection | awareness | 20`\n\n"
            "_تبلیغات آماده برای:_\n"
            "📸 Instagram/Facebook Ads\n"
            "📌 Pinterest Ads\n"
            "🔍 Etsy Ads\n"
            "🎵 TikTok Ads")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    objective = parts[1] if len(parts) > 1 else "sales"
    budget = parts[2] if len(parts) > 2 else "50"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a paid advertising expert for small e-commerce brands. "
                "You create high-converting ad copy with minimal budgets. "
                "You know Meta Ads, Pinterest Ads, Etsy Ads, and TikTok Ads. "
                "Write in Persian with ready-to-use English and Finnish ad copy."
            ),
            user_prompt=(
                "Create AD COPY for all major platforms:\n"
                f"Product: {product}\n"
                f"Objective: {objective}\n"
                f"Budget: €{budget}/month\n"
                f"{brand_ctx(message.chat.id)}\n"
                "📸 *INSTAGRAM/FACEBOOK ADS:*\n"
                "3 ad variations:\n"
                "- Primary text (125 chars)\n"
                "- Headline\n"
                "- Description\n"
                "- CTA button suggestion\n"
                "- Audience targeting recommendation\n"
                "- Image direction\n\n"
                "📌 *PINTEREST ADS:*\n"
                "2 promoted pin variations:\n"
                "- Pin title\n"
                "- Pin description\n"
                "- Keywords to target\n"
                "- Board strategy\n\n"
                "🔍 *ETSY ADS:*\n"
                "- Budget allocation advice\n"
                "- Which listings to promote\n"
                "- Tag optimization for ads\n\n"
                "🎵 *TIKTOK/REELS AD:*\n"
                "- 15-sec ad script\n"
                "- Hook ideas\n"
                "- Trending format to use\n\n"
                "💡 *BUDGET ALLOCATION:*\n"
                f"How to split €{budget}/month across platforms for maximum ROI\n\n"
                "📊 *TARGETING:*\n"
                "Detailed audience targeting for each platform\n"
                "Lookalike audience strategy\n"
                "Retargeting plan\n\n"
                "All ad copy in BOTH English and Finnish."
            ),
        )
        await _send_result(message, f"📣 *تبلیغات — {product}:*", body)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))

# ═══════════════════════════════════════════════
# /social — Social Proof System
# ═══════════════════════════════════════════════

@router.message(Command("social"))
async def cmd_social(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/social")

    if not raw:
        await safe_reply(message, "⭐ *سیستم اعتمادسازی — Social Proof:*\n\n"
            "`/social [محصول]`\n\n"
            "*مثال:*\n"
            "`/social handmade concrete candle`\n\n"
            "_تولید می‌کنه:_\n"
            "⭐ قالب درخواست نظر از مشتری\n"
            "📸 راهنمای UGC (محتوای کاربری)\n"
            "💬 نمونه پاسخ به نظرات\n"
            "🏷 Highlight/استوری اعتمادسازی\n"
            "📊 Trust badge و گارانتی")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a social proof and trust-building expert for e-commerce brands. "
                "You know how to leverage reviews, UGC, and testimonials to boost sales. "
                "Write in Persian with English/Finnish templates."
            ),
            user_prompt=(
                f"Create a COMPLETE social proof strategy for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "⭐ *1. REVIEW COLLECTION:*\n"
                "- Follow-up message after purchase (EN + FI)\n"
                "- Review request email template\n"
                "- Incentive ideas (without violating Etsy rules)\n"
                "- Where to collect: Etsy, Google, Instagram\n\n"
                "📸 *2. UGC (User-Generated Content):*\n"
                "- How to encourage customers to share photos\n"
                "- Hashtag for UGC collection\n"
                "- Repost template/caption\n"
                "- UGC campaign idea\n\n"
                "💬 *3. RESPONSE TEMPLATES:*\n"
                "- Reply to positive review (EN + FI)\n"
                "- Reply to negative review (EN + FI)\n"
                "- Reply to questions (EN + FI)\n"
                "- DM response to compliments\n\n"
                "📱 *4. INSTAGRAM HIGHLIGHTS:*\n"
                "- Highlight categories for trust\n"
                "- Content for each highlight\n"
                "- Story templates for reviews/testimonials\n\n"
                "🛡 *5. TRUST SIGNALS:*\n"
                "- Bio elements that build trust\n"
                "- Story highlights to create\n"
                "- Etsy shop 'About' section\n"
                "- Packaging inserts that encourage sharing\n\n"
                "📊 *6. NUMBERS STRATEGY:*\n"
                "- How to showcase social proof (X happy customers)\n"
                "- Milestone celebration posts\n"
                "- Behind-the-numbers content"
            ),
        )
        await _send_result(message, f"⭐ *اعتمادسازی — {raw}:*", body)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))

# ═══════════════════════════════════════════════
# /swipe — Ready-to-Use Caption/Bio/CTA Library
# ═══════════════════════════════════════════════

@router.message(Command("swipe"))
async def cmd_swipe(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/swipe")
    category = raw.lower() if raw else ""

    categories = {
        "bio": "Instagram bio variations",
        "cta": "Call-to-action phrases",
        "hook": "Post/Reel opening hooks",
        "close": "Closing lines for captions",
        "dm": "DM response templates",
        "faq": "FAQ answers for customers",
    }

    if category not in categories:
        lines = "\n".join(f"📝 `{k}` — {v}" for k, v in categories.items())
        await safe_reply(message, "📚 *کتابخانه آماده — Swipe File:*\n\n"
            "`/swipe [دسته]`\n\n"
            f"{lines}\n\n"
            "*مثال:*\n"
            "`/swipe bio`\n"
            "`/swipe hook`\n"
            "`/swipe cta`\n\n"
            "_مجموعه آماده کپی‌پیست!_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    prompts = {
        "bio": (
            "Create 15 Instagram bio variations for a handmade candle brand in Finland.\n"
            "Each bio: max 150 chars, include: value prop, location, CTA.\n"
            "5 in English, 5 in Finnish, 5 bilingual.\n"
            "Also provide: best link-in-bio structure, emojis to use."
        ),
        "cta": (
            "Create 30 call-to-action phrases for an artisan candle brand.\n"
            "Categories: Shop now, Learn more, Share, Save, DM, Comment, Follow.\n"
            "In both English and Finnish.\n"
            "For: Instagram captions, Stories, Etsy listings, emails."
        ),
        "hook": (
            "Create 30 scroll-stopping opening hooks for Instagram posts/Reels.\n"
            "Categories: Question, Statement, Controversy, Secret, Number, Story.\n"
            "All tailored for handmade candles & home decor.\n"
            "In English. Mark which work best for Reels vs Posts."
        ),
        "close": (
            "Create 25 caption closing lines that drive engagement.\n"
            "Categories: Question, Poll, Challenge, Emotion, Urgency.\n"
            "In English and Finnish.\n"
            "For handmade candles & decor brand."
        ),
        "dm": (
            "Create 20 DM response templates for a candle business.\n"
            "Scenarios: new inquiry, price question, custom order, shipping, "
            "collaboration request, complaint, compliment, wholesale inquiry.\n"
            "In English and Finnish."
        ),
        "faq": (
            "Create 15 FAQ answers for a handmade candle business.\n"
            "Topics: materials, burn time, shipping, custom orders, scents, "
            "care instructions, wholesale, returns, gift wrapping.\n"
            "In English and Finnish. Ready to paste into Etsy FAQ and Instagram."
        ),
    }

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a copywriting expert for artisan brands. "
                "Create a ready-to-use swipe file library. "
                "Every item must be polished, on-brand, and ready to copy-paste."
            ),
            user_prompt=f"{prompts[category]}\n{brand_ctx(message.chat.id)}\n"
                        "Make everything READY TO COPY-PASTE. Number each item.",
        )
        emoji_map = {"bio": "🔤", "cta": "🔘", "hook": "🪝", "close": "✍️", "dm": "💬", "faq": "❓"}
        await _send_result(
            message,
            f"{emoji_map.get(category, '📚')} *Swipe File — {categories[category]}:*",
            body,
        )
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))

# ═══════════════════════════════════════════════
# /competitor — Deep Competitor SWOT
# ═══════════════════════════════════════════════

@router.message(Command("competitor"))
async def cmd_competitor(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/competitor")

    if not raw:
        await safe_reply(message, "🔍 *تحلیل عمیق رقبا — SWOT Analysis:*\n\n"
            "`/competitor [نیچ یا رقیب]`\n\n"
            "*مثال:*\n"
            "`/competitor concrete candle etsy sellers`\n"
            "`/competitor handmade candle market Finland`\n\n"
            "_تحلیل SWOT + فرصت‌ها + استراتژی مقابله_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🔍 دارم تحلیل عمیق بازار انجام می‌دم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a competitive intelligence analyst specializing in handmade/artisan "
                "e-commerce on Etsy, Amazon Handmade, and Nordic marketplaces (Tori.fi). "
                "You provide data-driven SWOT analysis with specific, actionable strategies — "
                "not generic advice. You understand the Finnish/Nordic home decor market, "
                "candle industry trends, and what differentiates winners from losers. "
                "Write in Persian with English competitive terms and benchmarks."
            ),
            user_prompt=(
                f"Do a DEEP competitive analysis for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "📊 *1. MARKET OVERVIEW:*\n"
                "- Market size and growth\n"
                "- Key players\n"
                "- Price ranges\n"
                "- Demand trends\n\n"
                "🏢 *2. TOP 5 COMPETITOR PROFILES:*\n"
                "For each: strengths, weaknesses, pricing, USP, social media presence\n\n"
                "📋 *3. SWOT ANALYSIS (your brand):*\n"
                "- Strengths (what you do well)\n"
                "- Weaknesses (gaps to fix)\n"
                "- Opportunities (market gaps to exploit)\n"
                "- Threats (risks to watch)\n\n"
                "🎯 *4. COMPETITIVE ADVANTAGES:*\n"
                "- USP ideas for differentiation\n"
                "- Blue ocean opportunities\n"
                "- Underserved customer segments\n\n"
                "🗺 *5. BATTLE PLAN:*\n"
                "- Short-term (this month): 5 actions\n"
                "- Medium-term (3 months): 5 milestones\n"
                "- Long-term (6-12 months): 3 strategic goals\n\n"
                "💡 *6. STEAL-WORTHY IDEAS:*\n"
                "- 5 things competitors do well that you should adopt\n"
                "- 5 things they do poorly that you can exploit"
            ),
            temp=0.7,
        )
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"🔍 *تحلیل رقبا — {raw}:*", body)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))

# ═══════════════════════════════════════════════
# /megapost — Generate pro photo + poster + all content
# ═══════════════════════════════════════════════

@router.message(Command("megapost"))
async def cmd_megapost(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/megapost")

    if not raw:
        await safe_reply(message, "💎 *مگاپست — حداکثر محتوا از ۱ محصول:*\n\n"
            "`/megapost [محصول] | [قیمت €] | [توضیح]`\n\n"
            "*مثال:*\n"
            "`/megapost Concrete Candle | 35 | Soy wax, lavender, handmade`\n\n"
            "*تولید می‌کنه:*\n"
            "📸 ۴ عکس حرفه‌ای (۴ استایل مختلف)\n"
            "🎨 ۳ پوستر فروش\n"
            "✍️ ۵ کپشن EN + ۵ کپشن FI\n"
            "🏷 ۵۰ هشتگ\n"
            "📋 آگهی Etsy + Tori.fi\n"
            "🎬 اسکریپت ریلز\n"
            "📧 ایمیل معرفی\n"
            "📅 برنامه ۷ روزه\n\n"
            "_بمب اتمی محتوا! 💣_")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    price = parts[1] if len(parts) > 1 else ""
    desc = parts[2] if len(parts) > 2 else ""

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("💎 *مگاپست* — ساخت بمب محتوا شروع شد... (چند مرحله)\n\n⏳ مرحله ۱: عکس‌های حرفه‌ای...")

    try:
        # ── Step 1: Generate 4 professional photos ──
        styles = [
            ("dark", "dark moody, dramatic side lighting, dark walnut wood, shadows, Kinfolk style"),
            ("nordic", "Scandinavian, light birch wood, white grey tones, soft northern light, Finnish interior"),
            ("cozy", "cozy hygge, warm blanket, fairy lights bokeh, autumn vibes, intimate"),
            ("flat", "flat lay top-down, concrete background, dried petals, matches, Instagram flatlay"),
        ]

        photos_sent = 0
        for style_name, style_desc in styles:
            try:
                prompt = (
                    f"Professional product photography of {product}, "
                    "handmade artisan candle in textured raw concrete vessel, "
                    f"natural soy wax, {style_desc}, "
                    "8k resolution, commercial grade, magazine cover quality"
                )
                encoded = urllib.parse.quote(prompt)
                img_url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    f"?width=1024&height=1024&model=flux&seed={random.randint(1, 99999)}"
                )
                # v10.1: Route through TITANIUM shielded client
                if _TITANIUM_ACTIVE:
                    ti_resp = await shielded_get(img_url, timeout=60.0)
                    if ti_resp.success and ti_resp.status_code == 200 and len(ti_resp.content) > 1000:
                        photo = BufferedInputFile(ti_resp.content, filename=f"mega_{style_name}.png")
                        style_emojis = {"dark": "🌑", "nordic": "🇫🇮", "cozy": "🕯", "flat": "📐"}
                        await message.answer_photo(
                            photo=photo,
                            caption=f"📸 {style_emojis.get(style_name, '📸')} *{style_name}* — {product}",
                            parse_mode="Markdown",
                        )
                        photos_sent += 1
                    continue
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    resp = await client.get(img_url)
                    if resp.status_code == 200:
                        photo = BufferedInputFile(resp.content, filename=f"mega_{style_name}.png")
                        style_emojis = {"dark": "🌑", "nordic": "🇫🇮", "cozy": "🕯", "flat": "📐"}
                        await message.answer_photo(
                            photo=photo,
                            caption=f"📸 {style_emojis.get(style_name, '📸')} *{style_name}* — {product}",
                            parse_mode="Markdown",
                        )
                        photos_sent += 1
            except HandlerError as exc:
                logger.warning("Megapost photo %s failed: %s", style_name, exc)

        # ── Step 2: Generate posters ──
        await safe_edit_text(status, "💎 مرحله ۲: پوسترها...")
        try:
            from arki_project.utils.poster_gen import generate_poster
            for tpl in ["sale", "product", "minimal"]:
                try:
                    img_bytes = generate_poster(tpl, product, price, "", desc)
                    photo = BufferedInputFile(img_bytes, filename=f"mega_poster_{tpl}.png")
                    await message.answer_photo(photo=photo, caption=f"🎨 پوستر {tpl}")
                except HandlerError as e:
                    logger.debug("Suppressed: %s", e)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)

        # ── Step 3: AI content (everything) ──
        await safe_edit_text(status, "💎 مرحله ۳: تولید متن‌ها...")

        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a complete marketing team in one: copywriter, social media manager, "
                "SEO expert, email marketer, and content strategist. "
                "Create the ULTIMATE content package. Write in English and Finnish."
            ),
            user_prompt=(
                "Create the ULTIMATE MEGA CONTENT PACKAGE for:\n"
                f"Product: {product}\n"
                f"Price: €{price}\n"
                f"Description: {desc}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Generate ALL:\n\n"
                "═══ 5 INSTAGRAM CAPTIONS (EN) ═══\n"
                "Story, Educational, Sale, Aesthetic, Engagement styles\n\n"
                "═══ 5 INSTAGRAM CAPTIONS (FI) ═══\n"
                "Same 5 styles in Finnish\n\n"
                "═══ 50 HASHTAGS ═══\n"
                "20 English popular + 15 English niche + 15 Finnish\n\n"
                "═══ ETSY LISTING (Full) ═══\n"
                "SEO title + description + 13 tags + materials\n\n"
                "═══ TORI.FI LISTING (Finnish) ═══\n"
                "Otsikko + Kuvaus + Hinta\n\n"
                "═══ REEL SCRIPT ═══\n"
                "30-sec, scene-by-scene, with hook\n\n"
                "═══ EMAIL ═══\n"
                "Subject + body (EN) for newsletter\n\n"
                "═══ 7-DAY POSTING PLAN ═══\n"
                "Which caption, when, where, what photo\n\n"
                "Everything READY TO COPY-PASTE."
            ),
        )

        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"💎 *مگاپست کامل — {product}:*", body)

        # Summary
        await safe_reply(message, "✅ *مگاپست تمام شد!*\n\n"
            f"📸 {photos_sent} عکس حرفه‌ای\n"
            "🎨 ۳ پوستر\n"
            "✍️ ۱۰ کپشن (EN+FI)\n"
            "🏷 ۵۰ هشتگ\n"
            "📋 آگهی Etsy + Tori.fi\n"
            "🎬 اسکریپت ریلز\n"
            "📧 ایمیل\n"
            "📅 برنامه ۷ روزه\n\n"
            "_همه چیز آماده‌ — فقط پست کن! 🚀_")

    except HandlerError as exc:
        logger.error("Megapost failed: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))



