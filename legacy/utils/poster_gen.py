
from __future__ import annotations
"""
tg_bot/utils/poster_gen.py
──────────────────────────
Professional sale poster generator using Pillow + raqm (HarfBuzz).
Creates beautiful Persian-text posters for Instagram/Telegram.

Templates:
  1. sale      — Red/gold sale poster (1080x1080)
  2. product   — Clean product announcement (1080x1080)
  3. story     — Instagram story (1080x1920)
  4. minimal   — Modern minimal design (1080x1080)
"""


import io

from PIL import Image, ImageDraw, ImageFont

# ── TITANIUM v29.0 Integration ──


# ── Fonts ──
_FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
_FONT_REG = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"

# ── Text rendering helper ──
def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str | tuple = "white",
    anchor: str = "mm",
) -> None:
    """Draw Persian RTL text with proper shaping."""
    draw.text(
        xy, text, fill=fill, font=font,
        anchor=anchor, direction="rtl", language="fa",
    )


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_FONT_BOLD if bold else _FONT_REG, size)


def _gradient(
    w: int, h: int,
    color1: tuple[int, ...],
    color2: tuple[int, ...],
    vertical: bool = True,
) -> Image.Image:
    """Create a gradient background using fast 1-pixel strip + resize."""
    # Create a tiny 1-pixel strip and let Pillow's bilinear resize
    # handle the interpolation — 100x faster than per-pixel draw.
    if vertical:
        strip = Image.new("RGB", (1, 2))
        strip.putpixel((0, 0), color1[:3])
        strip.putpixel((0, 1), color2[:3])
        return strip.resize((w, h), Image.BILINEAR)
    else:
        strip = Image.new("RGB", (2, 1))
        strip.putpixel((0, 0), color1[:3])
        strip.putpixel((1, 0), color2[:3])
        return strip.resize((w, h), Image.BILINEAR)


# _add_decorations removed — was dead code (never called).


# ═══════════ Template 1: Sale Poster ═══════════

