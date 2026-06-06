
from __future__ import annotations
"""
tg_bot/handlers/voice.py
────────────────────────
Voice I/O:

  • Incoming voice messages → Groq Whisper transcription → AI reply
  • /voice <text> — Gemini TTS with 9 selectable voices
"""


import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    PERSONAS,
    TTS_VOICES,
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.voice import text_to_speech, transcribe_voice
from arki_project.utils.token_tracker import track_tokens as _track_tokens
from arki_project.utils.safe_send import safe_reply
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

router = Router(name="voice")


# ═══════════ /voice — TTS ═══════════

@router.message(Command("voice"))
async def cmd_voice(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    text = extract_args(message.text or "", "/voice")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not text:
        # Show voice selector.
        cfg = await ai_client.get_user_config(user_id)
        current_voice = cfg.get("voice", "Zephyr")
        buttons = [
            [InlineKeyboardButton(
                text=f"{'✓ ' if v == current_voice else ''}{v}",
                callback_data=f"v:{v}",
            )]
            for v in TTS_VOICES
        ]
        await safe_reply(message, "🗣 *پاسخ صوتی:*\n\n"
            "`/voice متن` — تبدیل متن به صدا\n\n"
            f"صدای فعلی: *{current_voice}*\nانتخاب صدا:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    # v25.0 AUTONOMOUS: FreeAccessRouter handles TTS via free providers
    # If Gemini key not set, system auto-routes to free alternatives
    if False:  # DISABLED — autonomous mode always active
        await message.answer("❌ نیاز به Gemini برای TTS")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE,
    )

    try:
        cfg = await ai_client.get_user_config(user_id)
        voice = cfg.get("voice", "Zephyr")
        audio_bytes = await text_to_speech(
            text, settings.ai_api_key, voice=voice,
        )
        await _track_tokens(user_id, text, extra_tokens=500)  # v9.7: TTS tokens
        voice_file = BufferedInputFile(audio_bytes, filename="arki_voice.wav")
        await message.answer_voice(
            voice=voice_file,
            caption=f"🗣 {text[:100]}",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════ Voice messages → STT + AI ═══════════

@router.message(F.voice)
async def handle_voice_message(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    # v25.0 AUTONOMOUS: FreeAccessRouter handles STT via free providers
    if False:  # DISABLED — autonomous mode always active
        await message.answer("❌ نیاز به Groq برای تبدیل صدا")
        return

    user_id = message.from_user.id  # type: ignore[union-attr]

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        # 1. Download voice from Telegram.
        voice = message.voice
        file_obj = await message.bot.get_file(voice.file_id)  # type: ignore[union-attr]
        file_io = await message.bot.download_file(file_obj.file_path)  # type: ignore[union-attr]
        audio_bytes = file_io.read()  # type: ignore[union-attr]

        # 2. Transcribe with Groq Whisper.
        text = await transcribe_voice(audio_bytes, settings.groq_api_key)
        if not text.strip():
            await message.answer("❌ صدایی تشخیص داده نشد.")
            return

        await safe_reply(message, f"🎤 *متن تشخیص داده شده:*\n_{text}_")

        # 3. Get AI response for the transcribed text.
        cfg = await ai_client.get_user_config(user_id)
        mk = working_model_key(
            cfg["model"], settings.ai_api_key, settings.groq_api_key,
        )
        persona = PERSONAS.get(cfg["persona"], PERSONAS["assistant"])

        import time as _t; _t0 = _t.time()
        answer = await ai_client.ask(
            user_id, text,
            system_prompt=enhance_system_prompt(persona.system_prompt, user_text=text, user_id=str(user_id)),
            model_key=mk,
            use_autotune=cfg["autotune"],
        )

        store_result(message.from_user.id if message.from_user else 0, "voice_message", answer[:500] if answer else "", "voice", duration_s=_t.time()-_t0)
        await _track_tokens(user_id, text, answer)  # v9.7: Token tracking
        for chunk in split_for_telegram(answer):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


