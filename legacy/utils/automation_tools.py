
from __future__ import annotations
"""
tg_bot/utils/automation_tools.py
────────────────────────────────
Backend utilities for automation agents.
All free, no paid API keys required.

Agents:
  1. QR Code Generator       — qrcode library (offline)
  2. URL Shortener            — is.gd API (free)
  3. Weather                  — wttr.in (free, no key)
  4. Currency/Crypto          — exchangerate-api.com (free)
  5. RSS/News Reader          — feedparser (offline)
  6. Screenshot/Web Capture   — free API
  7. Text-to-Image (poster)   — Pillow (offline)
"""


import io
import logging
import time
from typing import Any

import aiohttp

from arki_project.utils.http_pool import get_client

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


# ═══════════ Simple TTL Cache ═══════════

class _TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""
    def __init__(self, default_ttl: int = 600) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires, value = entry
        if time.monotonic() > expires:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._data[key] = (time.monotonic() + (ttl or self._default_ttl), value)

    def clear(self) -> None:
        self._data.clear()


_cache = _TTLCache(default_ttl=600)  # 10 min default


async def _http_get_with_retry(
    url: str, *, timeout: float = 15.0, retries: int = 2, delay: float = 1.5,
) -> dict | str:
    """GET with automatic retry on transient failures (5xx, timeouts).
    Returns a dict with status, text, json keys (aiohttp compat wrapper)."""
    import aiohttp as _aiohttp

    last_exc: Exception | None = None
    client = await get_client("general")
    for attempt in range(retries + 1):
        try:
            async with client.get(url, timeout=_aiohttp.ClientTimeout(total=timeout)) as resp:
                body_text = await resp.text()
                status = resp.status
                try:
                    body_json = await resp.json(content_type=None)
                except Exception:
                    body_json = None

                # Return a simple namespace for backward compat
                result = _HttpResult(status, body_text, body_json, None)
                if status < 500 or attempt == retries:
                    return result
                last_exc = Exception(f"HTTP {status}")
        except (_aiohttp.ClientError, TimeoutError) as exc:
            last_exc = exc
        if attempt < retries:
            import asyncio as _aio
            await _aio.sleep(delay * (attempt + 1))
    raise last_exc or Exception("HTTP request failed")


class _HttpResult:
    """Thin wrapper so utility functions can use .status_code, .text, .json(), .content."""
    __slots__ = ("status_code", "status", "text", "_json", "content")

    def __init__(self, status: int, text: str, json_data: Any, content_bytes: Any) -> None:
        self.status_code = status  # compat
        self.status = status
        self.text = text
        self._json = json_data
        self.content = content_bytes or text.encode()

    def json(self) -> Any:
        if self._json is None:
            import json
            self._json = json.loads(self.text)
        return self._json


# ═══════════ 1. QR Code ═══════════