def poster_sale(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Red/gold sale poster."""
    w, h = size

    # Gradient background: deep red to dark
    img = _gradient(w, h, (180, 20, 30), (40, 5, 10))
    draw = ImageDraw.Draw(img)

    # Gold banner stripe
    banner_y = h // 6
    draw.rectangle([0, banner_y - 40, w, banner_y + 40], fill=(212, 175, 55))
    _text(draw, (w // 2, banner_y), "🔥 جشنواره فروش ویژه 🔥", _font(32), fill="black")

    # Product name — big
    _text(draw, (w // 2, h * 2 // 5), product, _font(52), fill="white")

    # Discount badge
    if discount:
        cx, cy = w // 2, h * 3 // 5
        badge_r = 90
        draw.ellipse(
            [cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r],
            fill=(212, 175, 55),
        )
        _text(draw, (cx, cy - 15), discount, _font(42), fill=(180, 20, 30))
        _text(draw, (cx, cy + 30), "تخفیف", _font(22), fill=(180, 20, 30))

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 4), f"💰 {price} تومان", _font(36), fill=(212, 175, 55))

    # Subtitle / CTA
    cta = subtitle or "برای سفارش پیام بدید 📩"
    draw.rectangle([0, h - 80, w, h], fill=(0, 0, 0, 128))
    _text(draw, (w // 2, h - 40), cta, _font(26, bold=False), fill="white")

    # Border
    draw.rectangle([10, 10, w - 10, h - 10], outline=(212, 175, 55), width=3)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 2: Product Announcement ═══════════

def poster_product(
    product: str,
    description: str = "",
    price: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Clean modern product announcement."""
    w, h = size

    # Dark elegant gradient
    img = _gradient(w, h, (15, 15, 35), (30, 30, 60))
    draw = ImageDraw.Draw(img)

    # Accent line
    accent = (100, 200, 255)
    draw.rectangle([w // 4, h // 6, 3 * w // 4, h // 6 + 3], fill=accent)

    # Header
    _text(draw, (w // 2, h // 5), "✨ محصول جدید ✨", _font(30), fill=accent)

    # Product name
    _text(draw, (w // 2, h * 2 // 5), product, _font(48), fill="white")

    # Description
    if description:
        # Split into lines
        words = description.split()
        lines = []
        line = ""
        for word in words:
            if len(line + " " + word) > 30:
                lines.append(line.strip())
                line = word
            else:
                line += " " + word
        if line:
            lines.append(line.strip())

        y_start = h // 2 + 20
        for i, ln in enumerate(lines[:4]):
            _text(draw, (w // 2, y_start + i * 45), ln, _font(24, bold=False), fill=(200, 200, 220))

    # Price tag
    if price:
        py = h * 3 // 4 + 20
        draw.rounded_rectangle(
            [w // 4, py - 30, 3 * w // 4, py + 30],
            radius=15, fill=accent,
        )
        _text(draw, (w // 2, py), f"{price} تومان", _font(30), fill=(15, 15, 35))

    # CTA
    _text(draw, (w // 2, h - 60), "برای اطلاعات بیشتر پیام بدید 📩", _font(22, bold=False), fill=(150, 150, 170))

    # Accent line bottom
    draw.rectangle([w // 4, h - 30, 3 * w // 4, h - 27], fill=accent)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 3: Instagram Story ═══════════

def poster_story(
    product: str,
    price: str = "",
    discount: str = "",
    cta: str = "",
    size: tuple[int, int] = (1080, 1920),
) -> bytes:
    """Instagram story sized poster."""
    w, h = size

    # Vibrant gradient
    img = _gradient(w, h, (75, 0, 130), (200, 50, 80))
    draw = ImageDraw.Draw(img)

    # Top section
    _text(draw, (w // 2, h // 6), "⭐ پیشنهاد ویژه ⭐", _font(38), fill=(255, 220, 100))

    # Main product
    _text(draw, (w // 2, h // 3), product, _font(56), fill="white")

    # Discount
    if discount:
        cy = h // 2
        badge_r = 110
        draw.ellipse(
            [w // 2 - badge_r, cy - badge_r, w // 2 + badge_r, cy + badge_r],
            fill=(255, 220, 100),
        )
        _text(draw, (w // 2, cy - 20), discount, _font(50), fill=(75, 0, 130))
        _text(draw, (w // 2, cy + 35), "تخفیف", _font(26), fill=(75, 0, 130))

    # Price
    if price:
        _text(draw, (w // 2, h * 2 // 3), f"💰 {price} تومان", _font(40), fill=(255, 220, 100))

    # CTA
    cta_text = cta or "👆 بالا بکشید | لینک در بیو"
    draw.rounded_rectangle(
        [60, h - 200, w - 60, h - 130],
        radius=25, fill=(255, 255, 255),
    )
    _text(draw, (w // 2, h - 165), cta_text, _font(28), fill=(75, 0, 130))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 4: Minimal ═══════════

def poster_minimal(
    product: str,
    price: str = "",
    tagline: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Modern minimal white design."""
    w, h = size

    img = Image.new("RGB", (w, h), (250, 248, 245))
    draw = ImageDraw.Draw(img)

    # Thin accent bar at top
    draw.rectangle([0, 0, w, 6], fill=(30, 30, 30))

    # Product name
    _text(draw, (w // 2, h // 3), product, _font(50), fill=(30, 30, 30))

    # Tagline
    if tagline:
        _text(draw, (w // 2, h // 3 + 70), tagline, _font(24, bold=False), fill=(100, 100, 100))

    # Divider
    draw.rectangle([w // 3, h // 2, 2 * w // 3, h // 2 + 2], fill=(200, 200, 200))

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 5), f"{price} تومان", _font(38), fill=(30, 30, 30))

    # Bottom accent
    draw.rectangle([0, h - 6, w, h], fill=(30, 30, 30))

    # CTA
    _text(draw, (w // 2, h * 4 // 5), "سفارش: پیام در دایرکت 📩", _font(24, bold=False), fill=(100, 100, 100))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Main dispatcher ═══════════

TEMPLATES = {
    "sale": poster_sale,
    "product": poster_product,
    "story": poster_story,
    "minimal": poster_minimal,
}


def generate_poster(
    template: str,
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
) -> bytes:
    """Generate a poster image. Returns PNG bytes."""
    func = TEMPLATES.get(template, poster_sale)

    if template == "sale":
        return func(product=product, price=price, discount=discount, subtitle=subtitle)
    elif template == "story":
        return func(product=product, price=price, discount=discount, cta=subtitle)
    elif template == "product":
        return func(product=product, description=subtitle, price=price)
    elif template == "minimal":
        return func(product=product, price=price, tagline=subtitle)
    else:
        return func(product=product, price=price, discount=discount, subtitle=subtitle)


# ═══════════ Template 5: Luxury Gold ═══════════

def poster_luxury(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Luxury black & gold poster — premium feel."""
    w, h = size
    img = Image.new("RGB", (w, h), (10, 10, 10))
    draw = ImageDraw.Draw(img)

    # Gold frame with double border
    gold = (212, 175, 55)
    draw.rectangle([20, 20, w - 20, h - 20], outline=gold, width=2)
    draw.rectangle([35, 35, w - 35, h - 35], outline=gold, width=1)

    # Corner ornaments (L shapes)
    for cx, cy, dx, dy in [(40, 40, 1, 1), (w-40, 40, -1, 1),
                            (40, h-40, 1, -1), (w-40, h-40, -1, -1)]:
        draw.line([(cx, cy), (cx + dx*60, cy)], fill=gold, width=2)
        draw.line([(cx, cy), (cx, cy + dy*60)], fill=gold, width=2)

    # Header
    _text(draw, (w // 2, h // 5), "✦ لوکس کالکشن ✦", _font(28), fill=gold)
    # Divider
    draw.rectangle([w//4, h//5+30, 3*w//4, h//5+31], fill=gold)

    # Product
    _text(draw, (w // 2, h * 2 // 5), product, _font(50), fill="white")

    # Price in gold box
    if price:
        py = h * 3 // 5
        draw.rounded_rectangle([w//3, py-28, 2*w//3, py+28], radius=14, fill=gold)
        _text(draw, (w // 2, py), f"{price} تومان", _font(30), fill=(10, 10, 10))

    # Discount badge
    if discount:
        cx, cy = w * 4 // 5, h // 4
        draw.ellipse([cx-50, cy-50, cx+50, cy+50], fill=(180, 20, 30))
        _text(draw, (cx, cy), discount, _font(28), fill="white")

    # CTA
    cta = subtitle or "سفارش اختصاصی — پیام در دایرکت"
    _text(draw, (w // 2, h * 4 // 5), cta, _font(22, bold=False), fill=gold)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 6: Neon Glow ═══════════

def poster_neon(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Neon cyberpunk style poster."""
    w, h = size

    # Dark background
    img = _gradient(w, h, (5, 0, 30), (20, 0, 50))
    draw = ImageDraw.Draw(img)

    # Neon accent colors
    pink = (255, 20, 147)
    cyan = (0, 255, 255)

    # Horizontal neon lines
    for y_off in [h//6, h - h//6]:
        draw.rectangle([60, y_off, w-60, y_off+3], fill=pink)
        draw.rectangle([60, y_off+6, w-60, y_off+9], fill=cyan)

    # Grid lines (subtle)
    for i in range(0, w, 60):
        draw.line([(i, 0), (i, h)], fill=(20, 10, 50), width=1)
    for i in range(0, h, 60):
        draw.line([(0, i), (w, i)], fill=(20, 10, 50), width=1)

    # Header
    _text(draw, (w // 2, h // 4), "⚡ فروش ویژه ⚡", _font(36), fill=cyan)

    # Product name with glow effect (double render)
    _text(draw, (w // 2 + 2, h // 2 + 2), product, _font(52), fill=pink)
    _text(draw, (w // 2, h // 2), product, _font(52), fill="white")

    # Discount
    if discount:
        draw.rounded_rectangle(
            [w//3, h*3//5-25, 2*w//3, h*3//5+25],
            radius=12, fill=pink,
        )
        _text(draw, (w // 2, h * 3 // 5), f"{discount} تخفیف", _font(28), fill="white")

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 4), f"💰 {price} تومان", _font(34), fill=cyan)

    # CTA
    cta = subtitle or "⚡ فقط امشب — لینک در بیو"
    _text(draw, (w // 2, h * 7 // 8), cta, _font(24, bold=False), fill=(180, 180, 200))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 7: Nature/Organic ═══════════

def poster_nature(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Earthy nature-inspired poster for organic/eco brands."""
    w, h = size

    # Warm earth gradient
    img = _gradient(w, h, (245, 235, 220), (200, 180, 150))
    draw = ImageDraw.Draw(img)

    earth = (101, 67, 33)
    green = (46, 125, 50)
    cream = (245, 235, 220)

    # Leaf/organic border
    draw.rectangle([30, 30, w-30, h-30], outline=green, width=2)

    # Top leaf decoration
    _text(draw, (w // 2, h // 8), "🌿 طبیعی و ارگانیک 🌿", _font(28), fill=green)

    # Product name
    _text(draw, (w // 2, h * 2 // 5), product, _font(48), fill=earth)

    # Organic badge
    if discount:
        cx, cy = w // 2, h * 3 // 5
        # Rounded rectangle badge
        draw.rounded_rectangle(
            [cx-100, cy-30, cx+100, cy+30],
            radius=15, fill=green,
        )
        _text(draw, (cx, cy), f"{discount} تخفیف", _font(24), fill=cream)

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 4 - 10), f"🏷 {price} تومان", _font(34), fill=earth)

    # CTA
    cta = subtitle or "محصول ۱۰۰٪ طبیعی — سفارش در دایرکت 🌱"
    _text(draw, (w // 2, h * 7 // 8), cta, _font(22, bold=False), fill=(120, 100, 70))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 8: Gradient Modern ═══════════

def poster_gradient(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Bold gradient modern poster."""
    w, h = size

    # Vibrant gradient
    img = _gradient(w, h, (99, 102, 241), (236, 72, 153))
    draw = ImageDraw.Draw(img)

    # Subtle overlay circles (decorative)
    for cx, cy, r in [(w//4, h//4, 200), (3*w//4, 3*h//4, 250), (w//2, h//2, 150)]:
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(255,255,255,30), width=2)

    # Header
    _text(draw, (w // 2, h // 5), "🚀 پیشنهاد شگفت‌انگیز", _font(34), fill="white")

    # Product — bold & big
    _text(draw, (w // 2, h * 2 // 5), product, _font(54), fill="white")

    # Discount in pill shape
    if discount:
        draw.rounded_rectangle(
            [w//3-20, h//2+10, 2*w//3+20, h//2+60],
            radius=25, fill="white",
        )
        _text(draw, (w // 2, h // 2 + 35), f"🔥 {discount} تخفیف", _font(26), fill=(99, 102, 241))

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 4), f"{price} تومان", _font(40), fill="white")

    # CTA
    cta = subtitle or "همین الان سفارش بده! 👇"
    draw.rounded_rectangle(
        [w//4, h*7//8-25, 3*w//4, h*7//8+25],
        radius=20, fill="white",
    )
    _text(draw, (w // 2, h * 7 // 8), cta, _font(24), fill=(99, 102, 241))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 9: Vintage Retro ═══════════

def poster_vintage(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Vintage/retro style poster with warm tones."""
    w, h = size

    # Warm vintage background
    img = Image.new("RGB", (w, h), (243, 229, 209))
    draw = ImageDraw.Draw(img)

    brown = (101, 67, 33)
    dark_red = (139, 0, 0)
    cream = (243, 229, 209)

    # Double border
    draw.rectangle([15, 15, w-15, h-15], outline=brown, width=3)
    draw.rectangle([25, 25, w-25, h-25], outline=brown, width=1)

    # Top banner
    draw.rectangle([0, h//7-30, w, h//7+30], fill=dark_red)
    _text(draw, (w // 2, h // 7), "★ پیشنهاد ویژه ★", _font(32), fill=cream)

    # Product
    _text(draw, (w // 2, h * 2 // 5), product, _font(48), fill=brown)

    # Decorative line
    draw.rectangle([w//4, h//2-1, 3*w//4, h//2+1], fill=brown)

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 5), f"قیمت: {price} تومان", _font(34), fill=dark_red)

    # Discount in circle
    if discount:
        cx, cy = w * 4 // 5, h * 2 // 5
        draw.ellipse([cx-55, cy-55, cx+55, cy+55], fill=dark_red)
        _text(draw, (cx, cy - 10), discount, _font(30), fill=cream)
        _text(draw, (cx, cy + 20), "OFF", _font(18), fill=cream)

    # CTA
    cta = subtitle or "سفارش — پیام در دایرکت ✉"
    _text(draw, (w // 2, h * 4 // 5), cta, _font(24, bold=False), fill=brown)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 10: Flash Sale ═══════════

def poster_flash(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Urgent flash sale poster with high energy."""
    w, h = size

    # Bold yellow/black
    img = Image.new("RGB", (w, h), (255, 215, 0))
    draw = ImageDraw.Draw(img)

    black = (0, 0, 0)
    red = (220, 20, 60)

    # Diagonal stripes (warning pattern)
    for i in range(-h, w + h, 40):
        draw.line([(i, 0), (i + h, h)], fill=(255, 200, 0), width=20)

    # Central black box
    pad = 60
    draw.rounded_rectangle(
        [pad, h//5, w-pad, h*4//5],
        radius=30, fill=black,
    )

    # Flash sale header
    _text(draw, (w // 2, h // 4), "⚡ فروش فوری ⚡", _font(42), fill=(255, 215, 0))

    # Product
    _text(draw, (w // 2, h * 2 // 5 + 10), product, _font(46), fill="white")

    # Discount — BIG
    if discount:
        _text(draw, (w // 2, h // 2 + 30), discount, _font(72), fill=red)
        _text(draw, (w // 2, h // 2 + 80), "تخفیف", _font(28), fill=(255, 215, 0))

    # Price
    if price:
        _text(draw, (w // 2, h * 3 // 4 - 20), f"💰 {price} تومان", _font(32), fill="white")

    # Bottom urgency bar
    draw.rectangle([0, h - 70, w, h], fill=red)
    cta = subtitle or "⏰ فقط تا ۲۴ ساعت آینده!"
    _text(draw, (w // 2, h - 35), cta, _font(26), fill="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 11: Instagram Carousel Cover ═══════════

def poster_carousel(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Instagram carousel cover slide — swipe indicator."""
    w, h = size

    # Clean gradient
    img = _gradient(w, h, (30, 30, 60), (60, 30, 80))
    draw = ImageDraw.Draw(img)

    accent = (255, 165, 0)

    # Slide number indicator
    dot_y = h - 60
    for i in range(5):
        cx = w // 2 + (i - 2) * 30
        fill = accent if i == 0 else (100, 100, 120)
        draw.ellipse([cx-6, dot_y-6, cx+6, dot_y+6], fill=fill)

    # Content
    _text(draw, (w // 2, h // 4), "👆 بکشید", _font(24, bold=False), fill=(180, 180, 200))
    _text(draw, (w // 2, h * 2 // 5), product, _font(50), fill="white")

    # Subtitle / description
    desc = subtitle or "۵ نکته کلیدی"
    _text(draw, (w // 2, h // 2 + 20), desc, _font(30), fill=accent)

    # Swipe arrow
    _text(draw, (w - 60, h // 2), "➡️", _font(40), fill="white")

    # Brand watermark area
    if price:
        _text(draw, (w // 2, h * 3 // 4), price, _font(22, bold=False), fill=(150, 150, 170))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Template 12: Testimonial/Review ═══════════

def poster_testimonial(
    product: str,
    price: str = "",
    discount: str = "",
    subtitle: str = "",
    size: tuple[int, int] = (1080, 1080),
) -> bytes:
    """Customer review/testimonial poster."""
    w, h = size

    # Soft gradient
    img = _gradient(w, h, (240, 240, 250), (220, 225, 240))
    draw = ImageDraw.Draw(img)

    dark = (30, 30, 50)
    accent = (99, 102, 241)

    # Giant quotation mark
    _text(draw, (w // 4, h // 5), "❝", _font(80), fill=(200, 200, 220))

    # Review text (product field used as review text)
    _text(draw, (w // 2, h * 2 // 5), product, _font(36), fill=dark)

    # Stars
    _text(draw, (w // 2, h // 2 + 30), "⭐⭐⭐⭐⭐", _font(32), fill=accent)

    # Reviewer name
    reviewer = subtitle or "مشتری راضی"
    _text(draw, (w // 2, h * 3 // 5 + 20), f"— {reviewer}", _font(24, bold=False), fill=(120, 120, 140))

    # Divider
    draw.rectangle([w//3, h*3//4-1, 2*w//3, h*3//4+1], fill=accent)

    # Brand/product
    if price:
        _text(draw, (w // 2, h * 4 // 5), price, _font(22, bold=False), fill=(100, 100, 120))

    # Closing quote
    _text(draw, (3 * w // 4, h * 3 // 5 - 20), "❞", _font(60), fill=(200, 200, 220))

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ═══════════ Update TEMPLATES dict ═══════════

TEMPLATES.update({
    "luxury": poster_luxury,
    "neon": poster_neon,
    "nature": poster_nature,
    "gradient": poster_gradient,
    "vintage": poster_vintage,
    "flash": poster_flash,
    "carousel": poster_carousel,
    "testimonial": poster_testimonial,
})


