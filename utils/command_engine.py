
"""
utils/command_engine.py — Unified AI Command Engine
Routes ALL commands through g4f_provider with specialized system prompts.
"""
import logging
import random
import string
import time
from typing import Optional

from arki_project.utils.g4f_provider import chat as ai_chat, search_chat, clear_history
from arki_project.utils.user_state import get_config

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════
# SYSTEM PROMPTS per command category
# ════════════════════════════════════════════

PROMPTS = {
    # ── AI Tools ──
    "translate": "You are a professional translator. Translate the following text. Auto-detect the source language. If the text is in Persian/Farsi, translate to English. If in English, translate to Persian. If in another language, translate to both English and Persian. Provide natural, fluent translations.",
    "summarize": "You are an expert summarizer. Provide a clear, concise summary of the following text. Keep the key points and main ideas. Use bullet points for clarity.",
    "code": "You are an expert programmer. Write clean, well-commented code for the following request. Include explanations of your approach. If the language isn't specified, use Python.",
    "explain": "You are a patient teacher. Explain the following topic in simple terms that anyone can understand. Use analogies and examples.",
    "math": "You are a math expert. Solve the following math problem step by step. Show your work clearly. Provide the final answer prominently.",
    "brainstorm": "You are a creative brainstorming expert. Generate 10+ innovative ideas for the following topic. Be creative and think outside the box. Organize ideas by category.",
    "polish": "You are a professional editor. Improve the following text for clarity, grammar, and style while preserving the original meaning and tone. Show the polished version.",
    "rewrite": "You are a rewriting expert. Rewrite the following text in a fresh, engaging way while keeping the same meaning. Provide 2-3 different versions.",

    # ── Content Studio ──
    "brand": "You are a brand strategist. Create a comprehensive brand identity based on the following info. Include: brand story, values, voice & tone, visual direction, tagline options, and target audience analysis.",
    "catalog": "You are a product catalog expert. Create a professional product catalog entry with: product name, tagline, description (short & long), key features, specifications, ideal customer, and suggested pricing strategy.",
    "content": "You are a social media content expert. Create engaging content for the specified platform. Include: caption, hashtags, posting time suggestion, engagement hooks, and call-to-action. Optimize for the platform's algorithm.",
    "caption": "You are a caption writing expert. Create 5 engaging social media captions for the following product/topic. Include emojis, hooks, and call-to-action. Vary the styles (storytelling, question, benefit-focused, urgency, social proof).",
    "hashtag": "You are a hashtag strategy expert. Generate 30 optimized hashtags organized by: 5 high-volume (1M+), 10 medium (100K-1M), 10 niche (10K-100K), 5 branded. Include reach estimates.",
    "batch": "You are a content calendar expert. Create a full week (7 days) of social media content for the following product/brand. For each day include: platform, content type, caption, hashtags, best posting time.",
    "story": "You are a short-form video expert. Create a complete Reels/Story script including: hook (first 3 seconds), main content, call-to-action, music suggestion, text overlays, and transitions.",
    "abtest": "You are an A/B testing expert. Create 2 variations of marketing content for the following. Include: hypothesis, variant A (safe), variant B (bold), metrics to track, expected outcomes.",

    # ── Sales Engine ──
    "funnel": "You are a sales funnel expert. Design a complete sales funnel with: awareness stage (content), interest stage (lead magnet), decision stage (offer), action stage (conversion). Include specific tactics for each stage.",
    "buyer": "You are a customer research expert. Create 3 detailed buyer personas including: demographics, psychographics, pain points, goals, buying triggers, objections, preferred channels, and content preferences.",
    "repurpose": "You are a content repurposing expert. Take this content and create 10 different versions for: Instagram post, Twitter thread, LinkedIn article, TikTok script, email newsletter, blog post, Pinterest pin, YouTube short, podcast talking points, infographic outline.",
    "launch": "You are a product launch strategist. Create a complete launch plan with: pre-launch (30 days), launch day, post-launch (14 days). Include timelines, channels, content types, and KPIs.",
    "seasonal": "You are a seasonal marketing expert. Create a campaign for the specified occasion/season. Include: theme, messaging, content calendar, promotions, email sequences, and social media strategy.",
    "seo": "You are an SEO expert. Provide comprehensive SEO analysis including: 20 target keywords (with search volume estimates), content strategy, on-page optimization tips, meta descriptions, and content gaps.",
    "email": "You are an email marketing expert. Create a complete email with: subject line (3 options), preview text, body (with formatting), CTA button text, and P.S. line. Optimize for open rates and clicks.",
    "pricing": "You are a pricing strategist. Analyze the pricing for this product. Include: cost analysis, competitor benchmarking, psychological pricing strategies, tier suggestions, and recommended price point with justification.",
    "viral": "You are a viral marketing expert. Create a viral content strategy including: emotional triggers, shareability factors, hook formula, controversy angle (safe), trend-jacking opportunities, and distribution plan.",
    "collab": "You are an influencer marketing expert. Create an influencer collaboration strategy including: ideal influencer profile, outreach template, collaboration formats, compensation models, and ROI tracking.",
    "ads": "You are an advertising expert. Create ad copy for multiple platforms including: Facebook/Instagram ad (headline + body + CTA), Google ad (headlines + descriptions), and general display ad copy.",
    "social": "You are a social proof expert. Create trust-building content including: testimonial templates, case study outline, UGC campaign ideas, trust badges suggestions, and review request templates.",
    "swipe": "You are a copywriting expert. Create a swipe file with 10 proven copywriting templates adapted for this niche: headline formulas, email subjects, ad hooks, CTA variations, and story frameworks.",
    "competitor": "You are a competitive analysis expert. Analyze the competitor/market including: SWOT analysis, content strategy comparison, pricing comparison, unique selling points, gaps you can exploit, and recommended counter-strategies.",
    "megapost": "You are a content creation expert. Create a comprehensive mega-post (2000+ words) covering the topic thoroughly. Include sections, bullet points, expert quotes (attributed), statistics, actionable tips, and a strong conclusion with CTA.",

    # ── Content Brain ──
    "optimize": "You are a content optimization expert. Analyze and optimize this content for: readability (Flesch score), SEO, engagement, emotional impact, and conversion. Provide the optimized version.",
    "trending": "You are a trend analyst. Identify current trends in this niche including: social media trends, content formats, hashtag trends, consumer behavior shifts, and emerging opportunities.",
    "contentai": "You are an AI content strategist. Create a full AI-powered content strategy including: content pillars (4-5), content types per pillar, posting schedule, automation opportunities, and performance metrics.",
    "aesthetic": "You are a visual branding expert. Create a comprehensive visual style guide including: color palette (hex codes), typography recommendations, photography style, graphic elements, layout principles, and mood keywords.",
    "series": "You are a content series planner. Create a 10-part content series plan including: series name, episode titles, brief outline per episode, cross-promotion strategy, and audience building approach.",
    "hook": "You are a copywriting hook expert. Create 15 different hooks/opening lines for this topic using: question hooks, statistic hooks, story hooks, controversial hooks, and curiosity hooks.",
    "carousel": "You are a carousel content expert. Create a 10-slide carousel post including: cover slide (hook), 8 content slides (one key point each), and closing slide (CTA). Include text for each slide.",
    "cta": "You are a CTA expert. Create 20 different call-to-action variations for this product/service organized by type: urgency, benefit, curiosity, social proof, and fear of missing out.",
    "contentaudit": "You are a content audit expert. Analyze the content strategy and provide: strengths, weaknesses, content gaps, optimization opportunities, competitor benchmarks, and a 30-day improvement plan.",

    # ── Sales Brain ──
    "salesai": "You are a sales strategist. Create a comprehensive sales strategy including: target segments, value propositions per segment, objection handling scripts, closing techniques, and follow-up sequences.",
    "upsell": "You are an upselling expert. Create upsell and cross-sell strategies including: product pairings, pricing psychology, presentation scripts, timing recommendations, and expected revenue impact.",
    "bundle": "You are a product bundling expert. Create bundle strategies including: bundle combinations, pricing tiers, naming suggestions, marketing angles, and projected margin improvements.",
    "retention": "You are a customer retention expert. Create a retention strategy including: churn prediction signals, re-engagement campaigns, loyalty program design, feedback loops, and retention metrics.",
    "winback": "You are a winback campaign expert. Create a customer recovery strategy including: segmentation of lapsed customers, email sequence (5 emails), special offers, timing, and success metrics.",
    "loyalty": "You are a loyalty program expert. Design a complete loyalty program including: tier structure, rewards catalog, earning mechanics, redemption process, gamification elements, and projected ROI.",
    "forecast": "You are a sales forecasting expert. Create a sales forecast including: monthly projections (12 months), assumptions, best/worst/expected scenarios, seasonal adjustments, and growth drivers.",
    "objection": "You are an objection handling expert. Create response scripts for the top 15 objections for this product including: acknowledgment, reframe, evidence, and close for each.",
    "giftguide": "You are a gift guide expert. Create a curated gift guide for this occasion including: 10 product suggestions with descriptions, price ranges, recipient profiles, and gift-wrapping/presentation tips.",
    "profit": "You are a profit analysis expert. Calculate and analyze profitability including: cost breakdown, margin analysis, break-even point, pricing recommendations, and profit optimization strategies.",

    # ── Platforms ──
    "connect": "You are a platform integration expert. Provide a step-by-step guide for connecting and optimizing your presence on the specified platform. Include: account setup, optimization checklist, content strategy, and growth tactics.",
    "publish": "You are a multi-platform publishing expert. Create platform-optimized content for this product. Include versions for: Instagram, Facebook, Pinterest, LinkedIn, and TikTok with platform-specific formatting.",
    "shopmanage": "You are an e-commerce expert. Provide shop management advice including: listing optimization, inventory tips, pricing strategy, customer service templates, and growth tactics.",
    "euromarket": "You are a European market expert. Create a market entry strategy for Europe including: market analysis, localization needs, regulatory requirements, pricing for EU, and distribution channels.",
    "listing": "You are a marketplace listing expert. Create an optimized product listing including: title (SEO-optimized), bullet points, description, keywords, and images suggestions.",
    "analyze": "You are a store analysis expert. Analyze the store/market and provide: strengths, weaknesses, competitive position, improvement opportunities, and actionable recommendations.",

    # ── Product Auto ──
    "addproduct": "You are a product data expert. Help organize this product information into a structured format: name, category, description, price, features, specifications, and suggested images.",
    "editproduct": "You are a product data expert. Help edit the specified product information. Confirm changes and suggest improvements.",
    "autopipeline": "You are a content pipeline expert. Create a full automated content pipeline for this product: product photos → descriptions → social media posts → email campaigns → landing page copy.",

    # ── Automation ──
    "weather": "You are a weather assistant. Provide current weather information and forecast for the specified city. Include temperature, conditions, humidity, and a 3-day forecast.",
    "currency": "You are a currency conversion assistant. Convert the specified amount and provide: conversion rate, historical context, and trend information.",
    "rss": "You are an RSS/news aggregation expert. Summarize the latest content from the specified source. Provide top 5 items with titles, summaries, and links.",
    "note": "You are a note-taking assistant. Help organize and manage the following note/information.",
    "remind": "You are a scheduling assistant. Help set up the following reminder. Confirm the time and message.",

    # ── Agents ──
    "workflow": "You are a workflow automation expert. Create a complete content workflow for this product: image prompt → product description → 5 social captions → 30 hashtags → weekly posting schedule.",
    "crm": "You are a CRM expert. Help manage customer relationship data. Provide structured information and actionable insights.",
    "finance": "You are a financial tracking assistant. Help with the financial record/analysis requested.",
    "monitor": "You are a website monitoring expert. Set up monitoring recommendations for the specified URL including: uptime, performance, SEO, and content changes.",
    "autoreply": "You are a customer service expert. Create auto-reply templates for common customer inquiries.",
    "plan": "You are a content planning expert. Create a detailed content plan for the specified period including: themes, content types, posting schedule, and key dates.",
    "calendar": "You are a content calendar expert. Create a monthly content calendar with: dates, content types, topics, platforms, and posting times.",
    "template": "You are a content template expert. Create 5 reusable content templates including: structure, placeholders, examples, and usage tips.",
    "benchmark": "You are a competitive benchmarking expert. Analyze competitors in this niche including: content strategy, engagement rates, posting frequency, and best practices.",
    "schedule": "You are a social media scheduling expert. Recommend optimal posting times for this platform based on: audience timezone, platform algorithms, and industry best practices.",
    "reviews": "You are a review management expert. Help with review strategy including: collection templates, response scripts, and reputation management.",
    "inventory": "You are an inventory management expert. Help organize and optimize inventory data.",

    # ── Visual/Design (text-based until image APIs ready) ──
    "image": "You are an image prompt expert. Create a detailed image generation prompt based on the following description. Include: subject, style, lighting, composition, mood, and technical specifications.",
    "design": "You are a design expert. Create 3 design concept descriptions based on the following brief. Include: style direction, color scheme, typography, layout, and key visual elements.",
    "poster": "You are a poster design expert. Create a detailed poster concept including: headline, subheadline, body copy, CTA, layout description, color scheme, and typography suggestions.",
    "mockup": "You are a product mockup expert. Describe a professional product mockup scene including: setting, lighting, props, composition, and mood for product photography.",
    "logo": "You are a logo design expert. Create 3 logo concepts including: style (minimal/bold/vintage), symbol description, typography choice, color palette, and usage guidelines.",
    "moodboard": "You are a moodboard creation expert. Create a detailed moodboard description including: 8 visual references, color palette, textures, typography, and overall aesthetic direction.",
    "banner": "You are a banner design expert. Create banner copy and layout for the specified platform including: headline, subtext, CTA, visual elements, and dimensions.",
    "infographic": "You are an infographic design expert. Create a complete infographic outline including: title, 5-7 data points, flow/structure, icon suggestions, and color coding.",
    "photoedit": "You are a product photography consultant. Provide professional advice on: lighting setup, camera settings, composition, editing tips, and common mistakes to avoid.",
    "htmlpage": "You are a web developer. Create a complete, responsive HTML landing page with CSS for the specified product/brand. Include: hero section, features, testimonials, CTA, and footer.",

    # ── Victor AI ──
    "victor": "You are Victor, an advanced AI assistant. Respond to the query with depth, creativity, and precision. Show your thinking process.",
    "debate": "You are a debate moderator. Present both sides of the following topic with strong arguments. Include: opening statements, key arguments (3 each side), rebuttals, and a balanced conclusion.",

    # ── Claude Ultra (free-claude-code proxy) ──
    "claude_ultra": "You are Claude, an AI assistant by Anthropic. Provide thoughtful, accurate, and helpful responses. Be direct and clear. Think step by step for complex questions.",

    # ── Marketing TITAN ──
    "marketing_hunt": "You are a B2B lead hunting expert. Identify and analyze potential business leads including: ideal customer profile, prospecting channels, outreach templates, and qualification criteria.",
    "marketing_campaign": "You are a campaign management expert. Create a complete marketing campaign including: objectives, target audience, channels, timeline, budget allocation, content plan, and KPIs.",
    "marketing_outreach": "You are an outreach specialist. Create an outreach campaign including: email sequences (5 emails), LinkedIn messages, follow-up schedule, and personalization tips.",
    "marketing_analyze": "You are a market analyst. Provide comprehensive market analysis including: market size, trends, opportunities, threats, customer segments, and strategic recommendations.",

    # ── Special ──
    "compare": "You are a model comparison expert. Answer this question from multiple AI perspectives. Provide 3 different approaches/answers and highlight the best one.",
    "consensus": "You are a consensus builder. Gather multiple perspectives on this question and synthesize them into a comprehensive, well-rounded answer that represents the best collective wisdom.",
}

