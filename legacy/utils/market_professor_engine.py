
from __future__ import annotations
"""
tg_bot/utils/market_professor_engine.py — Marketing Agent TITAN (L9)
═════════════════════════════════════════════════════════════════════
Strategic market intelligence and analysis engine — "Professor of Marketing".

Architecture
────────────
   ┌─────────────────────────────────────────────────────────┐
   │              MARKET PROFESSOR ENGINE                     │
   ├──────────┬──────────┬──────────┬──────────┬─────────────┤
   │ Analyze  │ Compete  │ Social   │ Forecast │ Report      │
   ├──────────┼──────────┼──────────┼──────────┼─────────────┤
   │ Multi-   │ Pricing  │ IG Strat │ Trend    │ Daily       │
   │ Dimen    │ Compare  │ Pin Strt │ Detect   │ Briefing    │
   │ Market   │ Product  │ TikTok   │ Season   │ Weekly      │
   │ Region   │ Position │ FB Strt  │ Demand   │ Monthly     │
   │ Platform │ Opport.  │ Calendar │ Project  │ Custom      │
   └──────────┴──────────┴──────────┴──────────┴─────────────┘

Analysis Dimensions
───────────────────
  • Price × Region × Platform × Season × Category
  • Competitor landscape monitoring
  • Social media strategy generation (IG / Pinterest / TikTok / FB)
  • Platform ROI ranking
  • Trend detection & demand forecasting

Reuses
──────
  • forecast_engine.py — time-series trend projection
  • web_search.py — competitor research
  • ai_client.py — strategic insight generation
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Existing modules ──
try:
    from arki_project.utils.forecast_engine import ForecastEngine
    _FORECAST_AVAILABLE = True
except ImportError:
    _FORECAST_AVAILABLE = False

try:
    from arki_project.utils.web_search import WebSearchEngine
    _WEB_SEARCH_AVAILABLE = True
except ImportError:
    _WEB_SEARCH_AVAILABLE = False

# ── OMEGA modules ──
try:
    from arki_project.utils.deep_recon_engine import DeepReconEngine
    _DEEP_RECON_AVAILABLE = True
except ImportError:
    _DEEP_RECON_AVAILABLE = False

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
    from arki_project.utils.contact_intel_engine import ContactIntelEngine
    _CONTACT_INTEL_AVAILABLE = True
except ImportError:
    _CONTACT_INTEL_AVAILABLE = False

try:
    from arki_project.utils.content_forge_engine import ContentForgeEngine, ContentType
    _CONTENT_FORGE_AVAILABLE = True
except ImportError:
    _CONTENT_FORGE_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class CompetitorProfile:
    """Profile of a competitor brand."""
    name: str = ""
    website: str = ""
    price_range: str = ""
    products: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    social_followers: Dict[str, int] = field(default_factory=dict)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "website": self.website,
            "price_range": self.price_range,
            "products": self.products,
            "platforms": self.platforms,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "social_followers": self.social_followers,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass
class MarketInsight:
    """A single market insight or recommendation."""
    category: str = ""  # trend, opportunity, threat, recommendation
    title: str = ""
    description: str = ""
    impact: str = "medium"  # low, medium, high, critical
    action_items: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "action_items": self.action_items,
            "data": self.data,
        }


@dataclass
class DailyBriefing:
    """Complete daily marketing briefing."""
    date: str = ""
    summary: str = ""
    insights: List[MarketInsight] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    leads: List[Dict[str, Any]] = field(default_factory=list)
    platform_performance: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "summary": self.summary,
            "insights": [i.to_dict() for i in self.insights],
            "opportunities": self.opportunities,
            "leads": self.leads,
            "platform_performance": self.platform_performance,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }


# ═══════════════════════════════════════════════════════════
# Social Media Strategy
# ═══════════════════════════════════════════════════════════

SOCIAL_STRATEGIES = {
    "instagram": {
        "posting_frequency": "5-7 posts/week + daily stories",
        "best_times": ["09:00", "12:00", "18:00"],
        "content_mix": {
            "product_shots": 30,
            "behind_the_scenes": 20,
            "lifestyle_context": 20,
            "customer_features": 15,
            "educational": 10,
            "promotional": 5,
        },
        "hashtag_strategy": {
            "branded": ["#arkiobjects", "#arkicandles"],
            "product": ["#concretecandle", "#stonecandle", "#tealightholder"],
            "style": ["#scandinaviandesign", "#minimalistdecor", "#nordicliving"],
            "location": ["#madeinfinland", "#finnishdesign", "#pieksämäki"],
            "community": ["#handmadewithlove", "#artisanmade", "#smallbusiness"],
        },
    },
    "pinterest": {
        "posting_frequency": "10-15 pins/week",
        "best_times": ["14:00", "20:00"],
        "content_mix": {
            "product_pins": 40,
            "lifestyle_boards": 25,
            "diy_inspiration": 15,
            "gift_guides": 10,
            "seasonal": 10,
        },
        "board_strategy": [
            "Scandinavian Home Décor",
            "Concrete & Stone Design",
            "Candle Inspiration",
            "Minimalist Living",
            "Gift Ideas from Finland",
        ],
    },
    "tiktok": {
        "posting_frequency": "3-5 videos/week",
        "best_times": ["07:00", "12:00", "19:00"],
        "content_mix": {
            "making_process": 35,
            "satisfying_pours": 25,
            "before_after": 15,
            "packing_orders": 15,
            "trending_sounds": 10,
        },
        "content_ideas": [
            "Time-lapse of concrete pouring process",
            "ASMR: sanding and finishing stone candles",
            "Packing a customer order with care",
            "Before/after: raw concrete → finished candle",
            "Day in the life of a Finnish candle maker",
        ],
    },
    "facebook": {
        "posting_frequency": "3-5 posts/week",
        "best_times": ["09:00", "13:00", "16:00"],
        "content_mix": {
            "product_showcase": 25,
            "community_engagement": 25,
            "behind_the_scenes": 20,
            "customer_stories": 15,
            "promotional": 15,
        },
    },
}


# ═══════════════════════════════════════════════════════════
# Market Professor Engine
# ═══════════════════════════════════════════════════════════

class MarketProfessorEngine:
    """
    Strategic market intelligence engine — the "Professor of Marketing".

    Provides:
    - Multi-dimensional market analysis
    - Competitor intelligence
    - Social media strategy
    - Platform ROI ranking
    - Daily briefings with opportunities + leads + recommendations
    - Trend detection and demand forecasting
    """

    def __init__(
        self,
        *,
        competitor_limit: int = 20,
    ) -> None:
        self._competitor_limit = competitor_limit
        self._competitors: Dict[str, CompetitorProfile] = {}
        self._insights_cache: List[MarketInsight] = []
        self._web_search = WebSearchEngine() if _WEB_SEARCH_AVAILABLE else None
        self._forecast = ForecastEngine() if _FORECAST_AVAILABLE else None
        # OMEGA engines
        self._deep_recon = DeepReconEngine() if _DEEP_RECON_AVAILABLE else None
        self._social_intel = SocialIntelEngine() if _SOCIAL_INTEL_AVAILABLE else None
        self._competitor_radar = CompetitorRadarEngine() if _COMPETITOR_RADAR_AVAILABLE else None
        self._contact_intel = ContactIntelEngine() if _CONTACT_INTEL_AVAILABLE else None
        self._content_forge = ContentForgeEngine() if _CONTENT_FORGE_AVAILABLE else None

    # ── Daily Briefing ───────────────────────────────────

    async def generate_daily_briefing(
        self,
        *,
        data_bridge=None,
        platform_engine=None,
        ai_client=None,
    ) -> DailyBriefing:
        """
        Generate a comprehensive daily marketing briefing.

        Aggregates data from:
        - Dashboard stats (prospects, emails, listings)
        - Platform performance
        - New opportunities
        - Learning insights
        - Market trends
        """
        now = datetime.now(timezone.utc)
        briefing = DailyBriefing(date=now.strftime("%Y-%m-%d"))

        # 1. Gather metrics
        if data_bridge:
            briefing.metrics = await data_bridge.get_dashboard_stats()

            # Hot leads
            hot_prospects = await data_bridge.get_prospects(
                min_score=70.0, limit=10,
            )
            briefing.leads = hot_prospects

            # New opportunities
            opps = await data_bridge.get_opportunities(
                status="discovered", limit=10,
            )
            briefing.opportunities = opps

            # Learning insights
            learning = await data_bridge.get_learning_insights(days=7)
            if learning.get("success_rate_by_type"):
                briefing.insights.append(MarketInsight(
                    category="trend",
                    title="Outreach Performance (7d)",
                    description=f"Success rates: {learning['success_rate_by_type']}",
                    impact="medium",
                    data=learning,
                ))

        # 2. Platform performance
        if platform_engine:
            try:
                ranking = await platform_engine.get_platform_ranking(data_bridge=data_bridge)
                briefing.platform_performance = ranking[:10]
            except Exception as exc:
                logger.warning("Platform ranking error: %s", exc)

        # 3. Seasonal insights
        seasonal = self._get_seasonal_insights(now)
        briefing.insights.extend(seasonal)

        # 4. AI-powered summary (if available)
        if ai_client:
            try:
                briefing.summary = await self._generate_ai_summary(briefing, ai_client)
            except Exception:
                briefing.summary = self._generate_template_summary(briefing)
        else:
            briefing.summary = self._generate_template_summary(briefing)

        # 5. Recommendations
        briefing.recommendations = self._generate_recommendations(briefing)

        # 6. Store report
        if data_bridge:
            await data_bridge.store_report({
                "report_type": "daily_brief",
                "title": f"Daily Briefing — {briefing.date}",
                "summary": briefing.summary,
                "full_report": briefing.to_dict(),
                "recommendations": briefing.recommendations,
                "metrics": briefing.metrics,
            })

        return briefing

    # ── Competitor Intelligence ───────────────────────────

    async def analyze_competitors(
        self,
        *,
        ai_client=None,
        data_bridge=None,
    ) -> List[CompetitorProfile]:
        """
        Research and analyze competitor brands in the handmade candle space.
        """
        if not self._web_search:
            return list(self._competitors.values())

        competitor_queries = [
            "handmade concrete candle brand Europe",
            "artisan candle maker Finland Nordic",
            "minimalist candle brand Etsy top sellers",
            "handmade stone candle holder brand",
            "concrete home decor brand Scandinavian",
        ]

        discovered = []
        for query in competitor_queries[:3]:
            try:
                results = await self._web_search.search(query, max_results=10)
                for sr in results:
                    title = sr.get("title", "") if isinstance(sr, dict) else getattr(sr, "title", "")
                    url = sr.get("url", "") if isinstance(sr, dict) else getattr(sr, "url", "")
                    snippet = sr.get("snippet", "") if isinstance(sr, dict) else getattr(sr, "snippet", "")

                    if self._is_competitor_brand(title, url, snippet):
                        profile = CompetitorProfile(
                            name=title[:128],
                            website=url,
                            last_updated=datetime.now(timezone.utc),
                        )
                        key = url.lower()
                        if key not in self._competitors:
                            self._competitors[key] = profile
                            discovered.append(profile)

                import asyncio
                await asyncio.sleep(2.0)

            except Exception as exc:
                logger.warning("Competitor research error: %s", exc)

        # Store as report
        if data_bridge and discovered:
            await data_bridge.store_report({
                "report_type": "competitor_analysis",
                "title": f"Competitor Analysis — {len(discovered)} brands found",
                "summary": f"Discovered {len(discovered)} competitor brands",
                "full_report": {"competitors": [c.to_dict() for c in discovered]},
                "recommendations": [],
            })

        return discovered

    # ── Social Media Strategy ────────────────────────────

    async def get_social_strategy(
        self,
        platform: str,
        *,
        ai_client=None,
    ) -> Dict[str, Any]:
        """
        Get social media strategy for a specific platform.

        Returns posting frequency, content mix, hashtags, and content ideas.
        """
        base_strategy = SOCIAL_STRATEGIES.get(platform, {})
        if not base_strategy:
            return {"error": f"No strategy template for {platform}"}

        strategy = dict(base_strategy)
        strategy["platform"] = platform

        # Enhance with AI if available
        if ai_client:
            try:
                prompt = f"""As a social media strategist for ArkiObjects (Finnish handmade concrete candles,
minimalist Scandinavian style, €10-50 price range), suggest 5 specific content ideas
for {platform} this week. Consider current trends and seasonal relevance.

