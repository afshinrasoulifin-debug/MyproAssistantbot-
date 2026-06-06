from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/video.py
────────────────────────
AI Video Generation Hub:

  /video       — AI video generation from text prompt
  /slideshow   — AI slideshow (6 frames, animated GIF)
  /animate     — Animate a concept into moving frames
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

from arki_project.utils.video_gen import generate_video, generate_slideshow, frames_to_gif
from arki_project.utils.token_tracker import track_tokens as _track_tokens
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args

logger = logging.getLogger(__name__)

router = Router(name="video")


@router.message(Command("video"))
async def cmd_video(message: Message) -> None:
    """Generate a video from a text prompt."""
    prompt = extract_args(message.text or "", "/video")
    if not prompt:
        await safe_reply(message, "🎬 *تولید ویدیو با AI:*\n\n"
            "Usage: `/video [توضیح ویدیو]`\n\n"
            "*مثال‌ها:*\n"
            "`/video a cat walking in a garden`\n"
            "`/video غروب آفتاب روی دریا`\n"
            "`/video product showcase of handmade candles`\n"
            "`/video لوگو متحرک برند ارکی`\n\n"
            "*حالت‌ها:*\n"
            "`/video [توضیح]` — ویدیو اتوماتیک\n"
            "`/slideshow [توضیح]` — اسلایدشو ۶ فریم\n"
            "`/animate [توضیح]` — انیمیشن AI\n\n"
            "_رایگان و بدون محدودیت!_")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO
    )
    status = await message.answer("🎬 دارم ویدیو می‌سازم... (ممکنه تا ۲ دقیقه طول بکشه)")

    try:
        video_bytes, fmt, provider = await generate_video(prompt, mode="auto")
        await _track_tokens(
            message.from_user.id if message.from_user else 0,
            prompt, extra_tokens=2000,
        )

        if fmt == "gif":
            doc = BufferedInputFile(video_bytes, filename="video.gif")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 دوباره بساز",
                        callback_data=f"vid_retry:{prompt[:50]}",
                    ),
                    InlineKeyboardButton(
                        text="🖼 فقط عکس‌ها",
                        callback_data=f"vid_frames:{prompt[:50]}",
                    ),
                ],
            ])
            await message.answer_animation(
                animation=doc,
                caption=(
                    f"🎬 *{prompt[:100]}*\n"
                    f"_Provider: {provider} | فرمت: GIF_"
                ),
                reply_markup=kb,
                parse_mode="Markdown",
            )
        else:
            doc = BufferedInputFile(video_bytes, filename=f"video.{fmt}")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 دوباره بساز",
                        callback_data=f"vid_retry:{prompt[:50]}",
                    ),
                ],
            ])
            await message.answer_video(
                video=doc,
                caption=(
                    f"🎬 *{prompt[:100]}*\n"
                    f"_Provider: {provider}_"
                ),
                reply_markup=kb,
                parse_mode="Markdown",
            )

        try:
            await safe_delete(status)
        except HandlerError:
            pass
    except HandlerError as e:
        logger.error("Video generation failed: %s", e)
        await safe_edit_text(status, f"⚠️ خطا:\n`{str(e)[:200]}`")


