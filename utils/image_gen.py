from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/image_gen.py — v30.2
──────────────────────────────────
AI Image Generation — multi-provider via g4f.

Providers (fallback chain):
  1. OperaAria        — FREE, no key, high quality (1024×1024 PNG)
  2. FLUX.1-dev (BFL) — FREE via HF Spaces, FLUX model
  3. Pollinations.ai  — FREE, no key (may rate-limit datacenter IPs)

Features:
  • Smart prompt enhancement — detects intent (logo, product, etc.)
  • Multi-provider fallback chain
  • HD mode with model selection
  • Multi-style simultaneous generation
  • Logo text overlay with Pillow
"""

import asyncio
import io
import logging
import os
import re
import urllib.parse

logger = logging.getLogger(__name__)

# ── Provider config ──
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024

# ── Available models ──
IMAGE_MODELS = {
    "flux": "flux",
    "flux-pro": "flux-pro",
    "flux-realism": "flux-realism",
    "flux-anime": "flux-anime",
    "flux-3d": "flux-3d",
    "flux-cablyai": "flux-cablyai",
    "turbo": "turbo",
}

# ── Prompt enhancement ──

_LOGO_KEYWORDS = [
    "logo", "لوگو", "brand", "برند", "emblem", "نشان",
    "icon", "آیکون", "monogram", "مونوگرام",
]

_PRODUCT_KEYWORDS = [
    "product", "محصول", "candle", "شمع", "packaging", "بسته‌بندی",
    "bottle", "بطری", "jar", "شیشه", "box", "جعبه",
]


def _is_logo_request(prompt: str) -> bool:
    lower = prompt.lower()
    return any(kw in lower for kw in _LOGO_KEYWORDS)


def _is_product_request(prompt: str) -> bool:
    lower = prompt.lower()
    return any(kw in lower for kw in _PRODUCT_KEYWORDS)


def _extract_brand_name(prompt: str) -> str:
    patterns = [
        r"(?:logo|لوگو|brand|برند)\s+(?:for|برای|of)?\s*['\"]?([A-Za-z\u0600-\u06FF]+)",
        r"['\"]([A-Za-z\u0600-\u06FF]{2,20})['\"]",
    ]
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _enhance_prompt(prompt: str) -> str:
    """Enhance prompt for better quality results."""
    original = prompt.strip()
    if not original:
        return original

    if len(original) > 200:
        return original

    has_persian = bool(re.search(r'[\u0600-\u06FF]', original))

    if _is_logo_request(original):
        return (
            f"Professional minimalist logo design: {original}, "
            "clean vector style, centered composition, "
            "white background, modern branding, high contrast"
        )

    if _is_product_request(original):
        return (
            f"Professional product photography: {original}, "
            "studio lighting, soft shadows, commercial quality, "
            "clean background, 4K detail"
        )

    quality = (
        ", professional quality, detailed, high resolution, "
        "beautiful lighting, sharp focus"
    )
    return f"{original}{quality}"


def _extract_real_url(raw_url: str) -> str | None:
    """Extract real download URL from g4f relative URL format.
    
    g4f returns: /media/...?url=https%3A//actual-cdn.com/image.png
    We need to extract the url= parameter value.
    """
    if not raw_url:
        return None

    # Already a full URL
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url

    # Extract from ?url= parameter
    if "?url=" in raw_url or "&url=" in raw_url:
        try:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            urls = qs.get("url", [])
            if urls:
                return urls[0]
        except Exception:
            pass

    # Try regex extraction
    match = re.search(r'url=(https?[^\s&]+)', raw_url)
    if match:
        return urllib.parse.unquote(match.group(1))

    return None


async def _generate_via_g4f(
    prompt: str,
    provider_name: str = "OperaAria",
    model: str = "aria",
) -> bytes | None:
    """Generate image via g4f provider. Returns image bytes or None."""
    try:
        from g4f.client import AsyncClient
        from g4f import Provider

        prov = getattr(Provider, provider_name, None)
        if prov is None:
            logger.warning("g4f provider %s not found", provider_name)
            return None

        client = AsyncClient()
        response = await client.images.generate(
            model=model,
            prompt=prompt,
            provider=prov,
        )

        if not response.data:
            logger.warning("g4f %s: no image data returned", provider_name)
            return None

        img = response.data[0]
        url = getattr(img, "url", None)
        b64 = getattr(img, "b64_json", None)

        if b64:
            import base64
            data = base64.b64decode(b64)
            if len(data) > 1000:
                logger.info("g4f %s: %d bytes (b64)", provider_name, len(data))
                return data

        if url:
            real_url = _extract_real_url(url)
            if real_url:
                return await _download_image(real_url)

        logger.warning("g4f %s: no usable image in response", provider_name)
        return None

    except Exception as exc:
        err = str(exc)
        # Sometimes g4f raises but the URL is in the error message
        real_url = _extract_real_url(err)
        if real_url:
            logger.info("g4f %s: extracting URL from error", provider_name)
            return await _download_image(real_url)
        logger.warning("g4f %s failed: %s", provider_name, err[:200])
        return None


async def _download_image(url: str) -> bytes | None:
    """Download image from URL. Returns bytes or None."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 1000:
                ct = resp.headers.get("content-type", "")
                if "image" in ct or "octet" in ct or len(resp.content) > 5000:
                    logger.info("Downloaded image: %d bytes from %s", len(resp.content), url[:80])
                    return resp.content
    except ImportError:
        # Fallback to aiohttp
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if len(data) > 1000:
                            return data
        except Exception as e2:
            logger.warning("aiohttp download failed: %s", e2)
    except Exception as exc:
        logger.warning("Download failed from %s: %s", url[:80], exc)
    return None


