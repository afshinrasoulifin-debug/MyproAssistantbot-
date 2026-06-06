
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/vision.py
──────────────────────
Gemini vision — analyse images with multi-model fallback.

v9.8.6:
  • Multi-image support
  • OCR mode for text extraction
  • Better error messages in Persian
  • Response quality validation
"""


import base64
import logging
from typing import Sequence

from arki_project.utils.http_pool import get_client

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

_VISION_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
]

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


async def analyse_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    *,
    prompt: str = "این عکس رو کامل و دقیق تحلیل و توضیح بده. هر جزئیاتی رو بگو.",
    system_prompt: str = "",
    max_output_tokens: int = 4096,
) -> str:
    """Send an image to Gemini vision and get a text analysis.

    Tries multiple models in sequence for resilience.
    """
    b64 = base64.b64encode(image_bytes).decode()

    parts: list[dict] = []
    if prompt:
        parts.append({"text": prompt})
    parts.append({
        "inline_data": {"mime_type": mime_type, "data": b64},
    })

    body: dict = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"maxOutputTokens": max_output_tokens},
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    last_error: Exception | None = None
    for model in _VISION_MODELS:
        try:
            url = f"{BASE_URL}/models/{model}:generateContent"
            headers = {"x-goog-api-key": api_key}
            client = await get_client("gemini")
            async with client.post(url, json=body, headers=headers) as resp:

                if resp.status == 429:
                    logger.warning("Vision model %s rate limited, trying next", model)
                    continue

                if resp.status != 200:
                    err_text = await resp.text()
                    logger.warning(
                        "Vision model %s returned %d: %s",
                        model, resp.status, err_text[:200],
                    )
                    continue

                data = await resp.json()
                cands = data.get("candidates", [])
                if not cands:
                    # Check for safety block
                    block_reason = data.get("promptFeedback", {}).get("blockReason", "")
                    if block_reason:
                        return f"🛡 تصویر توسط فیلتر ایمنی بلاک شد: {block_reason}"
                    continue

                text = "".join(
                    p.get("text", "")
                    for p in cands[0].get("content", {}).get("parts", [])
                )
                if text.strip():
                    return text
        except ArkiBaseError as exc:
            logger.warning("Vision model %s error: %s", model, exc)
            last_error = exc
            continue

    raise last_error or Exception("❌ تحلیل عکس: همه مدل‌ها خطا دادند")


async def analyse_multiple_images(
    images: Sequence[tuple[bytes, str]],
    api_key: str,
    *,
    prompt: str = "این عکس‌ها رو مقایسه و تحلیل کن.",
    system_prompt: str = "",
) -> str:
    """Analyse multiple images in a single request.

    Parameters
    ----------
    images : list of (bytes, mime_type) tuples
    """
    parts: list[dict] = []
    if prompt:
        parts.append({"text": prompt})

    for img_bytes, mime in images:
        b64 = base64.b64encode(img_bytes).decode()
        parts.append({
            "inline_data": {"mime_type": mime, "data": b64},
        })

    body: dict = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"maxOutputTokens": 4096},
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    for model in _VISION_MODELS:
        try:
            url = f"{BASE_URL}/models/{model}:generateContent"
            headers = {"x-goog-api-key": api_key}
            client = await get_client("gemini")
            async with client.post(url, json=body, headers=headers) as resp:

                if resp.status != 200:
                    continue

                data = await resp.json()
                cands = data.get("candidates", [])
                if not cands:
                    continue
                text = "".join(
                    p.get("text", "")
                    for p in cands[0].get("content", {}).get("parts", [])
                )
                if text.strip():
                    return text
        except ArkiBaseError as exc:
            logger.warning("Multi-image vision %s error: %s", model, exc)
            continue

    raise Exception("❌ تحلیل عکس‌ها: همه مدل‌ها خطا دادند")


async def ocr_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
) -> str:
    """Extract text from an image using OCR-optimized prompt."""
    return await analyse_image(
        image_bytes, mime_type, api_key,
        prompt=(
            "Extract ALL text from this image exactly as written. "
            "Preserve formatting, line breaks, and structure. "
            "If it's a table, format as markdown table. "
            "Output only the extracted text, nothing else."
        ),
        max_output_tokens=8192,
    )


