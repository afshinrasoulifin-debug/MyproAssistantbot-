
from __future__ import annotations
"""
tg_bot/utils/titanium/header_entropy.py — L1 Header Entropy Layer v10.3.1
═════════════════════════════════════════════════════════════════════════
Generates typed decoy headers with semantic consistency.

Features:
  • 36 language profiles
  • Multi-browser Sec-Ch-Ua (Chrome, Edge, Brave, Opera)
  • User-Agent rotation (50+ real UAs)
  • Referer entropy
  • DNT and GPC headers
  • Platform-aware header sets

Ported from: TITANIUM ZKI security/header_entropy.ts
"""


from typing import Dict
from arki_project.utils.titanium.crypto import csprng_choice, csprng_int
from arki_project.utils.anti_detection import UserAgentGenerator, BrowserType, Platform

# ── Language profiles with proper q-values ────────────────────

LANG_PROFILES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fa;q=0.8",
    "fa-IR,fa;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "es-ES,es;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
    "ru-RU,ru;q=0.9,en;q=0.8",
    "ar-SA,ar;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
    "nl-NL,nl;q=0.9,en;q=0.8",
    "tr-TR,tr;q=0.9,en;q=0.8",
    "pl-PL,pl;q=0.9,en;q=0.8",
    "sv-SE,sv;q=0.9,en;q=0.8",
    "da-DK,da;q=0.9,en;q=0.8",
    "fi-FI,fi;q=0.9,en;q=0.8",
    "nb-NO,nb;q=0.9,en;q=0.8",
    "th-TH,th;q=0.9,en;q=0.8",
    "vi-VN,vi;q=0.9,en;q=0.8",
    "uk-UA,uk;q=0.9,en;q=0.8",
    "cs-CZ,cs;q=0.9,en;q=0.8",
    "ro-RO,ro;q=0.9,en;q=0.8",
    "hu-HU,hu;q=0.9,en;q=0.8",
    "el-GR,el;q=0.9,en;q=0.8",
    "id-ID,id;q=0.9,en;q=0.8",
    "ms-MY,ms;q=0.9,en;q=0.8",
    "hi-IN,hi;q=0.9,en;q=0.8",
    "bn-BD,bn;q=0.9,en;q=0.8",
    "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7,ar;q=0.6",
    "en-AU,en;q=0.9",
    "en-CA,en;q=0.9,fr;q=0.8",
    "zh-TW,zh;q=0.9,en;q=0.8",
]

# ── Sec-Ch-Ua brand strings (multi-browser) ──────────────────

SEC_CH_UA_BRANDS = [
    '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    '"Chromium";v="125", "Google Chrome";v="125", "Not-A.Brand";v="99"',
    '"Chromium";v="126", "Google Chrome";v="126", "Not-A.Brand";v="99"',
    '"Chromium";v="127", "Google Chrome";v="127", "Not-A.Brand";v="99"',
    '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
    '"Chromium";v="125", "Microsoft Edge";v="125", "Not-A.Brand";v="99"',
    '"Chromium";v="126", "Brave";v="126", "Not-A.Brand";v="99"',
    '"Chromium";v="124", "Opera";v="110", "Not-A.Brand";v="99"',
]

PLATFORMS = ['"Windows"', '"macOS"', '"Linux"', '"ChromeOS"']

# ── User-Agent rotation ──────────────────────────────────────

USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.1.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.1.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

CACHE_CONTROLS = [
    "no-cache", "max-age=0", "no-store",
    "max-age=0, no-cache", "max-age=300",
]

ACCEPTS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "application/json, text/plain, */*",
    "*/*",
]

ACCEPT_ENCODINGS = [
    "gzip, deflate, br",
    "gzip, deflate, br, zstd",
    "gzip, deflate",
]

PRIORITIES = ["u=0, i", "u=1, i", "u=0", "u=1"]

REFERERS = [
    "https://www.google.com/",
    "https://www.google.com/search?q=ai+chatbot",
    "https://duckduckgo.com/",
    "https://www.bing.com/",
    "",  # no referer (natural)
]

CONNECTION_VALUES = ["keep-alive", "Keep-Alive"]


def build_decoy_headers(browser_label: str, platform: str, version: str) -> Dict[str, str]:
    """
    Generate a set of semantically-consistent browser decoy headers.

    Every value matches what a real browser would send.
    36 language profiles × 8 browser brands × 17 UAs = massive entropy.
    """
    headers: Dict[str, str] = {}

    # Always include Accept-Language, potentially based on a more specific profile hint
    headers["Accept-Language"] = csprng_choice(LANG_PROFILES)

    # Generate User-Agent based on the provided profile
    headers["User-Agent"] = UserAgentGenerator.generate(
        browser=getattr(BrowserType, browser_label.upper(), BrowserType.CHROME),
        platform=getattr(Platform, platform.upper(), Platform.WINDOWS),
        version=version
    )

    # Ensure Sec-CH-UA headers are consistent with Chrome/Edge profiles
    if browser_label in ["chrome", "edge", "brave", "opera"]:
        # Dynamically generate Sec-CH-UA based on the profile's Chrome version
        chrome_version = version.split('.')[0] # e.g., '125'
        headers["sec-ch-ua"] = f'"Chromium";v="{chrome_version}", "Not;A=Brand";v="99"'
        headers["sec-ch-ua-mobile"] = "?0"
        headers["sec-ch-ua-platform"] = f'"{platform.capitalize()}"'
        headers["Sec-Fetch-Site"] = csprng_choice(["none", "same-origin", "cross-site"])
        headers["Sec-Fetch-Mode"] = csprng_choice(["cors", "navigate", "no-cors"])
        headers["Sec-Fetch-Dest"] = csprng_choice(["empty", "document"])

    # 90% chance: Cache-Control (almost always present)
    if csprng_int(0, 99) < 90:
        headers["Cache-Control"] = csprng_choice(CACHE_CONTROLS)

    # 80% chance: Accept (more common to send Accept header)
    if csprng_int(0, 99) < 80:
        headers["Accept"] = csprng_choice(ACCEPTS)

    # Always include encoding
    headers["Accept-Encoding"] = csprng_choice(ACCEPT_ENCODINGS)

    # 70% chance: Priority hints (more common in modern browsers)
    if csprng_int(0, 99) < 70:
        headers["Priority"] = csprng_choice(PRIORITIES)

    # 50% chance: Referer (increased probability for more human-like behavior)
    if csprng_int(0, 99) < 50:
        ref = csprng_choice(REFERERS)
        if ref:
            headers["Referer"] = ref

    # 60% chance: DNT / GPC privacy headers (increased probability)
    if csprng_int(0, 99) < 60:
        headers["DNT"] = "1"
        if csprng_int(0, 99) < 70: # Higher chance of GPC with DNT
            headers["Sec-GPC"] = "1"

    # Always: Connection keepalive, with a small chance of not sending it (edge case)
    if csprng_int(0, 99) < 95:
        headers["Connection"] = csprng_choice(CONNECTION_VALUES)

    return headers


