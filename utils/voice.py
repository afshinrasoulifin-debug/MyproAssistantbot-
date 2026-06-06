
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/voice.py
─────────────────────
Voice utilities:
  • transcribe_voice — Groq Whisper v3 Turbo (free, fast)
  • text_to_speech   — Gemini TTS with 9 selectable voices
"""


import base64
import io
import logging
import wave

from arki_project.utils.http_pool import get_client
from arki_project.utils.models_registry import TTS_MODEL

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)


# ──────────── STT (Groq Whisper) ────────────

async def transcribe_voice(
    audio_bytes: bytes,
    groq_api_key: str,
    *,
    filename: str = "audio.ogg",
) -> str:
    """Transcribe audio using Groq's Whisper Large v3 Turbo.
    Retries once on transient failures."""
    import asyncio as _aio

    import aiohttp as _aiohttp

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {groq_api_key}"}
    client = await get_client("groq")

    last_exc: Exception | None = None
    for attempt in range(2):  # max 2 attempts
        try:
            # aiohttp requires FormData for multipart uploads (not httpx files=)
            form = _aiohttp.FormData()
            form.add_field("file", audio_bytes, filename=filename, content_type="audio/ogg")
            form.add_field("model", "whisper-large-v3-turbo")
            form.add_field("response_format", "text")

            async with client.post(
                url,
                headers=headers,
                data=form,
                timeout=_aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp_text = await resp.text()
                if resp.status == 429 and attempt == 0:
                    await _aio.sleep(2)
                    continue
                if resp.status != 200:
                    raise Exception(
                        f"Whisper failed (HTTP {resp.status}): {resp_text[:200]}",
                    )
                return resp_text.strip()
        except ArkiBaseError as exc:
            last_exc = exc
            if attempt == 0:
                await _aio.sleep(1)
                continue
            raise

    raise last_exc or Exception("Transcription failed after retries")


# ──────────── TTS (Gemini — 9 voices) ────────────

async def text_to_speech(
    text: str,
    api_key: str,
    *,
    voice: str = "Zephyr",
) -> bytes:
    """Convert text to speech using Gemini TTS.

    Returns WAV bytes ready to send as a Telegram voice message.
    """
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": text}]},
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice},
                },
            },
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        f"/models/{TTS_MODEL}:generateContent"
    )
    headers = {"x-goog-api-key": api_key}

    client = await get_client("gemini")
    import aiohttp as _aiohttp
    async with client.post(
        url, json=body, headers=headers,
        timeout=_aiohttp.ClientTimeout(total=60),
    ) as resp:
        if resp.status != 200:
            raise Exception(f"TTS: HTTP {resp.status}")

        data = await resp.json()

    # Extract raw audio from response.
    for part in (
        data
        .get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    ):
        if "inlineData" in part:
            raw = base64.b64decode(part["inlineData"]["data"])
            # Wrap in WAV container.
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(raw)
            return wav_buf.getvalue()

    raise Exception("TTS: خروجی صوتی دریافت نشد")