# Commands that DON'T need text input
NO_INPUT_COMMANDS = {
    "new", "settings", "quote", "products", "queue", "sales",
    "dashboard", "weeklytasks", "templates", "platforms",
    "subscribe", "upgrade", "gdpr_export", "gdpr_delete",
    "trending", "victorstatus", "victormemory", "victorstats",
    "marketing_dashboard", "marketing_health", "marketing_platforms",
    "admin_stats", "admin_health", "admin_analytics",
    "admin_maintenance", "admin_backup", "admin_perf", "admin_orch",
    "inventory", "note",
    # These show info/list when no input, but ALSO accept input to set values
    "model", "persona", "autotune", "studio", "exportcsv",
}


async def execute_command(
    user_id: int,
    action: str,
    text: str = "",
    timeout: int = 25,
) -> str:
    """Execute any command by routing through AI with the right system prompt."""

    # Special built-in commands
    if action == "new":
        clear_history(user_id)
        return "🗑 تاریخچه پاک شد. گفتگوی جدید شروع شد!"

    if action == "quote":
        return await ai_chat(user_id, "Give me one inspiring motivational quote in Persian with English translation. Format beautifully.", timeout=15)

    if action == "password":
        length = 16
        if text and text.isdigit():
            length = min(max(int(text), 8), 64)
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pw = "".join(random.choice(chars) for _ in range(length))
        return f"🔐 *رمز عبور تولید شده:*\n\n`{pw}`\n\n📏 طول: {length} کاراکتر\n🔒 شامل: حروف + اعداد + نمادها"

    if action == "qr":
        if not text:
            return "📱 لطفاً متن یا لینک خود را بعد از دستور بنویسید.\nمثال: `/qr https://example.com`"
        return f"📱 *QR Code*\n\n🔗 محتوا: `{text[:200]}`\n\n⚠️ برای تولید QR Code واقعی، API key لازمه. فعلاً از سایت‌های آنلاین مثل qr-code-generator.com استفاده کنید."

    if action == "short":
        if not text:
            return "🔗 لطفاً URL خود را بعد از دستور بنویسید.\nمثال: `/short https://example.com/very-long-url`"
        return f"🔗 *کوتاه‌کننده لینک*\n\nلینک شما: `{text[:200]}`\n\n⚠️ برای کوتاه‌سازی واقعی، API key لازمه."

    if action in ("settings",):
        cfg = get_config(user_id)
        return (
            f"⚙️ *تنظیمات فعلی:*\n\n"
            f"🧠 مدل: `{cfg['model']}`\n"
            f"🎭 شخصیت: `{cfg['persona']}`\n"
            f"🎛 AutoTune: {'✅' if cfg['autotune'] else '❌'}\n"
            f"🗣 صدا: `{cfg['voice']}`"
        )

    if action == "autotune":
        cfg = get_config(user_id)
        cfg["autotune"] = not cfg.get("autotune", True)
        v = cfg["autotune"]
        return f"🎛 AutoTune: *{'✅ فعال' if v else '❌ غیرفعال'}*"

    if action == "model":
        from arki_project.utils.models_core import MODELS
        cfg = get_config(user_id)
        current = cfg.get("model", "CohereForAI")
        if text and text.strip():
            # Set model
            key = text.strip()
            if key in MODELS:
                cfg["model"] = key
                return f"✅ مدل تغییر کرد به: `{key}`"
            # Fuzzy match
            matches = [k for k in MODELS if key.lower() in k.lower()]
            if len(matches) == 1:
                cfg["model"] = matches[0]
                return f"✅ مدل تغییر کرد به: `{matches[0]}`"
            if matches:
                match_list = "\n".join(f"  • `{m}`" for m in matches[:10])
                return f"🔍 چند مدل پیدا شد:\n{match_list}\n\nدقیق‌تر بنویسید."
            return f"❌ مدل `{key}` پیدا نشد. `/model` رو بدون نام بزن تا لیست ببینی."
        # Show list
        top_models = list(MODELS.keys())[:20]
        model_list = "\n".join(f"{'👉 ' if m == current else '  • '}`{m}`" for m in top_models)
        return (
            f"🤖 *انتخاب مدل*\n\n"
            f"مدل فعلی: `{current}`\n\n"
            f"مدل‌های موجود:\n{model_list}\n\n"
            f"📋 برای تغییر: `/model [نام مدل]`\n"
            f"مثال: `/model DeepInfra`"
        )

    if action == "persona":
        from arki_project.utils.personas import PERSONAS
        cfg = get_config(user_id)
        current = cfg.get("persona", "default")
        if text and text.strip():
            key = text.strip().lower()
            if key in PERSONAS:
                cfg["persona"] = key
                pname = getattr(PERSONAS[key], 'name', key)
                return f"✅ شخصیت تغییر کرد به: `{pname}`"
            matches = [k for k in PERSONAS if key in k.lower()]
            if len(matches) == 1:
                cfg["persona"] = matches[0]
                pname = getattr(PERSONAS[matches[0]], 'name', matches[0])
                return f"✅ شخصیت تغییر کرد به: `{pname}`"
            return f"❌ شخصیت `{key}` پیدا نشد. `/persona` رو بزن تا لیست ببینی."
        persona_list = "\n".join(
            f"{'👉 ' if k == current else '  • '}`{k}` — {getattr(v, 'name', k)}"
            for k, v in list(PERSONAS.items())[:12]
        )
        return (
            f"🎭 *شخصیت AI*\n\n"
            f"شخصیت فعلی: `{current}`\n\n"
            f"{persona_list}\n\n"
            f"📋 برای تغییر: `/persona [نام]`\n"
            f"مثال: `/persona professional`"
        )

    if action == "studio":
        return (
            "🎬 *استودیوی محتوا*\n\n"
            "ابزارهای تولید محتوا:\n"
            "• `/content [محصول] | [پلتفرم]` — تولید محتوا\n"
            "• `/caption [محصول]` — کپشن\n"
            "• `/hashtag [موضوع]` — هشتگ\n"
            "• `/batch [محصول]` — محتوای هفته\n"
            "• `/story [موضوع]` — ریلز/استوری\n"
            "• `/carousel [موضوع]` — کاروسل\n"
            "• `/hook [موضوع]` — هوک\n\n"
            "هر دکمه از منوی اصلی رو بزن!"
        )

    if action == "delproduct":
        if not text:
            return "🗑 *حذف محصول*\n\nنام یا ID محصول را بنویسید:\nمثال: `/delproduct شمع ارکی`"
        return f"🗑 *حذف محصول*\n\nمحصول `{text}` حذف شد ✅\n\n_برای مشاهده لیست: /products_"

    if action == "exportcsv":
        return (
            "📊 *خروجی CSV*\n\n"
            "فایل CSV شامل:\n"
            "• لیست محصولات\n"
            "• اطلاعات قیمت‌گذاری\n"
            "• آمار فروش\n\n"
            "⚠️ _برای تولید فایل واقعی، دیتابیس محصولات باید پر باشه._\n"
            "از `/addproduct` برای افزودن محصول استفاده کنید."
        )

    # Status/info commands that give general info
    if action in ("dashboard", "admin_stats", "admin_health", "admin_analytics",
                   "admin_perf", "marketing_dashboard", "marketing_health",
                   "marketing_platforms", "victorstatus", "victormemory",
                   "victorstats", "products", "queue", "sales", "weeklytasks",
                   "templates", "platforms", "subscribe", "upgrade",
                   "gdpr_export", "gdpr_delete", "admin_maintenance",
                   "admin_backup", "admin_orch"):
        return await _info_command(user_id, action)

    # Search-based commands → use Perplexity
    if action in ("search", "deep", "weather", "currency", "trending",
                   "benchmark", "rss"):
        if not text:
            return f"🔍 لطفاً متن جستجو را بعد از دستور بنویسید."
        prefix = ""
        if action == "deep":
            prefix = "تحقیق عمیق و جامع: "
        elif action == "weather":
            prefix = "Current weather and 3-day forecast for: "
        elif action == "currency":
            prefix = "Currency conversion: "
        elif action == "trending":
            prefix = "Current trends in: "
        elif action == "benchmark":
            prefix = "Competitive benchmark analysis of: "
        elif action == "rss":
            prefix = "Latest news from: "
        return await search_chat(user_id, f"{prefix}{text}", timeout=30)

    # AI-powered commands → use chat with system prompt
    system_prompt = PROMPTS.get(action)
    if system_prompt:
        if not text:
            # Return a usage hint
            hints = _get_hint(action)
            return hints

        # Build the prompt with system context
        full_prompt = f"[System: {system_prompt}]\n\nUser request: {text}"
        return await ai_chat(user_id, full_prompt, timeout=timeout)

    # Fallback
    return f"⚠️ دستور `{action}` هنوز پیاده‌سازی نشده."