async def _generate_via_pollinations(
    prompt: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    model: str = "flux",
    seed: int | None = None,
) -> bytes | None:
    """Generate image via Pollinations.ai. Returns bytes or None."""
    try:
        encoded = urllib.parse.quote(prompt, safe="")
        url = POLLINATIONS_URL.format(prompt=encoded)
        params = {
            "width": str(width),
            "height": str(height),
            "nologo": "true",
            "model": model,
        }
        if seed is not None:
            params["seed"] = str(seed)

        full_url = url + "?" + urllib.parse.urlencode(params)
        data = await _download_image(full_url)
        if data and len(data) > 1000:
            logger.info("Pollinations: %d bytes", len(data))
            return data
        return None
    except Exception as exc:
        logger.warning("Pollinations failed: %s", exc)
        return None


async def generate_image(
    prompt: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    seed: int | None = None,
    enhance: bool = True,
) -> bytes:
    """
    Generate an image from a text prompt.
    
    Uses multi-provider fallback chain:
      1. OperaAria (g4f) — highest quality
      2. FLUX.1-dev (g4f) — good quality
      3. Pollinations.ai — reliable fallback
    
    Returns raw image bytes.
    Raises Exception on all providers failing.
    """
    if enhance:
        enhanced = _enhance_prompt(prompt)
        logger.info("Prompt enhanced: '%s' -> '%s'", prompt[:60], enhanced[:80])
    else:
        enhanced = prompt

    # Provider 1: OperaAria (best quality, ~1MB PNGs)
    logger.info("Trying OperaAria...")
    data = await _generate_via_g4f(enhanced, "OperaAria", "aria")
    if data:
        return _post_process(data, prompt)

    # Provider 2: FLUX.1-dev via HuggingFace Spaces
    logger.info("Trying FLUX.1-dev...")
    data = await _generate_via_g4f(enhanced, "BlackForestLabs_Flux1Dev", "flux-dev")
    if data:
        return _post_process(data, prompt)

    # Provider 3: Pollinations.ai
    logger.info("Trying Pollinations...")
    data = await _generate_via_pollinations(
        enhanced, width=width, height=height, seed=seed,
    )
    if data:
        return _post_process(data, prompt)

    raise Exception(
        "تمام سرویس‌های تولید تصویر در دسترس نیستند. لطفاً دوباره تلاش کنید."
    )


