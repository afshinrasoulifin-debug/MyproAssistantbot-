
from __future__ import annotations
"""
tg_bot/config_marketing.py — Marketing Agent TITAN Configuration
═══════════════════════════════════════════════════════════════════
Centralised settings for the autonomous marketing intelligence system.

All values load from environment variables with sensible defaults.
Import ``MarketingSettings`` and call ``load_marketing_settings()`` once
at boot; the singleton is then available everywhere via ``get_mkt_settings()``.
"""


import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional



# ═══════════════════════════════════════════════════════════
# Brand & Product Defaults
# ═══════════════════════════════════════════════════════════

DEFAULT_BRAND = {
    "name": "ArkiObjects",
    "tagline": "Handmade Concrete & Stone Candles",
    "style": "Minimalist Scandinavian",
    "location": "Pieksämäki, Finland",
    "languages": ["en", "fi"],
    "price_range_eur": (10, 50),
    "products": [
        "Concrete candles",
        "Tealight holders",
        "Stone decorative accessories",
        "Handmade home décor",
    ],
}


# ═══════════════════════════════════════════════════════════
# Target Markets
# ═══════════════════════════════════════════════════════════

DEFAULT_TARGET_MARKETS = [
    {"region": "Finland", "priority": 1, "languages": ["fi", "en"], "timezone": "Europe/Helsinki"},
    {"region": "Sweden", "priority": 2, "languages": ["sv", "en"], "timezone": "Europe/Stockholm"},
    {"region": "Norway", "priority": 3, "languages": ["no", "en"], "timezone": "Europe/Oslo"},
    {"region": "Denmark", "priority": 4, "languages": ["da", "en"], "timezone": "Europe/Copenhagen"},
    {"region": "Germany", "priority": 5, "languages": ["de", "en"], "timezone": "Europe/Berlin"},
    {"region": "Netherlands", "priority": 6, "languages": ["nl", "en"], "timezone": "Europe/Amsterdam"},
    {"region": "France", "priority": 7, "languages": ["fr", "en"], "timezone": "Europe/Paris"},
    {"region": "United Kingdom", "priority": 8, "languages": ["en"], "timezone": "Europe/London"},
    {"region": "United States", "priority": 9, "languages": ["en"], "timezone": "America/New_York"},
    {"region": "Canada", "priority": 10, "languages": ["en", "fr"], "timezone": "America/Toronto"},
    {"region": "Australia", "priority": 11, "languages": ["en"], "timezone": "Australia/Sydney"},
]


# ═══════════════════════════════════════════════════════════
# B2B Target Categories
# ═══════════════════════════════════════════════════════════

B2B_CATEGORIES = [
    {
        "id": "hotels",
        "name_en": "Hotels & Accommodation",
        "name_fi": "Hotellit ja majoitus",
        "search_terms": ["hotel", "boutique hotel", "bed and breakfast", "resort", "lodge"],
        "decision_makers": ["General Manager", "Interior Designer", "Purchasing Manager"],
    },
    {
        "id": "restaurants",
        "name_en": "Restaurants & Cafés",
        "name_fi": "Ravintolat ja kahvilat",
        "search_terms": ["restaurant", "café", "bistro", "fine dining", "wine bar"],
        "decision_makers": ["Owner", "Manager", "Interior Designer"],
    },
    {
        "id": "spas",
        "name_en": "Spas & Wellness",
        "name_fi": "Kylpylät ja hyvinvointi",
        "search_terms": ["spa", "wellness center", "yoga studio", "beauty salon", "meditation center"],
        "decision_makers": ["Spa Manager", "Owner", "Wellness Director"],
    },
    {
        "id": "galleries",
        "name_en": "Galleries & Art Spaces",
        "name_fi": "Galleriat ja taidetilat",
        "search_terms": ["art gallery", "design shop", "concept store", "artisan market"],
        "decision_makers": ["Gallery Owner", "Curator", "Buyer"],
    },
    {
        "id": "events",
        "name_en": "Event & Wedding Planning",
        "name_fi": "Tapahtumat ja hääsuunnittelu",
        "search_terms": ["wedding planner", "event planner", "party organizer", "bridal shop"],
        "decision_makers": ["Wedding Planner", "Event Coordinator", "Owner"],
    },
    {
        "id": "interior",
        "name_en": "Interior Design & Décor",
        "name_fi": "Sisustussuunnittelu ja sisustus",
        "search_terms": ["interior design", "home décor shop", "furniture store", "showroom"],
        "decision_makers": ["Interior Designer", "Store Manager", "Buyer"],
    },
    {
        "id": "corporate",
        "name_en": "Corporate & Offices",
        "name_fi": "Yritykset ja toimistot",
        "search_terms": ["co-working space", "startup office", "corporate gifting"],
        "decision_makers": ["Office Manager", "HR Manager", "CEO"],
    },
    {
        "id": "photography",
        "name_en": "Photography Studios",
        "name_fi": "Valokuvausstudiot",
        "search_terms": ["photography studio", "photo studio", "prop rental"],
        "decision_makers": ["Studio Owner", "Photographer"],
    },
]


