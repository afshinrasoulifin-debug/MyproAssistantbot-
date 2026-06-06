
from __future__ import annotations
"""
tg_bot/utils/tts_engine.py — Text-to-Speech Engine v29.0.0
Convert text to speech audio files.
"""
import logging
import os
import tempfile
from typing import Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-Speech with multiple backend support."""

    def __init__(self) -> None:
        self._backend = "gtts"  # Default: Google TTS

    async def synthesize(self, text: str, language: str = "fa",
                        output_path: str = None) -> Optional[str]:
        """Convert text to speech and return audio file path."""
        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp3")

        try:
            # Try Google TTS
            from gtts import gTTS
            tts = gTTS(text=text, lang=language)
            tts.save(output_path)
            return output_path
        except ImportError:
            logger.warning("gTTS not installed, trying edge-tts")

        try:
            # Try edge-tts
            import edge_tts
            voice = "fa-IR-FaridNeural" if language == "fa" else "en-US-GuyNeural"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return output_path
        except ImportError:
            logger.error("No TTS backend available (install gtts or edge-tts)")
            return None

    async def text_to_voice_message(self, bot: Any, chat_id: int, text: str,
                                    language: str = "fa") -> Any:
        """Generate and send voice message."""
        path = await self.synthesize(text, language)
        if path and os.path.exists(path):
            try:
                from aiogram.types import FSInputFile
                voice = FSInputFile(path)
                await bot.send_voice(chat_id, voice)
            finally:
                os.unlink(path)


_engine: Optional[TTSEngine] = None

def get_tts_engine() -> TTSEngine:
    global _engine
    if _engine is None:
        _engine = TTSEngine()
    return _engine


