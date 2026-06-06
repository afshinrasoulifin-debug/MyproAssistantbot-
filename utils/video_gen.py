from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/video_gen.py — v30.2
──────────────────────────────────
AI Video Generation.

Strategy:
  • Generate multiple AI images as frames
  • Convert frames to animated GIF
  • High quality via OperaAria / FLUX.1 / Pollinations
"""

import asyncio
import io
import logging
import re

logger = logging.getLogger(__name__)


def _enhance_video_prompt(prompt: str) -> str:
    """Enhance a video prompt for better quality."""
    original = prompt.strip()
    if not original or len(original) > 150:
        return original
    return f"{original}, cinematic, high quality, 4K, professional"


async def generate_slideshow(
    prompt: str,
    *,
    frame_count: int = 6,
    width: int = 1024,
    height: int = 576,
) -> tuple[list[bytes], str]:
    """
    Generate a series of related AI images as video frames.
    Returns (list_of_image_bytes, enhanced_prompt).
    """
    from arki_project.utils.image_gen import _generate_via_g4f, _generate_via_pollinations

    enhanced = _enhance_video_prompt(prompt)

    scene_modifiers = [
        "establishing wide shot",
        "medium shot, detailed view",
        "close-up, fine details visible",
        "dynamic angle with depth",
        "dramatic cinematic lighting",
        "aerial panoramic view",
        "side profile, artistic composition",
        "golden hour lighting, warm tones",
    ]

    # Generate frames — use OperaAria for best quality
    tasks = []
    for i in range(frame_count):
        modifier = scene_modifiers[i % len(scene_modifiers)]
        frame_prompt = f"{enhanced}, {modifier}, frame {i+1}"
        tasks.append(_generate_via_g4f(frame_prompt, "OperaAria", "aria"))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    frames = []
    for i, r in enumerate(results):
        if isinstance(r, bytes) and len(r) > 1000:
            frames.append(r)
        else:
            logger.warning("Frame %d failed: %s", i, r if isinstance(r, Exception) else "no data")

    # If OperaAria failed, try Pollinations for missing frames
    if len(frames) < 2:
        logger.info("Retrying frames with Pollinations...")
        for i in range(frame_count):
            if len(frames) >= frame_count:
                break
            modifier = scene_modifiers[i % len(scene_modifiers)]
            frame_prompt = f"{enhanced}, {modifier}"
            data = await _generate_via_pollinations(
                frame_prompt, width=width, height=height, seed=i * 1234 + 42,
            )
            if data and len(data) > 1000:
                frames.append(data)

    if not frames:
        raise Exception("تمام فریم‌ها ناموفق بودند. لطفاً دوباره تلاش کنید.")

    return frames, enhanced


async def frames_to_gif(frames: list[bytes], fps: int = 2) -> bytes:
    """Convert image frames to animated GIF using Pillow."""
    try:
        from PIL import Image

        pil_frames = []
        target_size = None

        for frame_bytes in frames:
            img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
            if target_size is None:
                target_size = img.size
            else:
                img = img.resize(target_size, Image.LANCZOS)
            pil_frames.append(img)

        if not pil_frames:
            raise Exception("هیچ فریم معتبری برای GIF وجود ندارد")

        buf = io.BytesIO()
        duration_ms = 1000 // fps
        pil_frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=pil_frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        logger.info("GIF created: %d frames, %d bytes", len(pil_frames), buf.tell())
        return buf.getvalue()
    except ImportError:
        raise Exception("Pillow مورد نیاز است: pip install Pillow")


async def generate_video(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 576,
    duration: int = 4,
    mode: str = "auto",
) -> tuple[bytes, str, str]:
    """
    Generate video (AI slideshow → animated GIF).
    
    Returns: (video_bytes, format_extension, provider_name)
    """
    frames, enhanced = await generate_slideshow(
        prompt, frame_count=6, width=width, height=height,
    )
    gif_data = await frames_to_gif(frames, fps=2)
    return gif_data, "gif", f"AI Slideshow ({len(frames)} frames)"
