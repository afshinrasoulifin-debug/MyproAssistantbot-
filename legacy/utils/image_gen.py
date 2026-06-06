
from __future__ import annotations
"""
tg_bot/utils/image_gen.py
─────────────────────────
Image generation via Pollinations.ai Flux model (free).

Features:
  • Smart prompt enhancement — detects intent (logo, product, etc.)
    and crafts optimized English prompts for best results.
  • Logo hybrid pipeline — AI generates icon/background, then Pillow
    overlays accurate text (AI image models can't spell).
  • Design variations with different seeds.
"""


import io
import logging
import re
import urllib.parse

from arki_project.utils.http_pool import get_client

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024

# ── Intent detection for prompt enhancement ──

_LOGO_WORDS = re.compile(
    r"(لوگو|logo|brand\s*mark|لوگوتایپ|logotype|نشان|emblem)",
    re.IGNORECASE,
)
_BANNER_WORDS = re.compile(
    r"(بنر|banner|هدر|header|کاور|cover)",
    re.IGNORECASE,
)
_POSTER_WORDS = re.compile(
    r"(پوستر|poster|فلایر|flyer|اعلامیه)",
    re.IGNORECASE,
)
_ICON_WORDS = re.compile(
    r"(آیکون|icon|آیکن|نماد|symbol)",
    re.IGNORECASE,
)
_PRODUCT_WORDS = re.compile(
    r"(محصول|product|شمع|candle|دکور|decor|اکسسوری|accessory)",
    re.IGNORECASE,
)


def _enhance_prompt(prompt: str) -> str:
    """
    Transform a vague user prompt into a detailed image generation prompt.
    Detects intent (logo, banner, product, etc.) and adds professional
    quality modifiers.
    """
    original = prompt.strip()
    if not original:
        return original

    # Extract brand/product name using the dedicated function
    brand_name = _extract_brand_name(original)

    # ── Logo intent ──
    if _LOGO_WORDS.search(original):
        # Check for typography/text style
        is_typo = bool(re.search(r"(تایپ|typo|font|فونت|حروف|text|متن)", original, re.IGNORECASE))
        is_minimal = bool(re.search(r"(مینیمال|minimal|ساده|simple|کلین|clean)", original, re.IGNORECASE))
        is_3d = bool(re.search(r"(سه\s*بعدی|3d|ابعادی)", original, re.IGNORECASE))

        style = "minimalist clean" if is_minimal else "professional modern"
        if is_3d:
            style = "3D rendered glossy"

        base = (
            f"{style} logo design, "
            f"{'typography wordmark' if is_typo else 'iconic symbol mark'}, "
            f"{'for brand ' + brand_name + ', ' if brand_name else ''}"
            "centered composition on dark background, "
            "high contrast, sharp edges, vector-style, "
            f"{'neon glow accents, ' if not is_minimal else ''}"
            "professional graphic design, 8K quality, "
            "behance award winning logo"
        )

        # DON'T ask AI to render text — it will misspell it
        # We'll overlay text with Pillow later
        return base

    # ── Banner intent ──
    if _BANNER_WORDS.search(original):
        return (
            "Professional wide banner design, "
            f"{'for ' + brand_name + ', ' if brand_name else ''}"
            "modern gradient background, subtle geometric patterns, "
            "clean negative space for text overlay, "
            "corporate professional style, high quality, 4K"
        )

    # ── Poster intent ──
    if _POSTER_WORDS.search(original):
        return (
            "Professional poster design, dramatic lighting, "
            f"{'for ' + brand_name + ', ' if brand_name else ''}"
            "modern layout, bold visual hierarchy, "
            "clean typography area, vibrant colors, "
            "graphic design award quality, 4K"
        )

    # ── Icon intent ──
    if _ICON_WORDS.search(original):
        return (
            "App icon design, rounded square shape, "
            f"{'for ' + brand_name + ', ' if brand_name else ''}"
            "flat design with subtle gradient, centered symbol, "
            "clean minimal, iOS style icon, high quality render"
        )

    # ── Product/candle intent ──
    if _PRODUCT_WORDS.search(original):
        return (
            "Professional product photography, studio lighting, "
            "clean white or dark background, soft shadows, "
            "commercial advertising quality, high resolution, "
            f"luxury feel, 4K detail, {original}"
        )

    # ── General: add quality modifiers ──
    # Check if prompt is already in English and detailed
    is_persian = bool(re.search(r"[\u0600-\u06FF]", original))
    if is_persian:
        # Persian prompt — add quality modifiers
        return (
            f"{original}, professional quality, high detail, "
            "sharp focus, beautiful lighting, 4K resolution"
        )
    else:
        # English — add subtle quality boost
        if len(original.split()) < 10:
            return (
                f"{original}, professional quality, high detail, "
                "sharp focus, beautiful lighting, 4K"
            )
        return original  # Already detailed


def _is_logo_request(prompt: str) -> bool:
    """Check if the prompt is requesting a logo."""
    return bool(_LOGO_WORDS.search(prompt))


