
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/files.py
────────────────────────
Handle uploaded documents and photos:

  • Documents: read contents (PDF/Excel/Word/CSV/ZIP/TXT/code) → display
    If user adds a caption → AI analyses the file content
  • Photos: Gemini Vision analysis
"""


import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.file_processor import process_file
from arki_project.utils.models_registry import (
    PERSONAS,
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.vision import analyse_image
from arki_project.utils.safe_send import safe_reply
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

router = Router(name="files")

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Image extensions — route to vision instead of file reader.
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
}


# ═══════════ Documents ═══════════

@router.message(F.document)
async def handle_document(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    doc = message.document
    if not doc:
        return
    user_id = message.from_user.id  # type: ignore[union-attr]
    filename = doc.file_name or "file"

    if (doc.file_size or 0) > MAX_FILE_SIZE:
        await message.answer("⚠️ فایل خیلی بزرگه (حداکثر 20MB)")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        # Download.
        file_obj = await message.bot.get_file(doc.file_id)  # type: ignore[union-attr]
        file_io = await message.bot.download_file(file_obj.file_path)  # type: ignore[union-attr]
        file_bytes = file_io.read()  # type: ignore[union-attr]

        # Check if it's an image file sent as document → vision.
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in _IMAGE_EXTS and settings.ai_api_key:
            mime = _MIME_MAP.get(ext, "image/jpeg")
            caption = (message.caption or "").strip() or "تحلیل کن."
            cfg = await ai_client.get_user_config(user_id)
            persona = PERSONAS.get(cfg["persona"], PERSONAS["assistant"])
            result = await analyse_image(
                file_bytes, mime, settings.ai_api_key,
                prompt=caption,
                system_prompt=persona.system_prompt,
            )
            for chunk in split_for_telegram(result):
                try:
                    await safe_reply(message, chunk)
                except HandlerError as exc:
                    logger.error("Error in handler: %s", exc)
                    await message.answer(chunk)
            return

        # Process as document.
        extracted = await process_file(file_bytes, filename)

        for chunk in split_for_telegram(extracted):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

        # If user added a caption/question → send to AI.
        caption = (message.caption or "").strip()
        if caption:
            cfg = await ai_client.get_user_config(user_id)
            mk = working_model_key(
                cfg["model"], settings.ai_api_key, settings.groq_api_key,
            )
            persona = PERSONAS.get(cfg["persona"], PERSONAS["assistant"])
            prompt = (
                f"File content:\n{extracted[:6000]}\n\n"
                f"User request: {caption}"
            )
            import time as _t; _t0 = _t.time()
            answer = await ai_client.ask(
                user_id, prompt,
                system_prompt=enhance_system_prompt(persona.system_prompt, user_text=prompt, user_id=str(user_id)),
                model_key=mk,
            )
            store_result(message.from_user.id if message.from_user else 0, "file_analysis", answer[:500] if answer else "", "files", duration_s=_t.time()-_t0)
            for chunk in split_for_telegram(answer):
                try:
                    await safe_reply(message, chunk)
                except HandlerError as exc:
                    logger.error("Error in handler: %s", exc)
                    await message.answer(chunk)
        else:
            await safe_reply(message, "💡 _Tip: کپشن/سوال اضافه کن تا AI فایل رو تحلیل کنه!_")

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════ Photos → Vision ═══════════

@router.message(F.photo)
async def handle_photo(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    if False:  # v25.0 AUTONOMOUS: FreeAccessRouter handles all
        await message.answer("❌ نیاز به Gemini برای تحلیل عکس")
        return

    user_id = message.from_user.id  # type: ignore[union-attr]

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        # Get highest-quality photo.
        photo = message.photo[-1]  # type: ignore[index]
        file_obj = await message.bot.get_file(photo.file_id)  # type: ignore[union-attr]
        file_io = await message.bot.download_file(file_obj.file_path)  # type: ignore[union-attr]
        image_bytes = file_io.read()  # type: ignore[union-attr]

        caption = (message.caption or "").strip()
        prompt = caption or (
            "این عکس رو کامل و دقیق تحلیل و توضیح بده. هر جزئیاتی رو بگو."
        )

        cfg = await ai_client.get_user_config(user_id)
        persona = PERSONAS.get(cfg["persona"], PERSONAS["assistant"])

        result = await analyse_image(
            image_bytes, "image/jpeg", settings.ai_api_key,
            prompt=prompt,
            system_prompt=persona.system_prompt,
        )

        for chunk in split_for_telegram(result):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