@router.message(Command("slideshow"))
async def cmd_slideshow(message: Message) -> None:
    """Generate an AI slideshow (6 frames as animated GIF)."""
    prompt = extract_args(message.text or "", "/slideshow")
    if not prompt:
        await safe_reply(message, "🎞 *اسلایدشو AI:*\n\n"
            "Usage: `/slideshow [توضیح]`\n\n"
            "*مثال:*\n"
            "`/slideshow فصل‌های سال در طبیعت`\n"
            "`/slideshow product photography candles`\n"
            "`/slideshow مراحل ساخت شمع`\n\n"
            "_۶ فریم AI + انیمیشن GIF_")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
    )
    status = await message.answer("🎞 دارم ۶ فریم می‌سازم...")

    try:
        frames, enhanced = await generate_slideshow(prompt, frame_count=6)

        # Send individual frames as album
        from aiogram.types import InputMediaPhoto
        media_group = []
        for i, frame_bytes in enumerate(frames[:10]):  # Max 10 for Telegram
            photo = BufferedInputFile(frame_bytes, filename=f"frame_{i+1}.png")
            media_group.append(InputMediaPhoto(
                media=photo,
                caption=f"🎞 فریم {i+1}/{len(frames)}" if i == 0 else "",
                parse_mode="Markdown" if i == 0 else None,
            ))

        if media_group:
            await message.answer_media_group(media=media_group)

        # Also send as GIF
        gif_data = await frames_to_gif(frames, fps=2)
        gif_file = BufferedInputFile(gif_data, filename="slideshow.gif")
        await message.answer_animation(
            animation=gif_file,
            caption=f"🎞 *اسلایدشو — {prompt[:80]}*\n_AI Slideshow | {len(frames)} فریم_",
            parse_mode="Markdown",
        )

        try:
            await safe_delete(status)
        except HandlerError:
            pass
    except HandlerError as e:
        logger.error("Slideshow failed: %s", e)
        await safe_edit_text(status, f"⚠️ خطا:\n`{str(e)[:200]}`")


@router.message(Command("animate"))
async def cmd_animate(message: Message) -> None:
    """Create an animated sequence from a concept."""
    prompt = extract_args(message.text or "", "/animate")
    if not prompt:
        await safe_reply(message, "🎭 *انیمیشن AI:*\n\n"
            "Usage: `/animate [توضیح]`\n\n"
            "*مثال:*\n"
            "`/animate a flower blooming`\n"
            "`/animate شمع روشن شدن`\n"
            "`/animate sunrise over mountains`\n\n"
            "_انیمیشن ۸ فریمی با AI_")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO
    )
    status = await message.answer("🎭 دارم انیمیشن می‌سازم... (۸ فریم)")

    try:
        frames, enhanced = await generate_slideshow(
            prompt, frame_count=8, width=768, height=768,
        )
        gif_data = await frames_to_gif(frames, fps=3)

        gif_file = BufferedInputFile(gif_data, filename="animation.gif")
        await message.answer_animation(
            animation=gif_file,
            caption=f"🎭 *انیمیشن — {prompt[:80]}*\n_AI Animation | {len(frames)} فریم | 3 FPS_",
            parse_mode="Markdown",
        )

        try:
            await safe_delete(status)
        except HandlerError:
            pass
    except HandlerError as e:
        logger.error("Animation failed: %s", e)
        await safe_edit_text(status, f"⚠️ خطا:\n`{str(e)[:200]}`")


# ── Callback handlers ──

@router.callback_query(F.data.startswith("vid_retry:"))
async def cb_vid_retry(callback: CallbackQuery) -> None:
    await callback.answer("🎬 ساخت دوباره...")
    prompt = callback.data.split(":", 1)[1]
    try:
        video_bytes, fmt, provider = await generate_video(prompt, mode="auto")
        if fmt == "gif":
            doc = BufferedInputFile(video_bytes, filename="video.gif")
            await callback.message.answer_animation(
                animation=doc,
                caption=f"🎬 *{prompt[:100]}* (retry)\n_Provider: {provider}_",
                parse_mode="Markdown",
            )
        else:
            doc = BufferedInputFile(video_bytes, filename=f"video.{fmt}")
            await callback.message.answer_video(
                video=doc,
                caption=f"🎬 *{prompt[:100]}* (retry)\n_Provider: {provider}_",
                parse_mode="Markdown",
            )
    except HandlerError as exc:
        await callback.message.answer(f"❌ {exc}")


@router.callback_query(F.data.startswith("vid_frames:"))
async def cb_vid_frames(callback: CallbackQuery) -> None:
    await callback.answer("🖼 ساخت فریم‌ها...")
    prompt = callback.data.split(":", 1)[1]
    try:
        frames, _ = await generate_slideshow(prompt, frame_count=4)
        for i, frame_bytes in enumerate(frames, 1):
            photo = BufferedInputFile(frame_bytes, filename=f"frame_{i}.png")
            await callback.message.answer_photo(
                photo=photo,
                caption=f"🖼 فریم {i}/{len(frames)}",
            )
    except HandlerError as exc:
        await callback.message.answer(f"❌ {exc}")
