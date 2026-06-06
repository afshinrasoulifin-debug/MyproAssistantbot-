
"""content_studio_pkg.cmd_contentpack_group — sub-module of content_studio"""

from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError

# ═══ TITANIUM v29.0 Integration ═══

__all__ = ['cmd_contentpack']

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
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))