def _post_process(data: bytes, prompt: str) -> bytes:
    """Post-process: add logo text overlay if needed."""
    if _is_logo_request(prompt):
        brand = _extract_brand_name(prompt)
        if brand and len(brand) <= 30:
            data = _overlay_logo_text(data, brand)
    return data


async def generate_image_hd(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    model: str = "flux-realism",
    seed: int | None = None,
    enhance: bool = True,
) -> bytes:
    """Generate HD image. Tries g4f first, Pollinations as fallback."""
    if enhance:
        enhanced = _enhance_prompt(prompt)
    else:
        enhanced = prompt

    # For HD, try OperaAria first (produces highest quality)
    data = await _generate_via_g4f(enhanced, "OperaAria", "aria")
    if data:
        return _post_process(data, prompt)

    # Fallback to Pollinations with specific model
    data = await _generate_via_pollinations(
        enhanced, width=width, height=height, model=model, seed=seed,
    )
    if data:
        return _post_process(data, prompt)

    # Last resort: standard generate
    return await generate_image(prompt, width=width, height=height, seed=seed, enhance=enhance)


async def generate_image_multi_style(
    prompt: str,
    *,
    styles: list[str] | None = None,
    width: int = 1024,
    height: int = 1024,
) -> list[tuple[bytes, str]]:
    """Generate images in multiple art styles. Returns list of (bytes, style_name)."""
    if styles is None:
        styles = ["realism", "anime", "3d", "standard", "artistic"]

    style_prompts = {
        "realism": f"{prompt}, photorealistic, studio photography, 8K detail",
        "anime": f"{prompt}, anime art style, beautiful illustration, detailed",
        "3d": f"{prompt}, 3D render, cinema 4D, octane render, professional",
        "standard": f"{prompt}, high quality digital art, professional",
        "artistic": f"{prompt}, oil painting style, fine art, masterpiece",
    }

    tasks = []
    for style in styles:
        sp = style_prompts.get(style, f"{prompt}, {style} style")
        tasks.append(_generate_via_g4f(sp, "OperaAria", "aria"))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    images = []
    for style, result in zip(styles, results):
        if isinstance(result, bytes) and len(result) > 1000:
            images.append((result, style))
        else:
            logger.warning("Style %s failed: %s", style, result if isinstance(result, Exception) else "no data")

    if not images:
        # Fallback: generate at least one
        data = await generate_image(prompt, width=width, height=height)
        images.append((data, "standard"))

    return images


async def generate_design_variations(
    prompt: str,
    *,
    count: int = 3,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> list[bytes]:
    """Generate multiple design variations of the same prompt."""
    variations = [
        f"{prompt}, variation 1, unique creative interpretation",
        f"{prompt}, variation 2, different color scheme and composition",
        f"{prompt}, variation 3, alternative artistic style",
    ][:count]

    tasks = [
        _generate_via_g4f(v, "OperaAria", "aria")
        for v in variations
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    images = []
    for r in results:
        if isinstance(r, bytes) and len(r) > 1000:
            images.append(r)

    if not images:
        # Fallback
        img = await generate_image(prompt, width=width, height=height)
        images.append(img)

    return images


def _overlay_logo_text(image_data: bytes, text: str) -> bytes:
    """Overlay brand name text on a logo image using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(io.BytesIO(image_data)).convert("RGBA")
        w, h = img.size

        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        ]

        font_size = w // 10
        font = None
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except (OSError, IOError):
                continue

        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                return image_data

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (w - tw) // 2
        y = int(h * 0.75)

        draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 128), font=font)
        draw.text((x, y), text, fill=(255, 255, 255, 230), font=font)

        result = Image.alpha_composite(img, overlay).convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="PNG", quality=95)
        return buf.getvalue()
    except ImportError:
        return image_data
    except Exception as exc:
        logger.warning("Logo overlay failed: %s", exc)
        return image_data