# ═══════════════════════════════════════════════════════════
# Platform Registry
# ═══════════════════════════════════════════════════════════

PLATFORM_REGISTRY = {
    # Active platforms
    "etsy": {"name": "Etsy", "status": "active", "region": "global", "type": "marketplace", "url": "https://www.etsy.com"},
    "tori_fi": {"name": "Tori.fi", "status": "active", "region": "Finland", "type": "classifieds", "url": "https://www.tori.fi"},
    "instagram": {"name": "Instagram", "status": "active", "region": "global", "type": "social", "url": "https://www.instagram.com"},
    "facebook_mp": {"name": "Facebook Marketplace", "status": "active", "region": "global", "type": "marketplace", "url": "https://www.facebook.com/marketplace"},
    "pinterest": {"name": "Pinterest", "status": "active", "region": "global", "type": "social", "url": "https://www.pinterest.com"},
    "amazon_handmade": {"name": "Amazon Handmade", "status": "active", "region": "global", "type": "marketplace", "url": "https://www.amazon.com/handmade"},
    "shopify": {"name": "Shopify Store", "status": "active", "region": "global", "type": "own_store", "url": ""},
    "woocommerce": {"name": "WooCommerce", "status": "active", "region": "global", "type": "own_store", "url": ""},
    "tiktok_shop": {"name": "TikTok Shop", "status": "active", "region": "global", "type": "social", "url": "https://www.tiktok.com"},
    "huuto_net": {"name": "Huuto.net", "status": "active", "region": "Finland", "type": "auction", "url": "https://www.huuto.net"},
    "tradera": {"name": "Tradera", "status": "active", "region": "Sweden", "type": "auction", "url": "https://www.tradera.com"},
    # Registering platforms
    "depop": {"name": "Depop", "status": "registering", "region": "global", "type": "marketplace", "url": "https://www.depop.com"},
    "vinted": {"name": "Vinted", "status": "registering", "region": "Europe", "type": "marketplace", "url": "https://www.vinted.com"},
    "folksy": {"name": "Folksy", "status": "registering", "region": "UK", "type": "marketplace", "url": "https://folksy.com"},
    "dawanda_successor": {"name": "Kasuwa", "status": "registering", "region": "Germany", "type": "marketplace", "url": "https://www.kasuwa.de"},
    "afound": {"name": "Afound", "status": "registering", "region": "Nordics", "type": "marketplace", "url": "https://www.afound.com"},
    "madeit": {"name": "Madeit", "status": "registering", "region": "Australia", "type": "marketplace", "url": "https://www.madeit.com.au"},
    "not_on_hp": {"name": "Not On The High Street", "status": "registering", "region": "UK", "type": "marketplace", "url": "https://www.notonthehighstreet.com"},
}