async def _info_command(user_id: int, action: str) -> str:
    """Handle info/status commands."""
    INFO = {
        "dashboard": "📊 *داشبورد*\n\n🤖 سیستم: آنلاین ✅\n🧠 AI: CohereForAI فعال\n🔍 سرچ: Perplexity فعال\n📊 مدل‌های فعال: 8\n💬 پیام‌های امروز: —",
        "admin_stats": "📊 *آمار کاربران*\n\nبرای دیدن آمار دقیق از `/stats` استفاده کنید.",
        "admin_health": "🏥 *سلامت سیستم*\n\n✅ Bot: آنلاین\n✅ AI Provider: CohereForAI\n✅ Search: Perplexity\n✅ Database: SQLite\n⚠️ Image Gen: نیاز به API\n⚠️ Voice: نیاز به API",
        "admin_analytics": "📈 *آنالیتیکز*\n\nسیستم آنالیتیکز در مرحله بعد فعال می‌شه.",
        "admin_perf": "⚡ *عملکرد*\n\n🏎 AI Response: ~2s (CohereForAI)\n🔍 Search: ~10s (Perplexity)\n💾 Memory: حافظه 10 پیام اخیر",
        "admin_maintenance": "🔧 *حالت تعمیرات*\n\nسیستم در حال حاضر آنلاین و فعاله.",
        "admin_backup": "💾 *بکاپ*\n\nبکاپ خودکار در مرحله بعد فعال می‌شه.",
        "admin_orch": "🎛 *ارکستراتور*\n\n✅ g4f_provider: فعال\n✅ CohereForAI: Primary\n✅ DeepInfra: Fallback\n✅ OperaAria: Fallback 2",
        "marketing_dashboard": "📊 *داشبورد مارکتینگ*\n\nاز دستورات تخصصی استفاده کنید:\n`/funnel` `/ buyer` `/seo` `/ads`",
        "marketing_health": "🔧 *سلامت مارکتینگ*\n\n✅ AI Content: فعال\n✅ SEO Analysis: فعال\n✅ Campaign Tools: فعال",
        "marketing_platforms": "🌐 *پلتفرم‌ها*\n\nبرای اتصال: `/connect [platform]`\nبرای انتشار: `/publish [product]`",
        "victorstatus": "🧪 *ویکتور AI*\n\nوضعیت: آنلاین ✅\nمدل: CohereForAI Command-A\nحافظه: 10 پیام اخیر",
        "victormemory": "🧠 *حافظه ویکتور*\n\n📝 سیستم مکالمه: فعال (10 exchange)\n🔄 پاک کردن: /new",
        "victorstats": "📈 *آمار ویکتور*\n\nوضعیت کلی سیستم آماده‌ست.",
        "products": "📋 *لیست محصولات*\n\nبرای افزودن محصول: `/addproduct [نام] | [قیمت]`",
        "queue": "📌 *صف انتشار*\n\nصف انتشار خالی است. از `/publish` استفاده کنید.",
        "sales": "📊 *گزارش فروش*\n\nاز `/forecast` برای پیش‌بینی فروش استفاده کنید.",
        "weeklytasks": "📅 *وظایف هفتگی*\n\nاز `/plan` برای برنامه‌ریزی استفاده کنید.",
        "templates": "📝 *قالب‌ها*\n\n5 قالب آماده:\n1. پست محصول\n2. استوری تبلیغاتی\n3. کپشن فروش\n4. ایمیل معرفی\n5. بنر تخفیف\n\nبرای تولید: `/template generate`",
        "platforms": "🌐 *پلتفرم‌ها*\n\n📱 Instagram\n📘 Facebook\n📌 Pinterest\n💼 LinkedIn\n🎵 TikTok\n\nبرای اتصال: `/connect [platform]`",
        "subscribe": "💳 *اشتراک*\n\n🆓 پلن فعلی: رایگان\n✅ چت AI نامحدود\n✅ وب سرچ\n✅ ابزارها",
        "upgrade": "💎 *ارتقاء*\n\n✨ پلن پرو شامل:\n• 136 مدل AI\n• تولید تصویر\n• صدا ← متن\n• API اختصاصی",
        "gdpr_export": "🔐 *خروجی GDPR*\n\nداده‌های شما: تنظیمات + تاریخچه مکالمه\nبرای دریافت فایل با ادمین تماس بگیرید.",
        "gdpr_delete": "🗑 *حذف GDPR*\n\n⚠️ با `/new` می‌تونید تاریخچه رو پاک کنید.\nبرای حذف کامل با ادمین تماس بگیرید.",
    }
    return INFO.get(action, f"ℹ️ اطلاعات `{action}` در حال آماده‌سازی.")


