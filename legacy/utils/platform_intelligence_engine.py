
from __future__ import annotations
"""
tg_bot/utils/platform_intelligence_engine.py — Marketing Agent TITAN (L9)
═════════════════════════════════════════════════════════════════════════════
Platform monitoring, opportunity discovery, and auto-listing engine.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────┐
   │             PLATFORM INTELLIGENCE ENGINE                 │
   ├──────────┬──────────┬──────────┬──────────┬─────────────┤
   │ Monitor  │ Discover │ Events   │ AutoList │ Rank        │
   ├──────────┼──────────┼──────────┼──────────┼─────────────┤
   │ Active   │ New EU   │ Xmas     │ Generate │ ROI/Traffic │
   │ Platform │ Market   │ Markets  │ Optimise │ Visibility  │
   │ Status   │ places   │ Craft    │ Publish  │ Recommend   │
   │ Perf     │ Scout    │ Fairs    │ Update   │ Priority    │
   │ Alert    │ Rank     │ Exhibit  │ Sync     │ Report      │
   └──────────┴──────────┴──────────┴──────────┴─────────────┘

Manages 18+ platforms:
  Active (11): Etsy, Tori.fi, Instagram, Facebook MP, Pinterest,
               Amazon Handmade, Shopify, WooCommerce, TikTok Shop,
               Huuto.net, Tradera
  Registering (7): Depop, Vinted, Folksy, Kasuwa, Afound, Madeit, NOTHS

Reuses
──────
  • platform_publisher.py — actual publishing to platforms
  • web_search.py — discovering new platforms & events
  • seo_engine.py — listing optimisation
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


# ── Existing modules ──
try:
    from arki_project.utils.platform_publisher import PlatformPublisher
    _PUBLISHER_AVAILABLE = True
except ImportError:
    _PUBLISHER_AVAILABLE = False

try:
    from arki_project.utils.web_search import WebSearchEngine
    _WEB_SEARCH_AVAILABLE = True
except ImportError:
    _WEB_SEARCH_AVAILABLE = False

try:
    from arki_project.utils.seo_engine import SEOEngine
    _SEO_AVAILABLE = True
except ImportError:
    _SEO_AVAILABLE = False

# ── OMEGA modules ──
try:
    from arki_project.utils.social_intel_engine import SocialIntelEngine
    _SOCIAL_INTEL_AVAILABLE = True
except ImportError:
    _SOCIAL_INTEL_AVAILABLE = False

try:
    from arki_project.utils.competitor_radar_engine import CompetitorRadarEngine
    _COMPETITOR_RADAR_AVAILABLE = True
except ImportError:
    _COMPETITOR_RADAR_AVAILABLE = False

try:
    from arki_project.utils.content_forge_engine import ContentForgeEngine, ContentLanguage
    _CONTENT_FORGE_AVAILABLE = True
except ImportError:
    _CONTENT_FORGE_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class PlatformStatus:
    """Health status of a monitored platform."""
    platform_key: str = ""
    name: str = ""
    status: str = "unknown"  # healthy, warning, error, maintenance
    active_listings: int = 0
    total_views: int = 0
    total_sales: int = 0
    total_revenue: float = 0.0
    last_checked: Optional[datetime] = None
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform_key,
            "name": self.name,
            "status": self.status,
            "active_listings": self.active_listings,
            "total_views": self.total_views,
            "total_sales": self.total_sales,
            "total_revenue": round(self.total_revenue, 2),
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "issues": self.issues,
        }


@dataclass
class DiscoveryResult:
    """Result from platform/event discovery."""
    opportunities_found: int = 0
    opportunities_new: int = 0
    platforms_checked: int = 0
    events_found: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunities_found": self.opportunities_found,
            "opportunities_new": self.opportunities_new,
            "platforms_checked": self.platforms_checked,
            "events_found": self.events_found,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 1),
        }


# ═══════════════════════════════════════════════════════════
# Platform Intelligence Engine
# ═══════════════════════════════════════════════════════════

class PlatformIntelligenceEngine:
    """
    Platform monitoring, discovery, and auto-listing engine.

    Provides:
    - Health monitoring for 18+ active platforms
    - New EU marketplace discovery
    - Exhibition / Christmas market / craft fair finder
    - Auto-listing generation optimised per platform
    - Platform ROI ranking and recommendations
    """

    def __init__(
        self,
        *,
        platform_registry: Optional[Dict[str, Dict]] = None,
        scan_interval_hours: int = 168,
        exhibition_scan_hours: int = 72,
    ) -> None:
        self._registry = platform_registry or {}
        self._scan_interval = scan_interval_hours
        self._exhibition_scan_interval = exhibition_scan_hours
        self._last_scan: Dict[str, float] = {}
        self._web_search = WebSearchEngine() if _WEB_SEARCH_AVAILABLE else None
        self._publisher = PlatformPublisher() if _PUBLISHER_AVAILABLE else None
        self._seo = SEOEngine() if _SEO_AVAILABLE else None
        # OMEGA engines
        self._social_intel = SocialIntelEngine() if _SOCIAL_INTEL_AVAILABLE else None
        self._competitor_radar = CompetitorRadarEngine() if _COMPETITOR_RADAR_AVAILABLE else None
        self._content_forge = ContentForgeEngine() if _CONTENT_FORGE_AVAILABLE else None

    # ── Platform Monitoring ──────────────────────────────

    async def check_all_platforms(
        self,
        *,
        data_bridge=None,
    ) -> List[PlatformStatus]:
        """
        Check health and performance of all active platforms.
        """
        statuses = []

        for key, info in self._registry.items():
            if info.get("status") != "active":
                continue

            status = PlatformStatus(
                platform_key=key,
                name=info.get("name", key),
                last_checked=datetime.now(timezone.utc),
            )

            try:
                # Get listing stats from data bridge
                if data_bridge:
                    listings = await data_bridge.get_listings(
                        platform_key=key,
                        status="published",
                    )
                    status.active_listings = len(listings)
                    status.total_views = sum(l.get("views", 0) for l in listings)
                    status.total_sales = sum(l.get("sales", 0) for l in listings)
                    status.total_revenue = sum(l.get("revenue_eur", 0) for l in listings)

                    if status.active_listings == 0:
                        status.status = "warning"
                        status.issues.append("No active listings")
                    else:
                        status.status = "healthy"

                else:
                    status.status = "unknown"

            except Exception as exc:
                status.status = "error"
                status.issues.append(str(exc))

            statuses.append(status)

        return statuses

    async def get_platform_ranking(
        self,
        *,
        data_bridge=None,
    ) -> List[Dict[str, Any]]:
        """
        Rank platforms by ROI and performance.

        Returns platforms sorted by revenue-per-listing, then total revenue.
        """
        statuses = await self.check_all_platforms(data_bridge=data_bridge)
        ranked = []

        for s in statuses:
            revenue_per_listing = (
                s.total_revenue / max(s.active_listings, 1)
                if s.active_listings > 0 else 0.0
            )
            views_per_listing = (
                s.total_views / max(s.active_listings, 1)
                if s.active_listings > 0 else 0.0
            )

            ranked.append({
                **s.to_dict(),
                "revenue_per_listing": round(revenue_per_listing, 2),
                "views_per_listing": round(views_per_listing, 1),
                "roi_score": round(revenue_per_listing * 10 + views_per_listing * 0.1, 1),
            })

        ranked.sort(key=lambda x: x["roi_score"], reverse=True)
        return ranked

    # ── Platform Discovery ───────────────────────────────

    async def discover_new_platforms(
        self,
        *,
        regions: Optional[List[str]] = None,
        data_bridge=None,
    ) -> DiscoveryResult:
        """
        Discover new EU marketplaces for handmade / artisan products.
        """
        start = time.monotonic()
        result = DiscoveryResult()

        if not self._web_search:
            result.errors.append("WebSearchEngine not available")
            return result

        target_regions = regions or ["Europe", "EU", "Nordic", "Finland", "Germany", "UK"]

        queries = [
            "new handmade marketplace Europe 2024 2025",
            "artisan products platform EU marketplace",
            "sell handmade candles online Europe marketplace",
            "best platforms for handmade home decor EU",
            "new craft marketplace Nordic countries",
            "handmade marketplace alternatives to Etsy Europe",
            "online marketplace for artisans Finland Germany",
        ]

        for region in target_regions[:3]:
            queries.append(f"handmade marketplace {region} new")

        known_platforms = set(self._registry.keys())

        for query in queries:
            try:
                search_results = await self._web_search.search(query, max_results=20)
                result.platforms_checked += 1

                for sr in search_results:
                    title = sr.get("title", "") if isinstance(sr, dict) else getattr(sr, "title", "")
                    url = sr.get("url", "") if isinstance(sr, dict) else getattr(sr, "url", "")
                    snippet = sr.get("snippet", "") if isinstance(sr, dict) else getattr(sr, "snippet", "")

                    # Check if this is a new platform
                    if self._is_potential_platform(title, url, snippet, known_platforms):
                        result.opportunities_found += 1

                        if data_bridge:
                            opp_id = await data_bridge.create_opportunity({
                                "opportunity_type": "online_platform",
                                "name": title[:256],
                                "description": snippet[:500],
                                "url": url,
                                "country": self._guess_country_from_url(url),
                                "relevance_score": self._score_platform_relevance(title, snippet),
                                "source": "platform_discovery",
                            })
                            if opp_id:
                                result.opportunities_new += 1

                await asyncio.sleep(2.0)

            except Exception as exc:
                result.errors.append(f"Search '{query[:40]}': {exc}")

        result.duration_seconds = time.monotonic() - start
        return result

    async def discover_events(
        self,
        *,
        regions: Optional[List[str]] = None,
        data_bridge=None,
    ) -> DiscoveryResult:
        """
        Discover exhibitions, Christmas markets, and craft fairs.
        """
        start = time.monotonic()
        result = DiscoveryResult()

        if not self._web_search:
            result.errors.append("WebSearchEngine not available")
            return result

        target_regions = regions or ["Finland", "Sweden", "Germany", "Netherlands", "UK"]

        now = datetime.now(timezone.utc)
        year = now.year
        month_names = {
            10: "October", 11: "November", 12: "December",
            1: "January", 2: "February",
        }
        current_month = month_names.get(now.month, "")

        event_queries = []
        for region in target_regions:
            event_queries.extend([
                f"Christmas market {region} {year} vendor application handmade",
                f"craft fair {region} {year} artisan handmade",
                f"design market {region} {year} apply",
                f"handmade exhibition {region} {year}",
            ])

            if now.month >= 6:
                event_queries.append(f"joulumarkkinat {year} myyjä hakemus" if region == "Finland" else "")
                event_queries.append(f"Weihnachtsmarkt {year} Aussteller" if region == "Germany" else "")

        event_queries = [q for q in event_queries if q]

        for query in event_queries:
            try:
                search_results = await self._web_search.search(query, max_results=15)
                result.platforms_checked += 1

                for sr in search_results:
                    title = sr.get("title", "") if isinstance(sr, dict) else getattr(sr, "title", "")
                    url = sr.get("url", "") if isinstance(sr, dict) else getattr(sr, "url", "")
                    snippet = sr.get("snippet", "") if isinstance(sr, dict) else getattr(sr, "snippet", "")

                    if self._is_potential_event(title, snippet):
                        result.events_found += 1

                        if data_bridge:
                            opp_type = self._classify_event(title, snippet)
                            opp_id = await data_bridge.create_opportunity({
                                "opportunity_type": opp_type,
                                "name": title[:256],
                                "description": snippet[:500],
                                "url": url,
                                "country": self._extract_region(query),
                                "relevance_score": self._score_event_relevance(title, snippet),
                                "source": "event_discovery",
                            })
                            if opp_id:
                                result.opportunities_new += 1

                await asyncio.sleep(2.0)

            except Exception as exc:
                result.errors.append(f"Event search '{query[:40]}': {exc}")

        result.opportunities_found = result.events_found
        result.duration_seconds = time.monotonic() - start
        return result

    # ── Auto-Listing Generation ──────────────────────────

    async def generate_listing(
        self,
        *,
        product: Dict[str, Any],
        platform_key: str,
        language: str = "en",
        ai_client=None,
        data_bridge=None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an optimised listing for a specific platform.

        Takes product data and generates platform-specific title,
        description, tags, and pricing.
        """
        platform_info = self._registry.get(platform_key)
        if not platform_info:
            logger.warning("Unknown platform: %s", platform_key)
            return None

        platform_name = platform_info.get("name", platform_key)

        # SEO-optimise if engine available
        seo_tags = []
        if self._seo:
            try:
                seo_result = await self._seo.optimize(
                    title=product.get("name", ""),
                    description=product.get("description", ""),
                    category="home decor candles handmade",
                )
                seo_tags = seo_result.get("tags", []) if isinstance(seo_result, dict) else []
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        # Generate content
        if ai_client:
            try:
                listing_content = await self._generate_listing_with_ai(
                    product=product,
                    platform_name=platform_name,
                    platform_type=platform_info.get("type", "marketplace"),
                    language=language,
                    ai_client=ai_client,
                )
            except Exception as exc:
                logger.warning("AI listing gen failed: %s", exc)
                listing_content = self._generate_template_listing(product, platform_name, language)
        else:
            listing_content = self._generate_template_listing(product, platform_name, language)

        # Merge SEO tags
        tags = list(set(listing_content.get("tags", []) + seo_tags))

        listing_data = {
            "platform_key": platform_key,
            "product_name": product.get("name", ""),
            "title": listing_content.get("title", product.get("name", "")),
            "description": listing_content.get("description", ""),
            "tags": tags[:15],  # Most platforms limit tags
            "price_eur": product.get("price", 0),
            "currency": "EUR",
            "images": product.get("images", []),
            "language": language,
        }

        # Store if data bridge available
        if data_bridge:
            listing_id = await data_bridge.create_listing(listing_data)
            if listing_id:
                listing_data["id"] = listing_id

        return listing_data

    async def _generate_listing_with_ai(
        self,
        *,
        product: Dict[str, Any],
        platform_name: str,
        platform_type: str,
        language: str,
        ai_client,
    ) -> Dict[str, Any]:
        """Generate platform-optimised listing content with AI."""
        prompt = f"""Generate a product listing for {platform_name} ({platform_type}).

PRODUCT:
- Name: {product.get('name', 'Handmade Concrete Candle')}
- Description: {product.get('description', '')}
- Price: €{product.get('price', 25)}
- Material: {product.get('material', 'Concrete / Stone')}
- Origin: Handmade in Finland

PLATFORM: {platform_name}
LANGUAGE: {language}

Generate:
1. Optimised title (max 140 chars, include keywords)
2. Full description (300-500 words, engaging, SEO-friendly)
3. 13 relevant tags/keywords

Return as JSON: {{"title": "...", "description": "...", "tags": [...]}}"""

        response = await ai_client.generate(prompt)
        text = response.get("text", str(response)) if isinstance(response, dict) else str(response)

        try:
            # Try to parse JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        return {
            "title": product.get("name", "Handmade Concrete Candle"),
            "description": text[:2000],
            "tags": ["handmade", "concrete candle", "scandinavian", "finnish", "home decor"],
        }

    @staticmethod
    def _generate_template_listing(
        product: Dict[str, Any],
        platform_name: str,
        language: str,
    ) -> Dict[str, Any]:
        """Generate template-based listing (fallback)."""
        name = product.get("name", "Handmade Concrete Candle")
        return {
            "title": f"{name} — Handmade in Finland | ArkiObjects",
            "description": (
                f"{name} by ArkiObjects.\n\n"
                f"Handcrafted with care in our Pieksämäki, Finland studio. "
                f"Each piece is unique, made from high-quality concrete "
                f"with a minimalist Scandinavian aesthetic.\n\n"
                f"• Material: Premium concrete\n"
                f"• Style: Minimalist Scandinavian\n"
                f"• Origin: Handmade in Finland\n"
                f"• Makes a perfect gift\n\n"
                f"Ships from Finland. EU shipping available."
            ),
            "tags": [
                "handmade", "concrete candle", "scandinavian design",
                "finnish handmade", "home decor", "minimalist",
                "tealight holder", "artisan", "gift idea",
                "candle holder", "nordic design", "ArkiObjects",
            ],
        }

    # ── Helper Methods ───────────────────────────────────

    def _is_potential_platform(
        self,
        title: str,
        url: str,
        snippet: str,
        known: Set[str],
    ) -> bool:
        """Check if a search result looks like a marketplace platform."""
        combined = f"{title} {snippet}".lower()
        platform_signals = [
            "marketplace", "sell handmade", "artisan platform",
            "online shop", "craft marketplace", "sell online",
            "vendor registration", "seller account",
        ]
        has_signal = any(s in combined for s in platform_signals)

        # Exclude known platforms and non-platform sites
        exclude_domains = [
            "youtube.com", "reddit.com", "quora.com",
            "medium.com", "blog", "wikipedia",
        ]
        is_excluded = any(d in url.lower() for d in exclude_domains)

        return has_signal and not is_excluded

    def _is_potential_event(self, title: str, snippet: str) -> bool:
        """Check if a result looks like an event/market."""
        combined = f"{title} {snippet}".lower()
        event_signals = [
            "christmas market", "craft fair", "design market",
            "exhibition", "artisan fair", "handmade fair",
            "joulumarkkinat", "weihnachtsmarkt", "julmarknad",
            "vendor application", "stall booking", "exhibitor",
        ]
        return any(s in combined for s in event_signals)

    @staticmethod
    def _classify_event(title: str, snippet: str) -> str:
        """Classify event type."""
        combined = f"{title} {snippet}".lower()
        if any(k in combined for k in ["christmas", "joulu", "weihnacht", "jul"]):
            return "christmas_market"
        if any(k in combined for k in ["exhibition", "expo", "näyttely"]):
            return "exhibition"
        if any(k in combined for k in ["popup", "pop-up", "pop up"]):
            return "popup"
        return "craft_fair"

    @staticmethod
    def _extract_region(query: str) -> str:
        """Extract region from a search query."""
        regions = ["Finland", "Sweden", "Germany", "Netherlands", "UK", "France", "Norway", "Denmark"]
        for r in regions:
            if r.lower() in query.lower():
                return r
        return "Europe"

    @staticmethod
    def _guess_country_from_url(url: str) -> str:
        """Guess country from URL TLD."""
        tld_map = {
            ".fi": "Finland", ".se": "Sweden", ".de": "Germany",
            ".nl": "Netherlands", ".uk": "UK", ".fr": "France",
            ".no": "Norway", ".dk": "Denmark", ".au": "Australia",
        }
        url_lower = url.lower()
        for tld, country in tld_map.items():
            if tld in url_lower:
                return country
        return "International"

    @staticmethod
    def _score_platform_relevance(title: str, snippet: str) -> float:
        """Score how relevant a discovered platform is (0–100)."""
        score = 30.0
        combined = f"{title} {snippet}".lower()

        bonus_terms = {
            "handmade": 15, "artisan": 15, "craft": 10,
            "candle": 10, "home decor": 10, "europe": 5,
            "nordic": 5, "finland": 5, "free": 3,
        }
        for term, pts in bonus_terms.items():
            if term in combined:
                score += pts

        return min(score, 100.0)

    @staticmethod
    def _score_event_relevance(title: str, snippet: str) -> float:
        """Score how relevant an event is (0–100)."""
        score = 30.0
        combined = f"{title} {snippet}".lower()

        bonus_terms = {
            "handmade": 15, "artisan": 15, "craft": 10,
            "christmas": 10, "design": 10, "candle": 10,
            "nordic": 5, "finland": 8, "2025": 5, "2026": 5,
        }
        for term, pts in bonus_terms.items():
            if term in combined:
                score += pts

        return min(score, 100.0)

    # ── OMEGA: Social Intel Integration ──────────────────

    async def get_social_intel_report(
        self, focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get full social intelligence via OMEGA SocialIntelEngine."""
        if not self._social_intel:
            return {"error": "SocialIntelEngine not available"}
        try:
            report = await self._social_intel.full_social_intel(focus=focus)
            return report.to_dict()
        except Exception as exc:
            logger.warning("Social intel failed: %s", exc)
            return {"error": str(exc)}

    async def get_hashtag_strategy(
        self, content_type: str = "product_photo",
    ) -> Dict[str, Any]:
        """Get optimized hashtag strategy via OMEGA SocialIntelEngine."""
        if not self._social_intel:
            return {"error": "SocialIntelEngine not available"}
        return self._social_intel.get_hashtag_strategy(content_type)

    async def get_influencer_list(
        self, niche: Optional[str] = None, limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """Discover influencers via OMEGA SocialIntelEngine."""
        if not self._social_intel:
            return []
        try:
            influencers = await self._social_intel.discover_influencers(
                niche_override=niche, limit=limit,
            )
            return [i.to_dict() for i in influencers]
        except Exception as exc:
            logger.warning("Influencer discovery failed: %s", exc)
            return []

    async def get_community_list(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Find communities via OMEGA SocialIntelEngine."""
        if not self._social_intel:
            return []
        try:
            communities = await self._social_intel.find_communities(limit=limit)
            return [c.to_dict() for c in communities]
        except Exception as exc:
            logger.warning("Community discovery failed: %s", exc)
            return []

    # ── OMEGA: Competitor Radar Integration ───────────────

    async def run_competitor_scan(self) -> Dict[str, Any]:
        """Run full competitor scan via OMEGA CompetitorRadarEngine."""
        if not self._competitor_radar:
            return {"error": "CompetitorRadarEngine not available"}
        try:
            report = await self._competitor_radar.full_scan()
            return report.to_dict()
        except Exception as exc:
            logger.warning("Competitor scan failed: %s", exc)
            return {"error": str(exc)}

    async def get_competitor_swot(self, competitor_name: str) -> Optional[Dict[str, Any]]:
        """Generate SWOT for a competitor via OMEGA."""
        if not self._competitor_radar:
            return None
        swot = self._competitor_radar.generate_swot(competitor_name)
        return swot.to_dict() if swot else None

    async def track_competitor_prices(
        self, competitor_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Monitor competitor prices via OMEGA."""
        if not self._competitor_radar:
            return []
        try:
            prices = await self._competitor_radar.monitor_prices(competitor_name)
            return [p.to_dict() for p in prices]
        except Exception as exc:
            logger.warning("Price monitoring failed: %s", exc)
            return []

    # ── OMEGA: Content Forge Integration ──────────────────

    async def generate_platform_listing(
        self,
        product: Dict[str, Any],
        platform: str = "etsy",
        language: str = "en",
    ) -> Dict[str, Any]:
        """Generate an optimized product listing via OMEGA ContentForge."""
        if not self._content_forge:
            return {"error": "ContentForgeEngine not available"}
        try:
            lang_map = {"en": ContentLanguage.EN, "fi": ContentLanguage.FI, "sv": ContentLanguage.SV}
            forge_lang = lang_map.get(language, ContentLanguage.EN)
            piece = await self._content_forge.generate_product_description(
                product, platform=platform, language=forge_lang,
            )
            return piece.to_dict()
        except Exception as exc:
            logger.warning("Listing generation failed: %s", exc)
            return {"error": str(exc)}

    def get_stats(self) -> Dict[str, Any]:
        """Get platform intelligence stats."""
        active = sum(1 for v in self._registry.values() if v.get("status") == "active")
        registering = sum(1 for v in self._registry.values() if v.get("status") == "registering")
        return {
            "total_platforms": len(self._registry),
            "active_platforms": active,
            "registering_platforms": registering,
            "publisher_available": _PUBLISHER_AVAILABLE,
            "seo_available": _SEO_AVAILABLE,
            "web_search_available": _WEB_SEARCH_AVAILABLE,
            "omega_social_intel": _SOCIAL_INTEL_AVAILABLE,
            "omega_competitor_radar": _COMPETITOR_RADAR_AVAILABLE,
            "omega_content_forge": _CONTENT_FORGE_AVAILABLE,
        }


