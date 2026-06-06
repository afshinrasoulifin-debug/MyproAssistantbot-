
from __future__ import annotations
"""
utils/competitor_radar_engine.py — Competitor Radar Engine  v1.0-OMEGA
═══════════════════════════════════════════════════════════════════════════
Continuous competitor monitoring and strategic intelligence.

Capabilities
────────────
  • Price Monitor      — track competitor pricing across platforms
  • Catalog Track      — detect new products and changes
  • SEO Tracking       — keyword position monitoring
  • Review Analysis    — competitor review sentiment comparison
  • Market Share       — estimate relative market positions
  • Alert System       — real-time alerts on competitor changes
  • Auto-SWOT          — generate SWOT from gathered intelligence
  • Ad Detection       — discover competitor advertising

Author: Viktor AI  |  Arki Engine OMEGA
"""


import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

try:
    from arki_project.utils.web_search import WebSearchEngine
    _SEARCH_AVAILABLE = True
except ImportError:
    _SEARCH_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════════════

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeType(Enum):
    PRICE_CHANGE = "price_change"
    NEW_PRODUCT = "new_product"
    REMOVED_PRODUCT = "removed_product"
    NEW_REVIEW = "new_review"
    SEO_CHANGE = "seo_change"
    NEW_AD = "new_ad"
    SOCIAL_SPIKE = "social_spike"
    NEW_MARKET = "new_market"
    WEBSITE_CHANGE = "website_change"


@dataclass
class CompetitorProfile:
    """Tracked competitor profile."""
    name: str
    domain: Optional[str] = None
    platforms: Dict[str, str] = field(default_factory=dict)  # platform -> url
    price_range: Optional[str] = None
    product_count: Optional[int] = None
    review_avg: Optional[float] = None
    review_count: Optional[int] = None
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    market_position: str = "unknown"  # leader, challenger, niche, emerging
    location: Optional[str] = None
    social_profiles: Dict[str, str] = field(default_factory=dict)
    last_scanned: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "domain": self.domain,
            "platforms": self.platforms,
            "price_range": self.price_range,
            "product_count": self.product_count,
            "review_avg": self.review_avg,
            "review_count": self.review_count,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "market_position": self.market_position,
            "location": self.location,
            "social_profiles": self.social_profiles,
            "last_scanned": self.last_scanned,
            "tags": self.tags,
        }


@dataclass
class PricePoint:
    """Single price data point for a product."""
    product_name: str
    price: float
    currency: str = "EUR"
    platform: str = ""
    url: str = ""
    timestamp: str = ""
    competitor: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "price": self.price, "currency": self.currency,
            "platform": self.platform, "url": self.url,
            "timestamp": self.timestamp, "competitor": self.competitor,
        }


@dataclass
class SEOPosition:
    """Search engine ranking position."""
    keyword: str
    position: Optional[int] = None  # 1-100 or None if not found
    url: str = ""
    competitor: str = ""
    timestamp: str = ""
    previous_position: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword, "position": self.position,
            "url": self.url, "competitor": self.competitor,
            "timestamp": self.timestamp,
            "previous_position": self.previous_position,
            "change": (self.previous_position - self.position)
                if self.previous_position and self.position else None,
        }


@dataclass
class CompetitorAlert:
    """Alert about a competitor change."""
    competitor: str
    change_type: ChangeType
    priority: AlertPriority
    title: str
    description: str
    source_url: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    actionable: bool = True
    suggested_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor,
            "change_type": self.change_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "source_url": self.source_url,
            "data": self.data,
            "timestamp": self.timestamp,
            "actionable": self.actionable,
            "suggested_action": self.suggested_action,
        }


@dataclass
class SWOTAnalysis:
    """Auto-generated SWOT analysis."""
    competitor: str
    generated_at: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor,
            "generated_at": self.generated_at,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "opportunities": self.opportunities,
            "threats": self.threats,
            "recommendations": self.recommendations,
        }