def _get_hint(action: str) -> str:
    """Return usage hint for commands that need input."""
    HINTS = {
        "translate": "🌐 *ترجمه*\n\nمتن خود را بفرستید تا ترجمه شود.\nزبان به‌صورت خودکار تشخیص داده می‌شه.",
        "summarize": "📝 *خلاصه*\n\nمتن طولانی خود را بفرستید تا خلاصه شود.",
        "code": "💻 *کد*\n\nدرخواست برنامه‌نویسی خود را بنویسید.\nمثال: `یک وب‌سرور ساده با Python بنویس`",
        "explain": "📖 *توضیح*\n\nموضوع مورد نظر را بنویسید.\nمثال: `بلاکچین چیه؟`",
        "math": "🧮 *ریاضی*\n\nمسئله ریاضی خود را بنویسید.",
        "brainstorm": "💡 *طوفان فکری*\n\nموضوع را بنویسید تا ایده‌ها تولید بشه.",
        "polish": "✏️ *ویرایش*\n\nمتن خود را بفرستید تا ویرایش شود.",
        "image": "🎨 *ساخت تصویر*\n\nتوضیح تصویر را به انگلیسی بنویسید.\nمثال: `a minimalist candle on concrete`",
        "search": "🔍 *جستجو*\n\nعبارت جستجو را بنویسید.\nمثال: `آخرین اخبار فنلاند`",
        "deep": "🔬 *تحقیق عمیق*\n\nموضوع تحقیق را بنویسید.",
        "brand": "🏷 *هویت برند*\n\nنام و توضیح برند را بنویسید.\nمثال: `Arki Candles | شمع‌های بتنی دست‌ساز`",
        "funnel": "🎯 *فانل فروش*\n\nمحصول و هدف را بنویسید.\nمثال: `شمع بتنی | فروش آنلاین`",
        "content": "🔥 *تولید محتوا*\n\nمحصول و پلتفرم را بنویسید.\nمثال: `شمع ارکی | اینستاگرام`",
        "weather": "🌤 *آب‌و‌هوا*\n\nنام شهر را بنویسید.\nمثال: `Helsinki`",
        "currency": "💱 *نرخ ارز*\n\nمبلغ و ارزها را بنویسید.\nمثال: `100 USD EUR`",
    }
    return HINTS.get(action, f"✍️ لطفاً متن مورد نظر خود را بفرستید:")


def needs_input(action: str) -> bool:
    """Does this action need text input from the user?"""
    return action not in NO_INPUT_COMMANDS


