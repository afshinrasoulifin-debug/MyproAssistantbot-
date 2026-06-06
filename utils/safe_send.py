
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/safe_send.py
─────────────────────────
Safe wrappers for common Telegram operations that can fail silently.

v29.0.0:
  • safe_reply: retry with exponential backoff on FloodWait
  • safe_edit_text: handle more error types gracefully
  • safe_delete: handle more edge cases
  • safe_answer_callback: new helper for callback queries
  • send_long_text: auto-split long messages
"""


import asyncio
import logging

from aiogram.types import CallbackQuery, Message
from arki_project.utils.outbound_queue import get_outbound_queue

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


async def safe_delete(msg: Message | None) -> None:
    """Delete a message, silently ignoring any errors."""
    if msg is None:
        return
    try:
        await msg.delete()
    except ArkiBaseError as exc:
        logger.debug("safe_delete failed: %s", exc)


async def safe_edit_text(
    msg: Message | CallbackQuery | None,
    text: str,
    *,
    parse_mode: str | None = "Markdown",
    reply_markup: object = None,
) -> None:
    """
    Edit message text safely. Handles:
    - Message already deleted
    - Message too old (>48h)
    - Markdown parse failures → retry without parse_mode
    - Content unchanged (message is not modified)
    """
    if msg is None:
        return

    # If it's a CallbackQuery, get the message
    actual_msg: Message | None = None
    if isinstance(msg, CallbackQuery):
        actual_msg = msg.message  # type: ignore[assignment]
    else:
        actual_msg = msg

    if actual_msg is None:
        return

    kwargs: dict = {"text": text}
    if parse_mode:
        kwargs["parse_mode"] = parse_mode
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup

    try:
        await actual_msg.edit_text(**kwargs)
    except ArkiBaseError as exc:
        err_str = str(exc).lower()

        # Content unchanged — not an error
        if "message is not modified" in err_str:
            return

        # If Markdown parsing failed, retry without parse_mode
        if parse_mode and ("can't parse" in err_str or "parse" in err_str):
            try:
                kwargs.pop("parse_mode", None)
                await actual_msg.edit_text(**kwargs)
                return
            except ArkiBaseError as e:
                logger.debug("Suppressed: %s", e)

        # Message too old or deleted — not worth logging as warning
        if "message to edit not found" in err_str or "too old" in err_str:
            logger.debug("safe_edit_text: message gone: %s", exc)
            return

        logger.warning("safe_edit_text failed: %s", exc)


async def safe_reply(
    msg: Message,
    text: str,
    *,
    parse_mode: str | None = "Markdown",
    reply_markup: object = None,
    max_retries: int = 2,
) -> Message | None:
    """
    Send a reply with Markdown, falling back to plain text on parse error.
    Retries on FloodWait with exponential backoff.
    Returns the sent message or None on failure.
    """
    kwargs: dict = {"text": text}
    if parse_mode:
        kwargs["parse_mode"] = parse_mode
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup

    # v9.5: Route through outbound queue for rate limiting
    _queue = get_outbound_queue()

    for attempt in range(max_retries + 1):
        try:
            return await msg.answer(**kwargs)
        except ArkiBaseError as exc:
            err_str = str(exc).lower()

            # Parse error → fall back to plain text
            if parse_mode and ("can't parse" in err_str or "parse" in err_str):
                try:
                    kwargs.pop("parse_mode", None)
                    return await msg.answer(**kwargs)
                except ArkiBaseError as e:
                    logger.debug("Suppressed: %s", e)
                break

            # Flood wait → backoff and retry
            if "flood" in err_str or "retry_after" in err_str:
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    "FloodWait on safe_reply, waiting %ds (attempt %d/%d)",
                    wait_time, attempt + 1, max_retries,
                )
                if attempt < max_retries:
                    await asyncio.sleep(wait_time)
                    continue

            # Chat not found or blocked by user
            if "chat not found" in err_str or "blocked" in err_str:
                logger.warning(
                    "safe_reply: user blocked or chat gone: %s",
                    getattr(msg, "chat", "?"),
                )
                return None

            logger.error(
                "safe_reply FAILED for chat %s: %s",
                getattr(msg, "chat", "?"), exc,
            )
            break

    return None


async def safe_answer_callback(
    callback: CallbackQuery,
    text: str = "",
    *,
    show_alert: bool = False,
) -> None:
    """Answer a callback query safely."""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except ArkiBaseError as exc:
        logger.debug("safe_answer_callback failed: %s", exc)


async def send_long_text(
    msg: Message,
    text: str,
    *,
    parse_mode: str | None = "Markdown",
    reply_markup: object = None,
    chunk_limit: int = 4080,
) -> list[Message]:
    """
    Send a long text message, automatically splitting into chunks.
    Returns list of sent messages.
    """
    from arki_project.utils.text_processing import split_for_telegram

    chunks = split_for_telegram(text, limit=chunk_limit)
    sent_messages: list[Message] = []

    for i, chunk in enumerate(chunks):
        # Only add reply_markup to the last chunk
        rm = reply_markup if i == len(chunks) - 1 else None
        result = await safe_reply(
            msg, chunk, parse_mode=parse_mode, reply_markup=rm,
        )
        if result:
            sent_messages.append(result)

    return sent_messages