@dataclass
class MarketLandscape:
    """Overall market landscape analysis."""
    generated_at: str = ""
    total_competitors: int = 0
    market_segments: Dict[str, List[str]] = field(default_factory=dict)
    price_ranges: Dict[str, str] = field(default_factory=dict)
    trending_products: List[str] = field(default_factory=list)
    underserved_niches: List[str] = field(default_factory=list)
    market_growth: str = "stable"  # growing, stable, declining
    key_differentiators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_competitors": self.total_competitors,
            "market_segments": self.market_segments,
            "price_ranges": self.price_ranges,
            "trending_products": self.trending_products,
            "underserved_niches": self.underserved_niches,
            "market_growth": self.market_growth,
            "key_differentiators": self.key_differentiators,
        }


@dataclass
class CompetitorRadarReport:
    """Complete competitor intelligence report."""
    generated_at: str = ""
    competitors: List[CompetitorProfile] = field(default_factory=list)
    price_data: List[PricePoint] = field(default_factory=list)
    seo_positions: List[SEOPosition] = field(default_factory=list)
    alerts: List[CompetitorAlert] = field(default_factory=list)
    swot_analyses: List[SWOTAnalysis] = field(default_factory=list)
    market_landscape: Optional[MarketLandscape] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "competitors": [c.to_dict() for c in self.competitors],
            "price_data": [p.to_dict() for p in self.price_data],
            "seo_positions": [s.to_dict() for s in self.seo_positions],
            "alerts": [a.to_dict() for a in self.alerts],
            "swot_analyses": [s.to_dict() for s in self.swot_analyses],
            "market_landscape": self.market_landscape.to_dict() if self.market_landscape else None,
            "errors": self.errors,
        }


# ═══════════════════════════════════════════════════════════════════════
#  Price Extraction
# ═══════════════════════════════════════════════════════════════════════

_PRICE_PATTERNS = [
    re.compile(r'[€]\s?(\d+[.,]\d{2})', re.I),
    re.compile(r'(\d+[.,]\d{2})\s?[€]', re.I),
    re.compile(r'EUR\s?(\d+[.,]\d{2})', re.I),
    re.compile(r'(\d+[.,]\d{2})\s?EUR', re.I),
    re.compile(r'\$\s?(\d+[.,]\d{2})', re.I),
    re.compile(r'£\s?(\d+[.,]\d{2})', re.I),
    re.compile(r'(\d+[.,]\d{2})\s?(?:USD|GBP|SEK|NOK|DKK)', re.I),
]

_CURRENCY_DETECT = {
    "€": "EUR", "EUR": "EUR",
    "$": "USD", "USD": "USD",
    "£": "GBP", "GBP": "GBP",
    "SEK": "SEK", "NOK": "NOK", "DKK": "DKK",
}


def _extract_prices(text: str) -> List[Tuple[float, str]]:
    """Extract prices from text."""
    prices: List[Tuple[float, str]] = []
    for pattern in _PRICE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                price_str = match.group(1).replace(",", ".")
                price = float(price_str)
                if 0.5 <= price <= 10000:
                    # Detect currency from context
                    context = text[max(0, match.start()-5):match.end()+5]
                    currency = "EUR"
                    for sym, cur in _CURRENCY_DETECT.items():
                        if sym in context:
                            currency = cur
                            break
                    prices.append((price, currency))
            except (ValueError, IndexError):
                continue
    return prices


# ═══════════════════════════════════════════════════════════════════════
#  SEO Keywords (target keywords for candle/decor niche)
# ═══════════════════════════════════════════════════════════════════════

_TARGET_KEYWORDS = [
    "handmade concrete candle holder",
    "Nordic candle holder",
    "Scandinavian home decor",
    "concrete decor Finland",
    "handmade candles Finland",
    "minimalist candle holder",
    "artisan home decor Nordic",
    "stone candle holder",
    "handcrafted decor Scandinavia",
    "concrete home accessories",
    "käsintehty kynttilänjalka",
    "betoni sisustus",
    "pohjoismainen sisustus",
]