# ═══════════════════════════════════════════════════════════
# Settings Dataclass
# ═══════════════════════════════════════════════════════════

@dataclass
class MarketingSettings:
    """Marketing Agent TITAN configuration — all tunables in one place."""

    # ── B2B Hunter ──
    hunter_max_results_per_query: int = field(
        default_factory=lambda: int(os.environ.get("MKT_HUNTER_MAX_RESULTS", "50"))
    )
    hunter_search_radius_km: int = field(
        default_factory=lambda: int(os.environ.get("MKT_HUNTER_RADIUS_KM", "100"))
    )
    hunter_cooldown_hours: float = field(
        default_factory=lambda: float(os.environ.get("MKT_HUNTER_COOLDOWN_H", "24"))
    )
    hunter_max_concurrent: int = field(
        default_factory=lambda: int(os.environ.get("MKT_HUNTER_CONCURRENT", "3"))
    )

    # ── Outreach ──
    outreach_daily_limit: int = field(
        default_factory=lambda: int(os.environ.get("MKT_OUTREACH_DAILY_LIMIT", "50"))
    )
    outreach_followup_days: List[int] = field(
        default_factory=lambda: [3, 7, 14]  # Days after initial email
    )
    outreach_from_email: str = field(
        default_factory=lambda: os.environ.get("MKT_FROM_EMAIL", "hello@arkiobjects.com")
    )
    outreach_from_name: str = field(
        default_factory=lambda: os.environ.get("MKT_FROM_NAME", "ArkiObjects Finland")
    )
    outreach_catalog_pdf_path: str = field(
        default_factory=lambda: os.environ.get("MKT_CATALOG_PDF", "assets/catalog.pdf")
    )

    # ── Platform Intelligence ──
    platform_scan_interval_hours: int = field(
        default_factory=lambda: int(os.environ.get("MKT_PLATFORM_SCAN_H", "168"))  # weekly
    )
    exhibition_scan_interval_hours: int = field(
        default_factory=lambda: int(os.environ.get("MKT_EXHIBITION_SCAN_H", "72"))  # 3 days
    )

    # ── Market Professor ──
    professor_report_hour_utc: int = field(
        default_factory=lambda: int(os.environ.get("MKT_REPORT_HOUR_UTC", "7"))
    )
    professor_competitor_limit: int = field(
        default_factory=lambda: int(os.environ.get("MKT_COMPETITOR_LIMIT", "20"))
    )

    # ── Prospect Scoring ──
    scoring_hot_threshold: float = field(
        default_factory=lambda: float(os.environ.get("MKT_SCORE_HOT", "70"))
    )
    scoring_warm_threshold: float = field(
        default_factory=lambda: float(os.environ.get("MKT_SCORE_WARM", "40"))
    )

    # ── GDPR ──
    gdpr_data_retention_days: int = field(
        default_factory=lambda: int(os.environ.get("MKT_GDPR_RETENTION_DAYS", "730"))  # 2 years
    )
    gdpr_require_consent_b2c: bool = True
    gdpr_b2b_legitimate_interest: bool = True  # B2B outreach under legitimate interest

    # ── Brand & Product (loaded from defaults, can be overridden) ──
    brand: Dict = field(default_factory=lambda: dict(DEFAULT_BRAND))
    target_markets: List[Dict] = field(default_factory=lambda: list(DEFAULT_TARGET_MARKETS))
    b2b_categories: List[Dict] = field(default_factory=lambda: list(B2B_CATEGORIES))
    platforms: Dict = field(default_factory=lambda: dict(PLATFORM_REGISTRY))


# ── Singleton ──
_settings: Optional[MarketingSettings] = None


def load_marketing_settings() -> MarketingSettings:
    """Load and cache marketing settings."""
    global _settings
    if _settings is None:
        _settings = MarketingSettings()
    return _settings


def get_mkt_settings() -> MarketingSettings:
    """Get cached marketing settings (call load_marketing_settings first)."""
    if _settings is None:
        return load_marketing_settings()
    return _settings