Return as JSON: {{"content_ideas": ["idea1", "idea2", ...]}}"""

                response = await ai_client.generate(prompt)
                text = response.get("text", str(response)) if isinstance(response, dict) else str(response)

                import re
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    ai_ideas = json.loads(json_match.group())
                    strategy["ai_content_ideas"] = ai_ideas.get("content_ideas", [])

            except Exception as exc:
                logger.debug("AI social strategy enhancement failed: %s", exc)

        return strategy

    # ── Market Analysis ──────────────────────────────────

    async def analyze_market(
        self,
        *,
        dimension: str = "overview",
        data_bridge=None,
        ai_client=None,
    ) -> Dict[str, Any]:
        """
        Multi-dimensional market analysis.

        Dimensions: overview, pricing, regional, platform, seasonal
        """
        analysis: Dict[str, Any] = {
            "dimension": dimension,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if dimension == "overview" or dimension == "all":
            analysis["overview"] = {
                "market": "Handmade home décor & candles",
                "position": "Premium artisan, Scandinavian minimalist",
                "key_regions": ["Finland", "Nordics", "DACH", "UK", "North America"],
                "growth_areas": [
                    "Sustainable/eco-friendly products",
                    "Corporate gifting",
                    "Interior design partnerships",
                    "Experience-based marketing",
                ],
            }

        if dimension == "pricing" or dimension == "all":
            analysis["pricing"] = {
                "our_range_eur": {"min": 10, "max": 50, "average": 25},
                "market_comparison": {
                    "budget_handmade": {"range": "€5-15", "quality": "mass-handmade"},
                    "mid_artisan": {"range": "€15-35", "quality": "quality artisan"},
                    "premium_design": {"range": "€35-80+", "quality": "designer/limited"},
                },
                "positioning": "Mid-premium (excellent value for quality)",
                "recommendation": "Maintain €10-50; introduce premium limited editions at €50-80",
            }

        if dimension == "regional" or dimension == "all":
            if data_bridge:
                stats = await data_bridge.get_dashboard_stats()
                analysis["regional"] = {
                    "prospect_distribution": stats.get("prospects", {}),
                    "recommendation": "Focus on Finland → Nordics → DACH expansion path",
                }
            else:
                analysis["regional"] = {"status": "No data bridge available"}

        if dimension == "seasonal" or dimension == "all":
            now = datetime.now(timezone.utc)
            analysis["seasonal"] = {
                "current_month": now.month,
                "peak_months": [10, 11, 12],
                "is_peak": now.month in [10, 11, 12],
                "preparation_advice": self._get_seasonal_advice(now.month),
            }

        return analysis

    # ── Trend & Forecast ─────────────────────────────────

    async def detect_trends(
        self,
        *,
        data_bridge=None,
    ) -> List[MarketInsight]:
        """Detect trends from marketing event data."""
        trends: List[MarketInsight] = []

        if data_bridge:
            insights = await data_bridge.get_learning_insights(days=30)
            by_type = insights.get("by_type", {})

            # Email response rate trend
            email_sent = by_type.get("email_sent", 0)
            email_replied = by_type.get("email_replied", 0)
            if email_sent > 10:
                response_rate = round(email_replied / email_sent * 100, 1)
                impact = "high" if response_rate > 10 else "medium" if response_rate > 5 else "low"
                trends.append(MarketInsight(
                    category="trend",
                    title="Email Response Rate",
                    description=f"{response_rate}% response rate ({email_replied}/{email_sent})",
                    impact=impact,
                    data={"rate": response_rate, "sent": email_sent, "replied": email_replied},
                ))

            # Prospect discovery rate
            prospects_found = by_type.get("prospect_found", 0)
            if prospects_found > 0:
                trends.append(MarketInsight(
                    category="trend",
                    title="Prospect Discovery",
                    description=f"{prospects_found} new prospects in 30 days",
                    impact="medium",
                    data={"total": prospects_found},
                ))

        return trends

    # ── Internal Helpers ─────────────────────────────────

    def _get_seasonal_insights(self, now: datetime) -> List[MarketInsight]:
        """Generate seasonal marketing insights."""
        month = now.month
        insights = []

        if month in (8, 9):
            insights.append(MarketInsight(
                category="opportunity",
                title="Christmas Market Preparation",
                description="Start applying for Christmas markets NOW. Application deadlines are typically 2-3 months before.",
                impact="high",
                action_items=[
                    "Search for Christmas market vendor applications",
                    "Prepare product catalog for wholesale",
                    "Stock up inventory for peak season",
                ],
            ))

        if month in (10, 11):
            insights.append(MarketInsight(
                category="opportunity",
                title="Peak Holiday Season",
                description="This is the biggest sales period. Maximize visibility on all platforms.",
                impact="critical",
                action_items=[
                    "Boost Etsy listings with holiday keywords",
                    "Launch gift guide content on social media",
                    "Run B2B outreach to hotels for holiday decoration",
                    "Ensure all platforms have stock updated",
                ],
            ))

        if month in (1, 2):
            insights.append(MarketInsight(
                category="recommendation",
                title="Post-Holiday Strategy",
                description="Focus on Valentine's Day and spring décor transitions.",
                impact="medium",
                action_items=[
                    "Create Valentine's gift bundles",
                    "Target wedding planners for spring season",
                    "Refresh product photos with spring styling",
                ],
            ))

        return insights

    def _get_seasonal_advice(self, month: int) -> str:
        """Get seasonal marketing advice for the current month."""
        advice_map = {
            1: "New Year décor push. Valentine's prep. Review holiday performance.",
            2: "Valentine's campaigns. Spring collection planning. Wedding planner outreach.",
            3: "Spring collection launch. Easter prep. Interior design partnerships.",
            4: "Spring markets. Mother's Day prep. Refresh platform listings.",
            5: "Mother's Day campaigns. Summer event planning. B2B hotel outreach.",
            6: "Summer collection. Midsummer marketing (Nordics). Start Christmas prep.",
            7: "Summer markets. Behind-the-scenes content. Inventory planning.",
            8: "Christmas market applications due! Back-to-school décor. Autumn preview.",
            9: "Autumn collection launch. Christmas market prep. B2B holiday outreach.",
            10: "Pre-holiday push. Christmas market season starts. Gift guide content.",
            11: "BLACK FRIDAY. Cyber Monday. Holiday shipping deadlines. Peak outreach.",
            12: "Christmas sales peak. Last-minute gifts. New Year planning.",
        }
        return advice_map.get(month, "Focus on consistent content and outreach.")

    async def _generate_ai_summary(self, briefing: DailyBriefing, ai_client: Any) -> str:
        """Generate an AI-powered briefing summary."""
        prompt = f"""Summarize this marketing briefing in 3-4 concise sentences:

Metrics: {json.dumps(briefing.metrics, default=str)}
Hot leads: {len(briefing.leads)}
New opportunities: {len(briefing.opportunities)}
Insights: {len(briefing.insights)}
Platform performance: {len(briefing.platform_performance)} platforms tracked

Focus on actionable takeaways for a Finnish handmade candle brand (ArkiObjects).
Write in English, professional tone."""

        response = await ai_client.generate(prompt)
        return response.get("text", str(response)) if isinstance(response, dict) else str(response)

    def _generate_template_summary(self, briefing: DailyBriefing) -> str:
        """Generate a template-based briefing summary."""
        prospects = briefing.metrics.get("prospects", {})
        total_prospects = sum(prospects.values()) if isinstance(prospects, dict) else 0

        return (
            f"📊 Daily Marketing Brief — {briefing.date}\n"
            f"Prospects: {total_prospects} total | "
            f"Hot leads: {len(briefing.leads)} | "
            f"New opportunities: {len(briefing.opportunities)} | "
            f"Platforms tracked: {len(briefing.platform_performance)}\n"
            f"Insights: {len(briefing.insights)} actionable items."
        )

    def _generate_recommendations(self, briefing: DailyBriefing) -> List[str]:
        """Generate action recommendations from the briefing."""
        recs = []

        # Based on hot leads
        if briefing.leads:
            recs.append(f"🔥 {len(briefing.leads)} hot leads — prioritize outreach today")

        # Based on opportunities
        if briefing.opportunities:
            recs.append(f"🆕 {len(briefing.opportunities)} new opportunities — review and evaluate")

        # Based on insights
        for insight in briefing.insights:
            if insight.impact in ("high", "critical"):
                recs.append(f"⚠️ {insight.title}: {insight.action_items[0]}" if insight.action_items else "")

        # Platform-based
        if briefing.platform_performance:
            top = briefing.platform_performance[0] if briefing.platform_performance else None
            if top:
                recs.append(f"📈 Top platform: {top.get('name', 'Unknown')} — focus listings here")

        return [r for r in recs if r]

    @staticmethod
    def _is_competitor_brand(title: str, url: str, snippet: str) -> bool:
        """Check if a search result represents a competitor brand."""
        combined = f"{title} {snippet}".lower()
        brand_signals = [
            "handmade candle", "concrete candle", "artisan candle",
            "stone candle", "design candle", "hand poured",
        ]
        has_signal = any(s in combined for s in brand_signals)

        # Exclude directories, articles, generic results
        exclude = ["how to", "diy", "recipe", "wikipedia", "youtube.com"]
        is_excluded = any(e in combined for e in exclude)

        return has_signal and not is_excluded

    # ── OMEGA: Advanced Intelligence Methods ────────────

    async def omega_deep_competitor_analysis(
        self,
        competitor_domain: str,
    ) -> Dict[str, Any]:
        """Run deep recon + contact intel on a competitor domain."""
        result: Dict[str, Any] = {"domain": competitor_domain}

        if self._deep_recon:
            try:
                recon = await self._deep_recon.full_recon(competitor_domain, depth="deep")
                result["deep_recon"] = recon.to_dict() if hasattr(recon, 'to_dict') else {}
            except Exception as exc:
                result["deep_recon_error"] = str(exc)

        if self._contact_intel:
            try:
                contacts = await self._contact_intel.discover_contacts(
                    company_name=competitor_domain.split(".")[0].title(),
                    domain=competitor_domain,
                )
                result["contacts"] = contacts.to_dict()
            except Exception as exc:
                result["contacts_error"] = str(exc)

        return result

    async def omega_market_scan(self) -> Dict[str, Any]:
        """Run full OMEGA market scan with all engines."""
        report: Dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat()}

        # Competitor radar
        if self._competitor_radar:
            try:
                radar = await self._competitor_radar.full_scan()
                report["competitor_radar"] = radar.to_dict()
            except Exception as exc:
                report["competitor_radar_error"] = str(exc)

        # Social intel
        if self._social_intel:
            try:
                social = await self._social_intel.full_social_intel()
                report["social_intel"] = social.to_dict()
            except Exception as exc:
                report["social_intel_error"] = str(exc)

        # Trends
        if self._social_intel:
            try:
                report["current_trends"] = [
                    t.to_dict() for t in self._social_intel.get_current_trends()
                ]
            except Exception as exc:
                report["trends_error"] = str(exc)

        return report

    async def omega_content_calendar(
        self, weeks: int = 4, posts_per_week: int = 3,
    ) -> List[Dict[str, Any]]:
        """Generate content calendar via OMEGA ContentForge."""
        if not self._content_forge:
            return []
        try:
            entries = self._content_forge.generate_content_calendar(
                weeks_ahead=weeks, posts_per_week=posts_per_week,
            )
            return [e.to_dict() for e in entries]
        except Exception as exc:
            logger.warning("Content calendar generation failed: %s", exc)
            return []

    async def omega_ab_test(
        self,
        prospect: Dict[str, Any],
        test_variable: str = "subject_line",
    ) -> Dict[str, Any]:
        """Generate A/B test plan via OMEGA ContentForge."""
        if not self._content_forge:
            return {"error": "ContentForge not available"}
        try:
            plan = await self._content_forge.generate_ab_variants(
                content_type=ContentType.EMAIL_B2B if _CONTENT_FORGE_AVAILABLE else None,
                base_params={"prospect": prospect, "language": "en"},
                test_variable=test_variable,
            )
            return plan.to_dict()
        except Exception as exc:
            return {"error": str(exc)}

    def get_stats(self) -> Dict[str, Any]:
        """Get market professor engine stats."""
        return {
            "competitors_tracked": len(self._competitors),
            "cached_insights": len(self._insights_cache),
            "forecast_available": _FORECAST_AVAILABLE,
            "web_search_available": _WEB_SEARCH_AVAILABLE,
            "social_strategies": list(SOCIAL_STRATEGIES.keys()),
            "omega_deep_recon": _DEEP_RECON_AVAILABLE,
            "omega_social_intel": _SOCIAL_INTEL_AVAILABLE,
            "omega_competitor_radar": _COMPETITOR_RADAR_AVAILABLE,
            "omega_contact_intel": _CONTACT_INTEL_AVAILABLE,
            "omega_content_forge": _CONTENT_FORGE_AVAILABLE,
        }