def _extract_brand_name(prompt: str) -> str:
    """Extract brand/product name from prompt."""
    # Try quoted names first
    quoted = re.search(r'["\u201c]([^"\u201d]+)["\u201d]', prompt)
    if quoted:
        return quoted.group(1).strip()

    # Try "به اسم X" / "به نام X" — the actual name comes after
    name_match = re.search(
        r'(?:به\s*(?:اسم|نام))\s+(.+?)(?:\s*[,،.]|\s*$)',
        prompt, re.IGNORECASE,
    )
    if name_match:
        name = name_match.group(1).strip()
        name = re.sub(r"\s*(بساز|بکش|بزن|درست|طراحی).*$", "", name).strip()
        return name

    # Try "for X" / "named X" / "called X"
    name_match = re.search(
        r'(?:for|named|called)\s+(.+?)(?:\s*[,،.]|\s*$)',
        prompt, re.IGNORECASE,
    )
    if name_match:
        name = name_match.group(1).strip()
        name = re.sub(r"\s*(with|in|on|style|design).*$", "", name, flags=re.IGNORECASE).strip()
        return name

    return ""


async def generate_image(
    prompt: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    seed: int | None = None,
    enhance: bool = True,
) -> bytes:
    """
    Generate an image from a text prompt using Pollinations.ai Flux.

    If enhance=True (default), the prompt is automatically enhanced
    for better quality based on detected intent.

    Returns the raw image bytes (PNG/JPEG).
    Raises Exception on failure.
    """
    # Enhance prompt for better results
    if enhance:
        enhanced = _enhance_prompt(prompt)
        logger.info("Prompt enhanced: '%s' -> '%s'", prompt[:60], enhanced[:80])
    else:
        enhanced = prompt

    encoded_prompt = urllib.parse.quote(enhanced, safe="")
    url = POLLINATIONS_URL.format(prompt=encoded_prompt)

    params: dict[str, str] = {
        "width": str(width),
        "height": str(height),
        "nologo": "true",
        "model": "flux",
    }
    if seed is not None:
        params["seed"] = str(seed)

    logger.info("Generating image: %s", enhanced[:80])

    # v10.1: Route through TITANIUM shielded client
    if _TITANIUM_ACTIVE:
        full_url = str(url)
        if params:
            from urllib.parse import urlencode
            full_url += ("&" if "?" in full_url else "?") + urlencode(params)
        resp = await shielded_get(full_url, timeout=120.0, provider_name="image_gen")
        if not resp.success:
            raise Exception(f"Image generation failed (HTTP {resp.status})")
        data = resp.text.encode('latin-1') if isinstance(resp.text, str) else resp.text
        if len(data) < 1000:
            raise Exception("Received suspiciously small image data")
    else:
        import aiohttp as _aiohttp
        client = await get_client("image")
        async with client.get(
            url, params=params,
            timeout=_aiohttp.ClientTimeout(total=90),
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Image generation failed (HTTP {resp.status})")
            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type:
                raise Exception(f"Expected image, got {content_type}")
            data = await resp.read()
            if len(data) < 1000:
                raise Exception("Received suspiciously small image data")

        logger.info("Image generated: %d bytes", len(data))

    # ── Logo post-processing: overlay accurate text ──
    if _is_logo_request(prompt):
        brand = _extract_brand_name(prompt)
        if brand and len(brand) <= 30:
            data = _overlay_logo_text(data, brand)

    return data


def _overlay_logo_text(image_data: bytes, text: str) -> bytes:
    """
    Overlay brand name text on a logo image using Pillow.
    AI image models can't spell, so we add the text ourselves.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(io.BytesIO(image_data)).convert("RGBA")
        w, h = img.size

        # Create text overlay
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Find a good font
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

        font = None
        # Scale font so text spans ~60% of image width
        font_size = max(36, min(120, int(w * 0.6 / max(len(text), 1))))

        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue

        if font is None:
            font = ImageFont.load_default()

        # Measure text
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        # Position: bottom-center with a semi-transparent background bar
        x = (w - tw) // 2
        y = h - th - h // 6  # ~1/6 from bottom

        # Draw semi-transparent background behind text
        pad = 20
        bar_rect = [x - pad, y - pad, x + tw + pad, y + th + pad]
        draw.rounded_rectangle(bar_rect, radius=15, fill=(0, 0, 0, 160))

        # Draw text with slight shadow
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 200))  # Shadow
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))  # Main

        # Composite
        result = Image.alpha_composite(img, overlay).convert("RGB")

        buf = io.BytesIO()
        result.save(buf, format="PNG", quality=95)
        logger.info("Logo text overlay applied: '%s'", text)
        return buf.getvalue()

    except Exception as exc:
        logger.warning("Logo text overlay failed: %s", exc)
        return image_data  # Return original on failure


async def generate_design_variations(
    prompt: str,
    count: int = 3,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> list[bytes]:
    """Generate multiple design variations with different seeds."""
    import asyncio

    tasks = [
        generate_image(prompt, width=width, height=height, seed=i * 1000 + 42)
        for i in range(count)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    images: list[bytes] = []
    for r in results:
        if isinstance(r, bytes):
            images.append(r)
        else:
            logger.warning("Design variation failed: %s", r)

    if not images:
        raise Exception("All design variations failed.")
    return images