def generate_qr_code(
    data: str,
    *,
    box_size: int = 10,
    border: int = 2,
    fill_color: str = "black",
    back_color: str = "white",
) -> bytes:
    """Generate a QR code image. Returns PNG bytes."""
    import qrcode
    from qrcode.image.pil import PilImage

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img: PilImage = qr.make_image(
        fill_color=fill_color, back_color=back_color,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ═══════════ 2. URL Shortener ═══════════

async def shorten_url(url: str) -> str:
    """Shorten a URL using is.gd (free, no API key)."""
    import aiohttp as _aiohttp

    client = await get_client("general")
    api = f"https://is.gd/create.php?format=simple&url={url}"
    async with client.get(api, timeout=_aiohttp.ClientTimeout(total=10)) as resp:
        text = await resp.text()
        if resp.status == 200 and text.startswith("http"):
            return text.strip()
    # Fallback to TinyURL.
    api2 = f"https://tinyurl.com/api-create.php?url={url}"
    async with client.get(api2, timeout=_aiohttp.ClientTimeout(total=10)) as resp2:
        text2 = await resp2.text()
        if resp2.status == 200:
            return text2.strip()
    raise Exception("URL shortener failed")


# ═══════════ 3. Weather ═══════════

async def get_weather(
    city: str, *, lang: str = "fa",
) -> str:
    """Get weather using wttr.in (free, no API key). Cached for 10 minutes."""
    cache_key = f"weather:{city.lower()}:{lang}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"https://wttr.in/{city}?format=j1&lang={lang}"
    resp = await _http_get_with_retry(url, timeout=15.0)
    if resp.status_code != 200:
        raise Exception(f"Weather API error: {resp.status_code}")

    data = resp.json()
    current = data.get("current_condition", [{}])[0]
    area = data.get("nearest_area", [{}])[0]

    city_name = (
        area.get("areaName", [{}])[0].get("value", city)
        if area.get("areaName")
        else city
    )
    country = (
        area.get("country", [{}])[0].get("value", "")
        if area.get("country")
        else ""
    )

    temp_c = current.get("temp_C", "?")
    feels = current.get("FeelsLikeC", "?")
    humidity = current.get("humidity", "?")
    wind_km = current.get("windspeedKmph", "?")
    desc_fa = current.get("lang_fa", [{}])
    desc = desc_fa[0].get("value", "") if desc_fa else current.get("weatherDesc", [{}])[0].get("value", "")
    uv = current.get("uvIndex", "?")

    # 3-day forecast.
    forecast_lines = []
    for day in data.get("weather", [])[:3]:
        date = day.get("date", "")
        min_t = day.get("mintempC", "?")
        max_t = day.get("maxtempC", "?")
        forecast_lines.append(f"  📅 {date}: {min_t}°~{max_t}°C")

    text = (
        f"🌍 *{city_name}*{f', {country}' if country else ''}\n\n"
        f"🌡 دما: *{temp_c}°C* (حس واقعی: {feels}°C)\n"
        f"☁️ وضعیت: {desc}\n"
        f"💧 رطوبت: {humidity}%\n"
        f"💨 باد: {wind_km} km/h\n"
        f"☀️ UV: {uv}\n\n"
        "*پیش‌بینی ۳ روزه:*\n"
        + "\n".join(forecast_lines)
    )
    _cache.set(cache_key, text, ttl=600)  # Cache 10 min
    return text


# ═══════════ 4. Currency / Crypto ═══════════

async def get_exchange_rates(
    base: str = "USD",
) -> dict:
    """Get exchange rates from exchangerate-api (free tier: 1500/month). Cached 10 min."""
    cache_key = f"exchange:{base.upper()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"https://open.er-api.com/v6/latest/{base.upper()}"
    resp = await _http_get_with_retry(url, timeout=10.0)
    if resp.status_code != 200:
        raise Exception(f"Exchange API error: {resp.status_code}")
    data = resp.json()
    _cache.set(cache_key, data, ttl=600)  # Cache 10 min
    return data


async def convert_currency(
    amount: float, from_cur: str, to_cur: str,
) -> str:
    """Convert between currencies."""
    data = await get_exchange_rates(from_cur)
    rates = data.get("rates", {})
    to_upper = to_cur.upper()
    if to_upper not in rates:
        raise Exception(f"ارز {to_upper} پیدا نشد")
    result = amount * rates[to_upper]
    return (
        "💱 *تبدیل ارز:*\n\n"
        f"*{amount:,.2f} {from_cur.upper()}* = *{result:,.2f} {to_upper}*\n\n"
        f"📅 {data.get('time_last_update_utc', '')[:16]}"
    )


async def get_popular_rates() -> str:
    """Get popular exchange rates for Iranians."""
    data = await get_exchange_rates("USD")
    rates = data.get("rates", {})

    pairs = [
        ("USD/IRR", rates.get("IRR", 0)),
        ("USD/EUR", rates.get("EUR", 0)),
        ("USD/GBP", rates.get("GBP", 0)),
        ("USD/TRY", rates.get("TRY", 0)),
        ("USD/AED", rates.get("AED", 0)),
        ("USD/CNY", rates.get("CNY", 0)),
    ]
    text = "💱 *نرخ ارز (پایه: USD):*\n\n"
    for name, rate in pairs:
        if rate:
            text += f"  {name}: *{rate:,.2f}*\n"
    text += f"\n📅 {data.get('time_last_update_utc', '')[:16]}"
    return text


# ═══════════ 5. RSS / News ═══════════

async def fetch_rss(
    url: str, *, max_items: int = 5,
) -> str:
    """Fetch and format RSS feed entries."""
    import feedparser

    client = await get_client("general")
    async with client.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status != 200:
            raise Exception(f"RSS fetch error: {resp.status}")
        rss_text = await resp.text()

    feed = feedparser.parse(rss_text)
    title = feed.feed.get("title", "RSS Feed")

    text = f"📰 *{title}*\n\n"
    for i, entry in enumerate(feed.entries[:max_items], 1):
        entry_title = entry.get("title", "بدون عنوان")
        link = entry.get("link", "")
        published = entry.get("published", "")[:16]
        summary = entry.get("summary", "")[:100]
        text += (
            f"*{i}.* {entry_title}\n"
            f"   🔗 {link}\n"
            f"   📅 {published}\n\n"
        )
    return text


# ═══════════ 6. Note/Memo Storage ═══════════
# (uses SQLite via the existing DB — see database/models.py)


# ═══════════ 7. Random Tools ═══════════

async def get_random_quote() -> str:
    """Get a random inspirational quote (free API)."""
    try:
        client = await get_client("general")
        async with client.get("https://api.quotable.io/random", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return f"💬 _{data['content']}_\n\n— *{data['author']}*"
    except Exception as e:
        logger.debug("Suppressed: %s", e)
    # Fallback static quotes.
    try:
        from arki_project.utils.titanium.crypto import csprng_choice
    except ImportError:
        import random as _rnd
        csprng_choice = _rnd.choice
    quotes = [
        ("هر لحظه‌ای که صرف نگرانی می‌کنی، لحظه‌ای از شادی‌ات کم می‌شود.", "رالف والدو امرسون"),
        ("بزرگ‌ترین افتخار در زندگی نیفتادن نیست، بلکه هر بار برخاستن است.", "نلسون ماندلا"),
        ("آینده متعلق به کسانی است که به زیبایی رویاهایشان ایمان دارند.", "النور روزولت"),
    ]
    q, a = csprng_choice(quotes)
    return f"💬 _{q}_\n\n— *{a}*"


async def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    import secrets
    import string

    chars = string.ascii_letters + string.digits + "!@#$%&*"
    pwd = "".join(secrets.choice(chars) for _ in range(length))
    return f"🔐 *رمز عبور امن ({length} کاراکتر):*\n\n`{pwd}`"


async def get_ip_info() -> str:
    """Get public IP information."""
    client = await get_client("general")
    async with client.get("https://ipapi.co/json/", timeout=aiohttp.ClientTimeout(total=10)) as resp:
        if resp.status != 200:
            raise Exception("IP API error")
        d = await resp.json()
    return (
        "🌐 *اطلاعات IP:*\n\n"
        f"IP: `{d.get('ip', '?')}`\n"
        f"شهر: {d.get('city', '?')}\n"
        f"کشور: {d.get('country_name', '?')}\n"
        f"ISP: {d.get('org', '?')}\n"
        f"Timezone: {d.get('timezone', '?')}"
    )


