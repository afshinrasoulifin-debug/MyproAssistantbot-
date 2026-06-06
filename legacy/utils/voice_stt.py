
"""
tg_bot/utils/voice_stt.py — Voice-to-Text Engines
═══════════════════════════════════════════════════
Faster-Whisper (free, local CPU) with Gemini fallback.
"""
import asyncio
import logging
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


async def transcribe_audio(audio_path: str, language: str = "fa") -> str:
    """
    Transcribe audio — tries Faster-Whisper first (free), falls back to Gemini.
    """
    # Try Faster-Whisper (free, no API quota)
    result = await _try_faster_whisper(audio_path, language)
    if result:
        return result
    
    # Fallback: return empty (caller will use Gemini)
    return ""


async def _try_faster_whisper(audio_path: str, language: str) -> str:
    """CPU-based STT using Faster-Whisper."""
    try:
        from faster_whisper import WhisperModel
        
        model = WhisperModel("small", device="cpu", compute_type="int8")
        
        def _sync() -> Any:
            segments, _ = model.transcribe(audio_path, language=language)
            return " ".join(seg.text for seg in segments)
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync)
    except ImportError:
        logger.debug("faster-whisper not installed")
        return ""
    except Exception as e:
        logger.warning("Faster-Whisper failed: %s", e)
        return ""