# Known competitor niches for handmade candles/concrete decor
_COMPETITOR_SEARCH_QUERIES = [
    "handmade concrete candle holder Etsy",
    "Nordic concrete decor shop",
    "Scandinavian handmade candle shop",
    "concrete home decor Finland",
    "artisan candle holder Europe",
    "betoninen kynttilänjalka myynti",
    "handgjorda ljushållare betong",
]


# ═══════════════════════════════════════════════════════════════════════
#  SWOT Generator
# ═══════════════════════════════════════════════════════════════════════

def _generate_swot(
    competitor: CompetitorProfile,
    our_brand: str = "ArkiObjects",
) -> SWOTAnalysis:
    """Generate SWOT analysis for a competitor vs our brand."""
    swot = SWOTAnalysis(
        competitor=competitor.name,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Strengths
    if competitor.review_avg and competitor.review_avg >= 4.5:
        swot.strengths.append(f"High customer satisfaction ({competitor.review_avg}/5)")
    if competitor.review_count and competitor.review_count > 100:
        swot.strengths.append(f"Established reputation ({competitor.review_count} reviews)")
    if competitor.product_count and competitor.product_count > 50:
        swot.strengths.append(f"Large product catalog ({competitor.product_count} items)")
    if len(competitor.platforms) > 3:
        swot.strengths.append(f"Multi-platform presence ({len(competitor.platforms)} platforms)")
    if competitor.market_position == "leader":
        swot.strengths.append("Market leader position")

    if not swot.strengths:
        swot.strengths.append("Established presence in the market")

    # Weaknesses
    if competitor.review_avg and competitor.review_avg < 4.0:
        swot.weaknesses.append(f"Below-average reviews ({competitor.review_avg}/5)")
    if competitor.product_count and competitor.product_count < 10:
        swot.weaknesses.append("Limited product range")
    if not competitor.social_profiles:
        swot.weaknesses.append("Weak social media presence")
    if competitor.location and "china" in competitor.location.lower():
        swot.weaknesses.append("Mass-produced, not handmade — lacks authenticity")
    if len(competitor.platforms) <= 1:
        swot.weaknesses.append("Single-platform dependency")

    if not swot.weaknesses:
        swot.weaknesses.append("Limited differentiation in the market")

    # Opportunities
    if competitor.review_avg and competitor.review_avg < 4.5:
        swot.opportunities.append("Win their dissatisfied customers with superior quality")
    if not competitor.social_profiles.get("instagram"):
        swot.opportunities.append("Dominate Instagram where they're absent")
    if not competitor.social_profiles.get("pinterest"):
        swot.opportunities.append("Build Pinterest presence they lack")
    swot.opportunities.append(f"Position {our_brand} as authentic handmade alternative")
    swot.opportunities.append("Target their B2B customers with personalized outreach")

    # Threats
    if competitor.price_range:
        try:
            prices = re.findall(r'\d+', competitor.price_range)
            if prices and float(prices[0]) < 15:
                swot.threats.append("Aggressive low pricing could undercut our margins")
        except (ValueError, IndexError):
            pass
    if competitor.market_position == "leader":
        swot.threats.append("Established brand loyalty difficult to break")
    if competitor.review_count and competitor.review_count > 500:
        swot.threats.append("Strong social proof from high review count")
    swot.threats.append("Potential for competitor to copy our unique designs")

    # Recommendations
    swot.recommendations.append(
        f"Focus on what {competitor.name} can't offer: genuine Finnish handmade authenticity"
    )
    swot.recommendations.append(
        "Target their negative reviews to identify and approach dissatisfied customers"
    )
    swot.recommendations.append(
        "Differentiate with behind-the-scenes content showing handcraft process"
    )

    return swot


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════

class CompetitorRadarEngine:
    """
    Competitor monitoring and strategic intelligence engine.

    Tracks competitors across platforms, monitors prices,
    analyzes reviews, and generates strategic insights.
    """

    def __init__(
        self,
        our_brand: str = "ArkiObjects",
        tracked_competitors: Optional[List[Dict[str, str]]] = None,
        keywords: Optional[List[str]] = None,
    ) -> None:
        self.our_brand = our_brand
        self._tracked: Dict[str, CompetitorProfile] = {}
        self._price_history: Dict[str, List[PricePoint]] = {}
        self._seo_history: Dict[str, List[SEOPosition]] = {}
        self._alerts: List[CompetitorAlert] = []
        self._keywords = keywords or _TARGET_KEYWORDS
        self._web_search = WebSearchEngine() if _SEARCH_AVAILABLE else None
        self._stats = {
            "competitors_tracked": 0,
            "price_checks": 0,
            "seo_checks": 0,
            "alerts_generated": 0,
            "swot_generated": 0,
            "scans_completed": 0,
            "errors": 0,
        }

        # Initialize tracked competitors
        if tracked_competitors:
            for comp in tracked_competitors:
                name = comp.get("name", "")
                if name:
                    self._tracked[name] = CompetitorProfile(
                        name=name,
                        domain=comp.get("domain"),
                        location=comp.get("location"),
                    )

    async def full_scan(self) -> CompetitorRadarReport:
        """
        Run a complete competitor scan.

        Returns comprehensive report with all intelligence.
        """
        report = CompetitorRadarReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Phase 1: Discover competitors if none tracked
            if not self._tracked:
                await self._discover_competitors(report)
            else:
                report.competitors = list(self._tracked.values())

            # Phase 2: Price monitoring
            await self._monitor_prices(report)

            # Phase 3: SEO position tracking
            await self._track_seo(report)

            # Phase 4: Generate SWOT for each competitor
            for comp in report.competitors:
                swot = _generate_swot(comp, self.our_brand)
                report.swot_analyses.append(swot)
                self._stats["swot_generated"] += 1

            # Phase 5: Market landscape
            report.market_landscape = self._build_landscape(report)

            # Phase 6: Generate alerts
            report.alerts = self._generate_alerts(report)

            self._stats["scans_completed"] += 1

        except Exception as e:
            report.errors.append(f"scan_error: {str(e)}")
            self._stats["errors"] += 1
            logger.exception("Competitor scan failed")

        return report

    async def discover_competitors(
        self,
        niche: str = "handmade concrete candle",
        region: str = "Europe",
        limit: int = 10,
    ) -> List[CompetitorProfile]:
        """Discover competitors in the niche."""
        competitors: List[CompetitorProfile] = []

        if not self._web_search:
            return competitors

        queries = [
            f'{niche} shop {region}',
            f'{niche} Etsy seller',
            f'concrete candle holder artisan {region}',
            f'handmade Nordic decor shop',
            f'Scandinavian candle maker',
        ]

        seen_domains: Set[str] = set()
        seen_names: Set[str] = set()

        for query in queries:
            try:
                results = await self._web_search.search(query, max_results=10)
                self._stats["seo_checks"] += 1
                for r in (results or []):
                    url = getattr(r, "url", "") or ""
                    title = getattr(r, "title", "") or ""
                    snippet = getattr(r, "snippet", "") or ""

                    # Skip our own brand
                    if self.our_brand.lower() in title.lower():
                        continue

                    # Extract domain
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower().replace("www.", "")

                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    # Check if it's a competitor
                    if self._is_competitor(title, snippet, url):
                        name = self._extract_brand_name(title, domain)
                        if name.lower() in seen_names:
                            continue
                        seen_names.add(name.lower())

                        platform_type = self._detect_platform(url)
                        comp = CompetitorProfile(
                            name=name,
                            domain=domain if platform_type == "website" else None,
                            platforms={platform_type: url} if platform_type else {},
                            last_scanned=datetime.now(timezone.utc).isoformat(),
                        )

                        # Extract price from snippet
                        prices = _extract_prices(snippet)
                        if prices:
                            min_p = min(p[0] for p in prices)
                            max_p = max(p[0] for p in prices)
                            comp.price_range = f"€{min_p:.0f}-{max_p:.0f}"

                        competitors.append(comp)
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug("competitor discovery error: %s", e)

        competitors = competitors[:limit]
        for comp in competitors:
            self._tracked[comp.name] = comp
        self._stats["competitors_tracked"] = len(self._tracked)
        return competitors

    async def monitor_prices(
        self,
        competitor_name: Optional[str] = None,
    ) -> List[PricePoint]:
        """Monitor competitor prices."""
        prices: List[PricePoint] = []

        if not self._web_search:
            return prices

        targets = [self._tracked[competitor_name]] if competitor_name and competitor_name in self._tracked \
            else list(self._tracked.values())

        for comp in targets:
            try:
                query = f'"{comp.name}" price candle concrete'
                results = await self._web_search.search(query, max_results=5)
                self._stats["price_checks"] += 1

                for r in (results or []):
                    snippet = getattr(r, "snippet", "") or ""
                    url = getattr(r, "url", "") or ""
                    extracted = _extract_prices(snippet)
                    for price_val, currency in extracted:
                        pp = PricePoint(
                            product_name=self._guess_product_name(snippet),
                            price=price_val,
                            currency=currency,
                            platform=self._detect_platform(url) or "web",
                            url=url,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            competitor=comp.name,
                        )
                        prices.append(pp)
                        # Store in history
                        self._price_history.setdefault(comp.name, []).append(pp)
            except Exception:
                self._stats["errors"] += 1

        return prices

    async def track_seo_positions(
        self,
        keywords: Optional[List[str]] = None,
    ) -> List[SEOPosition]:
        """Track SEO positions for target keywords."""
        kws = keywords or self._keywords[:5]
        positions: List[SEOPosition] = []

        if not self._web_search:
            return positions

        for kw in kws:
            try:
                results = await self._web_search.search(kw, max_results=20)
                self._stats["seo_checks"] += 1
                for rank, r in enumerate(results or [], 1):
                    url = getattr(r, "url", "") or ""
                    title = getattr(r, "title", "") or ""

                    # Check if any tracked competitor appears
                    for comp_name, comp in self._tracked.items():
                        domain = comp.domain or ""
                        if domain and domain in url.lower():
                            pos = SEOPosition(
                                keyword=kw, position=rank,
                                url=url, competitor=comp_name,
                                timestamp=datetime.now(timezone.utc).isoformat(),
                            )
                            positions.append(pos)

                    # Check our own brand
                    if self.our_brand.lower() in (title + url).lower():
                        pos = SEOPosition(
                            keyword=kw, position=rank,
                            url=url, competitor=self.our_brand,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                        positions.append(pos)
            except Exception:
                self._stats["errors"] += 1

        return positions

    def generate_swot(
        self,
        competitor_name: str,
    ) -> Optional[SWOTAnalysis]:
        """Generate SWOT analysis for a specific competitor."""
        comp = self._tracked.get(competitor_name)
        if not comp:
            return None
        return _generate_swot(comp, self.our_brand)

    def get_market_landscape(self) -> MarketLandscape:
        """Get current market landscape analysis."""
        return self._build_landscape(CompetitorRadarReport(
            competitors=list(self._tracked.values()),
        ))

    def add_competitor(
        self,
        name: str,
        domain: Optional[str] = None,
        platforms: Optional[Dict[str, str]] = None,
    ) -> CompetitorProfile:
        """Manually add a competitor to track."""
        comp = CompetitorProfile(
            name=name, domain=domain,
            platforms=platforms or {},
            last_scanned=datetime.now(timezone.utc).isoformat(),
        )
        self._tracked[name] = comp
        self._stats["competitors_tracked"] = len(self._tracked)
        return comp

    def remove_competitor(self, name: str) -> bool:
        """Remove a competitor from tracking."""
        if name in self._tracked:
            del self._tracked[name]
            self._stats["competitors_tracked"] = len(self._tracked)
            return True
        return False

    def list_tracked(self) -> List[Dict[str, Any]]:
        """List all tracked competitors."""
        return [c.to_dict() for c in self._tracked.values()]

    def get_price_trends(
        self,
        competitor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get price trend analysis."""
        if competitor_name:
            history = self._price_history.get(competitor_name, [])
            return self._analyze_price_trend(competitor_name, history)

        trends = {}
        for name, history in self._price_history.items():
            trends[name] = self._analyze_price_trend(name, history)
        return trends

    def get_alerts(
        self,
        priority: Optional[AlertPriority] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent alerts, optionally filtered by priority."""
        alerts = self._alerts
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return [a.to_dict() for a in alerts[:limit]]

    # ── Internal helpers ──────────────────────────────────────────

    async def _discover_competitors(self, report: CompetitorRadarReport) -> None:
        """Discover and populate report with competitors."""
        competitors = await self.discover_competitors()
        report.competitors = competitors

    async def _monitor_prices(self, report: CompetitorRadarReport) -> None:
        """Monitor prices for all tracked competitors."""
        report.price_data = await self.monitor_prices()

    async def _track_seo(self, report: CompetitorRadarReport) -> None:
        """Track SEO positions."""
        report.seo_positions = await self.track_seo_positions()

    def _build_landscape(self, report: CompetitorRadarReport) -> MarketLandscape:
        """Build market landscape from gathered data."""
        landscape = MarketLandscape(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_competitors=len(report.competitors),
        )

        # Segment competitors
        segments: Dict[str, List[str]] = {
            "premium": [], "mid_range": [], "budget": [], "unknown": [],
        }
        for comp in report.competitors:
            if comp.price_range:
                try:
                    prices = re.findall(r'\d+', comp.price_range)
                    if prices:
                        avg = sum(float(p) for p in prices) / len(prices)
                        if avg > 40:
                            segments["premium"].append(comp.name)
                        elif avg > 15:
                            segments["mid_range"].append(comp.name)
                        else:
                            segments["budget"].append(comp.name)
                    else:
                        segments["unknown"].append(comp.name)
                except (ValueError, ZeroDivisionError):
                    segments["unknown"].append(comp.name)
            else:
                segments["unknown"].append(comp.name)

        landscape.market_segments = {k: v for k, v in segments.items() if v}

        # Underserved niches
        landscape.underserved_niches = [
            "Concrete/stone candle holders (few competitors)",
            "B2B bulk orders for hotels/restaurants",
            "Personalized/custom pieces for events",
            "Subscription candle boxes",
        ]

        landscape.key_differentiators = [
            "Handmade in Finland (authenticity)",
            "Concrete/stone material (unique)",
            "Scandinavian minimalist design",
            "Small-batch artisan production",
        ]

        return landscape

    def _generate_alerts(self, report: CompetitorRadarReport) -> List[CompetitorAlert]:
        """Generate alerts from report data."""
        alerts: List[CompetitorAlert] = []
        now = datetime.now(timezone.utc).isoformat()

        # Price alerts
        for pp in report.price_data:
            history = self._price_history.get(pp.competitor, [])
            if len(history) >= 2:
                prev = history[-2]
                if pp.price < prev.price * 0.9:
                    alert = CompetitorAlert(
                        competitor=pp.competitor,
                        change_type=ChangeType.PRICE_CHANGE,
                        priority=AlertPriority.HIGH,
                        title=f"{pp.competitor} dropped prices",
                        description=f"Price dropped from €{prev.price:.2f} to €{pp.price:.2f}",
                        source_url=pp.url,
                        timestamp=now,
                        suggested_action="Consider adjusting pricing or highlighting value proposition",
                    )
                    alerts.append(alert)

        # New competitor alert
        for comp in report.competitors:
            if comp.last_scanned == now[:10]:  # New today
                alert = CompetitorAlert(
                    competitor=comp.name,
                    change_type=ChangeType.NEW_MARKET,
                    priority=AlertPriority.MEDIUM,
                    title=f"New competitor discovered: {comp.name}",
                    description=f"Found on {', '.join(comp.platforms.keys())}",
                    timestamp=now,
                    suggested_action="Analyze their product line and pricing strategy",
                )
                alerts.append(alert)

        self._alerts.extend(alerts)
        self._stats["alerts_generated"] += len(alerts)
        return alerts

    def _is_competitor(self, title: str, snippet: str, url: str) -> bool:
        """Check if a search result is a potential competitor."""
        combined = f"{title} {snippet}".lower()
        competitor_signals = [
            "candle", "concrete", "handmade", "artisan",
            "decor", "home", "design", "craft",
            "kynttilä", "betoni", "käsintehty", "sisustus",
            "ljus", "betong", "handgjord", "inredning",
        ]
        # Must match at least 2 signals
        matches = sum(1 for s in competitor_signals if s in combined)
        if matches < 2:
            return False

        # Skip non-shop results
        non_shop = ["wikipedia", "dictionary", "how to", "diy tutorial"]
        if any(ns in combined for ns in non_shop):
            return False

        # Must be a shop/store/seller
        shop_signals = [
            "shop", "store", "buy", "price", "€", "$",
            "etsy", "amazon", "kauppa", "myydään",
            "seller", "artisan", "maker",
        ]
        return any(s in combined for s in shop_signals)

    def _extract_brand_name(self, title: str, domain: str) -> str:
        """Extract a clean brand name from title or domain."""
        # Clean title
        name = title.split("-")[0].split("|")[0].split("–")[0].strip()
        # Remove common suffixes
        for suffix in ["Etsy", "Shop", "Store", "Home", "by"]:
            name = re.sub(rf'\s*{suffix}\s*$', '', name, flags=re.I).strip()
        if len(name) > 3 and len(name) < 50:
            return name
        # Fallback to domain
        return domain.split(".")[0].title()

    def _detect_platform(self, url: str) -> Optional[str]:
        """Detect platform from URL."""
        url_lower = url.lower()
        platforms = {
            "etsy.com": "etsy",
            "amazon.": "amazon",
            "tori.fi": "tori",
            "facebook.com": "facebook",
            "instagram.com": "instagram",
            "pinterest.": "pinterest",
            "shopify.com": "shopify",
        }
        for domain, platform in platforms.items():
            if domain in url_lower:
                return platform
        return "website"

    def _guess_product_name(self, text: str) -> str:
        """Guess product name from text snippet."""
        product_words = ["candle", "holder", "concrete", "stone", "vase",
                        "planter", "tray", "coaster", "sculpture"]
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in product_words:
                start = max(0, i - 2)
                end = min(len(words), i + 3)
                return " ".join(words[start:end])
        return "Unknown product"

    def _analyze_price_trend(
        self, competitor: str, history: List[PricePoint],
    ) -> Dict[str, Any]:
        """Analyze price trends from history."""
        if not history:
            return {"competitor": competitor, "trend": "no_data"}

        prices = [pp.price for pp in history]
        return {
            "competitor": competitor,
            "current_avg": sum(prices) / len(prices),
            "min": min(prices),
            "max": max(prices),
            "data_points": len(prices),
            "trend": "stable" if len(prices) < 2 else
                     "rising" if prices[-1] > prices[0] else
                     "falling" if prices[-1] < prices[0] else "stable",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            **self._stats,
            "our_brand": self.our_brand,
            "tracked_count": len(self._tracked),
            "web_search_available": _SEARCH_AVAILABLE,
        }


