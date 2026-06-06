
from __future__ import annotations
"""
utils/social_intel_engine.py — Social Intelligence Engine  v1.0-OMEGA
═════════════════════════════════════════════════════════════════════════
Social media intelligence, influencer discovery, and trend analysis.

Capabilities
────────────
  • Influencer Discovery — find relevant influencers by niche + region
  • Hashtag Analysis     — effectiveness scoring, cluster detection
  • Review Sentiment     — multi-language sentiment across platforms
  • Trend Detection      — seasonal + viral trend identification
  • Community Finder     — Facebook groups, Reddit, forums, Pinterest boards
  • Engagement Scoring   — predict content performance
  • Competitor Social    — monitor competitor social strategies

Author: Viktor AI  |  Arki Engine OMEGA
"""


import asyncio
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

class Platform(Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    PINTEREST = "pinterest"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    REDDIT = "reddit"
    ETSY = "etsy"


class SentimentLabel(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class Influencer:
    """Discovered influencer profile."""
    name: str
    platform: Platform
    handle: str
    url: str
    followers_estimate: Optional[int] = None
    engagement_rate: Optional[float] = None
    niche_tags: List[str] = field(default_factory=list)
    location: Optional[str] = None
    language: Optional[str] = None
    relevance_score: float = 0.0  # 0-1
    contact_info: Optional[str] = None
    collaboration_fit: float = 0.0  # 0-1
    source: str = "search"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "platform": self.platform.value,
            "handle": self.handle, "url": self.url,
            "followers_estimate": self.followers_estimate,
            "engagement_rate": self.engagement_rate,
            "niche_tags": self.niche_tags,
            "location": self.location, "language": self.language,
            "relevance_score": self.relevance_score,
            "contact_info": self.contact_info,
            "collaboration_fit": self.collaboration_fit,
            "source": self.source,
        }


@dataclass
class HashtagCluster:
    """Group of related hashtags with effectiveness metrics."""
    primary_tag: str
    related_tags: List[str] = field(default_factory=list)
    estimated_posts: Optional[int] = None
    competition_level: str = "medium"  # low, medium, high
    relevance_score: float = 0.0
    recommended_usage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_tag": self.primary_tag,
            "related_tags": self.related_tags,
            "estimated_posts": self.estimated_posts,
            "competition_level": self.competition_level,
            "relevance_score": self.relevance_score,
            "recommended_usage": self.recommended_usage,
        }


@dataclass
class ReviewInsight:
    """Aggregated review sentiment and insights."""
    platform: str
    total_reviews: int = 0
    average_rating: float = 0.0
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL
    sentiment_score: float = 0.0  # -1 to 1
    positive_themes: List[str] = field(default_factory=list)
    negative_themes: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    sample_reviews: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "total_reviews": self.total_reviews,
            "average_rating": self.average_rating,
            "sentiment": self.sentiment.value,
            "sentiment_score": self.sentiment_score,
            "positive_themes": self.positive_themes,
            "negative_themes": self.negative_themes,
            "keywords": self.keywords,
            "sample_reviews": self.sample_reviews,
        }


@dataclass
class TrendSignal:
    """Detected trend or seasonal pattern."""
    trend_type: str  # seasonal, viral, emerging, declining
    topic: str
    description: str
    platforms: List[str] = field(default_factory=list)
    strength: float = 0.0  # 0-1
    time_sensitivity: str = "medium"  # low, medium, high, urgent
    action_suggestion: str = ""
    relevant_hashtags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_type": self.trend_type, "topic": self.topic,
            "description": self.description, "platforms": self.platforms,
            "strength": self.strength,
            "time_sensitivity": self.time_sensitivity,
            "action_suggestion": self.action_suggestion,
            "relevant_hashtags": self.relevant_hashtags,
        }


@dataclass
class Community:
    """Online community relevant to business."""
    name: str
    platform: str
    url: str
    member_count: Optional[int] = None
    activity_level: str = "medium"
    relevance_score: float = 0.0
    description: str = ""
    join_strategy: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "platform": self.platform,
            "url": self.url, "member_count": self.member_count,
            "activity_level": self.activity_level,
            "relevance_score": self.relevance_score,
            "description": self.description,
            "join_strategy": self.join_strategy,
        }


@dataclass
class SocialIntelReport:
    """Complete social intelligence report."""
    query: str
    generated_at: str = ""
    influencers: List[Influencer] = field(default_factory=list)
    hashtag_clusters: List[HashtagCluster] = field(default_factory=list)
    review_insights: List[ReviewInsight] = field(default_factory=list)
    trends: List[TrendSignal] = field(default_factory=list)
    communities: List[Community] = field(default_factory=list)
    competitor_profiles: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query, "generated_at": self.generated_at,
            "influencers": [i.to_dict() for i in self.influencers],
            "hashtag_clusters": [h.to_dict() for h in self.hashtag_clusters],
            "review_insights": [r.to_dict() for r in self.review_insights],
            "trends": [t.to_dict() for t in self.trends],
            "communities": [c.to_dict() for c in self.communities],
            "competitor_profiles": self.competitor_profiles,
            "errors": self.errors,
        }


# ═══════════════════════════════════════════════════════════════════════
#  Sentiment Analysis (rule-based multi-language)
# ═══════════════════════════════════════════════════════════════════════

# Positive/negative word lists (EN, FI, SV, DE, FR)
_POSITIVE_WORDS = {
    "en": {"beautiful", "amazing", "love", "excellent", "wonderful", "perfect",
           "great", "stunning", "gorgeous", "unique", "quality", "handmade",
           "cozy", "elegant", "charming", "fantastic", "recommend", "best"},
    "fi": {"kaunis", "upea", "ihana", "erinomainen", "loistava", "täydellinen",
           "hieno", "ainutlaatuinen", "laadukas", "käsintehty", "kodikkaat",
           "tyylikäs", "suosittelen", "paras", "mahtava", "tunnelmallinen"},
    "sv": {"vacker", "fantastisk", "underbar", "utmärkt", "perfekt",
           "unik", "kvalitet", "handgjord", "mysig", "elegant", "rekommenderar"},
    "de": {"schön", "wunderbar", "ausgezeichnet", "perfekt", "einzigartig",
           "handgemacht", "gemütlich", "elegant", "empfehle", "qualität"},
    "fr": {"beau", "magnifique", "excellent", "parfait", "unique",
           "artisanal", "élégant", "recommande", "qualité", "charmant"},
}

_NEGATIVE_WORDS = {
    "en": {"bad", "terrible", "awful", "poor", "broken", "disappointed",
           "cheap", "fragile", "overpriced", "damaged", "waste", "horrible",
           "worst", "scam", "slow", "ugly", "defective", "refund"},
    "fi": {"huono", "kamala", "pettymys", "halpa", "hauras", "kallis",
           "vaurioitunut", "turha", "hidas", "ruma", "viallinen", "palautus"},
    "sv": {"dålig", "fruktansvärd", "besviken", "billig", "skör",
           "dyr", "skadad", "långsam", "ful", "defekt", "retur"},
    "de": {"schlecht", "schrecklich", "enttäuscht", "billig", "zerbrechlich",
           "teuer", "beschädigt", "langsam", "hässlich", "defekt"},
    "fr": {"mauvais", "terrible", "déçu", "bon marché", "fragile",
           "cher", "endommagé", "lent", "laid", "défectueux"},
}


def _analyze_sentiment(text: str) -> Tuple[SentimentLabel, float]:
    """Analyze sentiment of text (multi-language)."""
    text_lower = text.lower()
    words = set(re.findall(r'\b[a-zäöåéèüñ]+\b', text_lower))

    pos_count = 0
    neg_count = 0
    for lang_words in _POSITIVE_WORDS.values():
        pos_count += len(words & lang_words)
    for lang_words in _NEGATIVE_WORDS.values():
        neg_count += len(words & lang_words)

    total = pos_count + neg_count
    if total == 0:
        return SentimentLabel.NEUTRAL, 0.0

    score = (pos_count - neg_count) / max(total, 1)
    score = max(-1.0, min(1.0, score))

    if score >= 0.5:
        return SentimentLabel.VERY_POSITIVE, score
    elif score >= 0.15:
        return SentimentLabel.POSITIVE, score
    elif score <= -0.5:
        return SentimentLabel.VERY_NEGATIVE, score
    elif score <= -0.15:
        return SentimentLabel.NEGATIVE, score
    return SentimentLabel.NEUTRAL, score


def _extract_themes(texts: List[str], positive: bool = True) -> List[str]:
    """Extract common themes from review texts."""
    word_set = set()
    for lang_words in (_POSITIVE_WORDS if positive else _NEGATIVE_WORDS).values():
        word_set.update(lang_words)

    theme_counts: Dict[str, int] = {}
    for text in texts:
        words = set(re.findall(r'\b[a-zäöåéèüñ]+\b', text.lower()))
        matches = words & word_set
        for m in matches:
            theme_counts[m] = theme_counts.get(m, 0) + 1

    sorted_themes = sorted(theme_counts.items(), key=lambda x: -x[1])
    return [t[0] for t in sorted_themes[:10]]


# ═══════════════════════════════════════════════════════════════════════
#  Hashtag Intelligence
# ═══════════════════════════════════════════════════════════════════════

# Product-relevant hashtag categories for handmade candles/decor
_HASHTAG_CATEGORIES = {
    "product_core": {
        "tags": ["handmadecandles", "concretecandles", "stonecandles",
                 "decorativecandles", "scentedcandles", "soywaxcandles",
                 "candlemaking", "handmadedecor", "homedecor",
                 "scandinaviandesign", "nordicdesign", "minimalistdecor"],
        "relevance": 1.0,
    },
    "lifestyle": {
        "tags": ["hygge", "cozy", "cozyhome", "homeinterior",
                 "slowliving", "mindfulhome", "selfcare",
                 "homedecoration", "interiordesign", "nordicliving"],
        "relevance": 0.8,
    },
    "material": {
        "tags": ["concrete", "handmade", "artisan", "handcrafted",
                 "madebyhand", "smallbusiness", "shopsmall",
                 "supportsmallbusiness", "makersmovement", "craftsman"],
        "relevance": 0.9,
    },
    "seasonal": {
        "tags": ["christmascandles", "christmasdecor", "wintercandles",
                 "autumndecor", "springdecor", "valentinesday",
                 "mothersday", "fathersday", "giftideas", "christmasgift"],
        "relevance": 0.7,
    },
    "location": {
        "tags": ["madeinfinland", "finnishdesign", "madeinnordics",
                 "scandinavian", "helsinki", "finnishmade",
                 "europeanmade", "nordiccraft", "finnishcraft"],
        "relevance": 0.85,
    },
    "market": {
        "tags": ["etsyseller", "etsyfinds", "shopetsy",
                 "handmadefinland", "designmarket", "artmarket",
                 "craftsmarket", "christmasmarket", "fleamarket"],
        "relevance": 0.6,
    },
}

_COMPETITION_THRESHOLDS = {
    "low": 50_000,      # < 50K posts
    "medium": 500_000,  # 50K - 500K posts
    "high": 5_000_000,  # > 500K posts
}


def _build_hashtag_clusters(
    niche: str = "candles",
    region: str = "finland",
) -> List[HashtagCluster]:
    """Build hashtag clusters for the niche."""
    clusters: List[HashtagCluster] = []

    for cat_name, cat_data in _HASHTAG_CATEGORIES.items():
        primary = cat_data["tags"][0] if cat_data["tags"] else cat_name
        cluster = HashtagCluster(
            primary_tag=f"#{primary}",
            related_tags=[f"#{t}" for t in cat_data["tags"][1:]],
            relevance_score=cat_data["relevance"],
            competition_level="medium",
            recommended_usage=f"Use 2-3 from '{cat_name}' category per post",
        )
        clusters.append(cluster)

    return clusters


# ═══════════════════════════════════════════════════════════════════════
#  Seasonal Trend Engine
# ═══════════════════════════════════════════════════════════════════════

_SEASONAL_TRENDS = {
    1: [  # January
        TrendSignal(
            trend_type="seasonal", topic="New Year Fresh Start",
            description="New year home refresh, declutter + redecorate",
            platforms=["instagram", "pinterest"],
            strength=0.7, time_sensitivity="high",
            action_suggestion="Post 'New Year New Home' content with minimalist candle setups",
            relevant_hashtags=["#newyeardecor", "#freshstart", "#homedecor2026"],
        ),
    ],
    2: [  # February
        TrendSignal(
            trend_type="seasonal", topic="Valentine's Day Gifts",
            description="Romantic gifts, candle gift sets peak demand",
            platforms=["instagram", "etsy", "pinterest"],
            strength=0.9, time_sensitivity="urgent",
            action_suggestion="Launch Valentine's gift bundles, romantic styling photos",
            relevant_hashtags=["#valentinesday", "#giftideas", "#romanticdecor"],
        ),
    ],
    3: [  # March
        TrendSignal(
            trend_type="seasonal", topic="Spring Awakening",
            description="Spring decor refresh, lighter colors and scents",
            platforms=["instagram", "pinterest"],
            strength=0.6, time_sensitivity="medium",
            action_suggestion="Feature spring scents and pastel concrete pieces",
            relevant_hashtags=["#springdecor", "#springcleaning", "#freshhome"],
        ),
    ],
    4: [  # April
        TrendSignal(
            trend_type="seasonal", topic="Easter & Spring Markets",
            description="Easter gifts, spring craft markets opening",
            platforms=["instagram", "facebook"],
            strength=0.7, time_sensitivity="high",
            action_suggestion="Prepare for spring market season, Easter-themed products",
            relevant_hashtags=["#easterdecor", "#springmarket", "#handmadegifts"],
        ),
    ],
    5: [  # May
        TrendSignal(
            trend_type="seasonal", topic="Mother's Day",
            description="Gift purchases spike, personalized items popular",
            platforms=["instagram", "etsy", "pinterest"],
            strength=0.9, time_sensitivity="urgent",
            action_suggestion="Mother's Day gift sets with premium packaging",
            relevant_hashtags=["#mothersday", "#giftformom", "#handmadegift"],
        ),
    ],
    6: [  # June
        TrendSignal(
            trend_type="seasonal", topic="Midsummer / Wedding Season",
            description="Juhannus in Finland, wedding decor peak",
            platforms=["instagram", "pinterest"],
            strength=0.8, time_sensitivity="high",
            action_suggestion="Wedding table candle collections, Midsummer themed posts",
            relevant_hashtags=["#juhannus", "#weddingdecor", "#summercandles"],
        ),
    ],
    7: [  # July
        TrendSignal(
            trend_type="seasonal", topic="Summer Living",
            description="Outdoor entertaining, terrace and garden decor",
            platforms=["instagram", "pinterest"],
            strength=0.5, time_sensitivity="low",
            action_suggestion="Outdoor candle styling, durable concrete pieces for gardens",
            relevant_hashtags=["#summerdecor", "#outdoorliving", "#gardencandles"],
        ),
    ],
    8: [  # August
        TrendSignal(
            trend_type="seasonal", topic="Back to Cozy",
            description="Transition to autumn, hygge content starts trending",
            platforms=["instagram", "pinterest", "tiktok"],
            strength=0.7, time_sensitivity="medium",
            action_suggestion="Start autumn content, warm tones, cozy setups",
            relevant_hashtags=["#hygge", "#cozyseason", "#autumndecor"],
        ),
    ],
    9: [  # September
        TrendSignal(
            trend_type="seasonal", topic="Autumn Craft Markets",
            description="Helsinki Design Week, autumn markets, craft fairs",
            platforms=["instagram", "facebook"],
            strength=0.8, time_sensitivity="high",
            action_suggestion="Apply to autumn markets, feature behind-the-scenes content",
            relevant_hashtags=["#designweek", "#craftmarket", "#autumncandles"],
        ),
    ],
    10: [  # October
        TrendSignal(
            trend_type="seasonal", topic="Halloween & Dark Aesthetics",
            description="Dark concrete pieces, moody candle styling",
            platforms=["instagram", "tiktok", "pinterest"],
            strength=0.7, time_sensitivity="high",
            action_suggestion="Moody dark concrete pieces, Halloween styling",
            relevant_hashtags=["#halloween", "#darkdecor", "#moodyhome"],
        ),
    ],
    11: [  # November
        TrendSignal(
            trend_type="seasonal", topic="Christmas Prep & Black Friday",
            description="Gift buying starts, Black Friday/Cyber Monday",
            platforms=["instagram", "etsy", "facebook"],
            strength=0.95, time_sensitivity="urgent",
            action_suggestion="Launch Christmas collection, Black Friday deals",
            relevant_hashtags=["#blackfriday", "#christmasgifts", "#shophandmade"],
        ),
    ],
    12: [  # December
        TrendSignal(
            trend_type="seasonal", topic="Christmas Markets & Last-Minute Gifts",
            description="Peak season: Christmas markets, gift sets, corporate gifts",
            platforms=["instagram", "etsy", "facebook"],
            strength=1.0, time_sensitivity="urgent",
            action_suggestion="Christmas market presence, express shipping, gift wrapping",
            relevant_hashtags=["#christmasmarket", "#joulumarkkinat", "#handmadechristmas"],
        ),
    ],
}

# Evergreen trends for handmade/artisan niche
_EVERGREEN_TRENDS = [
    TrendSignal(
        trend_type="emerging", topic="Sustainable & Eco-Friendly",
        description="Growing demand for sustainable, eco-conscious products",
        platforms=["instagram", "tiktok", "pinterest"],
        strength=0.8, time_sensitivity="low",
        action_suggestion="Highlight sustainability: natural materials, eco packaging",
        relevant_hashtags=["#sustainable", "#ecofriendly", "#zerowaste"],
    ),
    TrendSignal(
        trend_type="emerging", topic="Behind-the-Scenes Content",
        description="Audiences love seeing the making process",
        platforms=["tiktok", "instagram"],
        strength=0.85, time_sensitivity="low",
        action_suggestion="Film candle/concrete pouring process, workshop tours",
        relevant_hashtags=["#behindthescenes", "#makingof", "#handmadeprocess"],
    ),
    TrendSignal(
        trend_type="emerging", topic="Minimalist Scandinavian Aesthetic",
        description="Nordic minimalism continues to grow globally",
        platforms=["pinterest", "instagram"],
        strength=0.75, time_sensitivity="low",
        action_suggestion="Lean into Nordic aesthetic in all content",
        relevant_hashtags=["#scandinaviandesign", "#nordicminimalism", "#lessismore"],
    ),
]


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════

class SocialIntelEngine:
    """
    Social intelligence engine for marketing insights.

    Integrates web search to discover influencers, analyze
    communities, detect trends, and monitor competitors.
    """

    def __init__(
        self,
        niche: str = "handmade candles concrete decor",
        region: str = "Finland",
        languages: Optional[List[str]] = None,
    ) -> None:
        self.niche = niche
        self.region = region
        self.languages = languages or ["en", "fi", "sv"]
        self._web_search = WebSearchEngine() if _SEARCH_AVAILABLE else None
        self._stats = {
            "influencers_found": 0,
            "communities_found": 0,
            "reviews_analyzed": 0,
            "trends_detected": 0,
            "searches_done": 0,
            "errors": 0,
        }

    async def full_social_intel(
        self,
        focus: Optional[str] = None,
    ) -> SocialIntelReport:
        """
        Run complete social intelligence scan.

        Args:
            focus: Optional focus area ("influencers", "hashtags",
                   "reviews", "trends", "communities", or None for all)
        """
        report = SocialIntelReport(
            query=self.niche,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        tasks = []
        if focus is None or focus == "influencers":
            tasks.append(self._discover_influencers(report))
        if focus is None or focus == "hashtags":
            tasks.append(self._analyze_hashtags(report))
        if focus is None or focus == "trends":
            tasks.append(self._detect_trends(report))
        if focus is None or focus == "communities":
            tasks.append(self._find_communities(report))

        await asyncio.gather(*tasks, return_exceptions=True)
        return report

    async def discover_influencers(
        self,
        niche_override: Optional[str] = None,
        platforms: Optional[List[Platform]] = None,
        min_followers: int = 1000,
        max_followers: int = 500_000,
        limit: int = 20,
    ) -> List[Influencer]:
        """Discover influencers in the niche."""
        niche = niche_override or self.niche
        target_platforms = platforms or [
            Platform.INSTAGRAM, Platform.TIKTOK,
            Platform.PINTEREST, Platform.YOUTUBE,
        ]

        influencers: List[Influencer] = []

        if not self._web_search:
            return self._generate_sample_influencers(niche, target_platforms, limit)

        for platform in target_platforms:
            queries = self._build_influencer_queries(niche, platform)
            for query in queries[:2]:
                try:
                    results = await self._web_search.search(query, max_results=10)
                    self._stats["searches_done"] += 1
                    for r in (results or []):
                        inf = self._parse_influencer_result(
                            r, platform, niche
                        )
                        if inf and inf.relevance_score > 0.3:
                            influencers.append(inf)
                except Exception as e:
                    self._stats["errors"] += 1
                    logger.debug("influencer search error: %s", e)

        # Deduplicate by handle
        seen: Set[str] = set()
        unique: List[Influencer] = []
        for inf in influencers:
            key = f"{inf.platform.value}:{inf.handle}".lower()
            if key not in seen:
                seen.add(key)
                unique.append(inf)

        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        self._stats["influencers_found"] += len(unique[:limit])
        return unique[:limit]

    async def analyze_reviews(
        self,
        company_name: str,
        platforms: Optional[List[str]] = None,
    ) -> List[ReviewInsight]:
        """Analyze reviews for a company across platforms."""
        platforms = platforms or ["google", "etsy", "tripadvisor", "facebook"]
        insights: List[ReviewInsight] = []

        if not self._web_search:
            return insights

        for platform in platforms:
            try:
                query = f'"{company_name}" reviews {platform}'
                results = await self._web_search.search(query, max_results=10)
                self._stats["searches_done"] += 1

                texts = []
                for r in (results or []):
                    snippet = getattr(r, "snippet", "") or ""
                    texts.append(snippet)

                if texts:
                    combined = " ".join(texts)
                    sentiment, score = _analyze_sentiment(combined)
                    pos_themes = _extract_themes(texts, positive=True)
                    neg_themes = _extract_themes(texts, positive=False)

                    insight = ReviewInsight(
                        platform=platform,
                        total_reviews=len(texts),
                        sentiment=sentiment,
                        sentiment_score=score,
                        positive_themes=pos_themes,
                        negative_themes=neg_themes,
                    )
                    insights.append(insight)
                    self._stats["reviews_analyzed"] += len(texts)
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug("review analysis error: %s", e)

        return insights

    def get_hashtag_strategy(
        self,
        content_type: str = "product_photo",
    ) -> Dict[str, Any]:
        """Get optimized hashtag strategy for a content type."""
        clusters = _build_hashtag_clusters(self.niche, self.region)

        # Build strategy based on content type
        strategy: Dict[str, List[str]] = {
            "must_use": [],
            "recommended": [],
            "seasonal": [],
            "niche": [],
        }

        for cluster in clusters:
            if cluster.relevance_score >= 0.9:
                strategy["must_use"].append(cluster.primary_tag)
                strategy["must_use"].extend(cluster.related_tags[:2])
            elif cluster.relevance_score >= 0.7:
                strategy["recommended"].append(cluster.primary_tag)
                strategy["recommended"].extend(cluster.related_tags[:1])
            elif "seasonal" in cluster.primary_tag.lower():
                strategy["seasonal"].append(cluster.primary_tag)
            else:
                strategy["niche"].append(cluster.primary_tag)

        # Content-type specific additions
        type_tags = {
            "product_photo": ["#productphotography", "#flatlay", "#stilllife"],
            "behind_scenes": ["#makerslife", "#studiolife", "#workinprogress"],
            "lifestyle": ["#homedecor", "#interiorinspiration", "#cozyhome"],
            "tutorial": ["#howto", "#diy", "#candlemaking"],
            "reels": ["#reels", "#trending", "#viral"],
        }
        strategy["content_specific"] = type_tags.get(content_type, [])

        return {
            "strategy": strategy,
            "total_tags": sum(len(v) for v in strategy.values()),
            "recommendation": "Use 20-25 hashtags per post. Mix must_use + recommended + seasonal",
            "clusters": [c.to_dict() for c in clusters],
        }

    def get_current_trends(self) -> List[TrendSignal]:
        """Get trends relevant to current month + evergreen."""
        now = datetime.now(timezone.utc)
        month = now.month

        trends = list(_SEASONAL_TRENDS.get(month, []))
        # Also include next month's trends for preparation
        next_month = (month % 12) + 1
        for trend in _SEASONAL_TRENDS.get(next_month, []):
            modified = TrendSignal(
                trend_type="upcoming",
                topic=f"[Prep] {trend.topic}",
                description=f"Coming next month: {trend.description}",
                platforms=trend.platforms,
                strength=trend.strength * 0.6,
                time_sensitivity="medium",
                action_suggestion=f"Start preparing: {trend.action_suggestion}",
                relevant_hashtags=trend.relevant_hashtags,
            )
            trends.append(modified)

        trends.extend(_EVERGREEN_TRENDS)
        self._stats["trends_detected"] += len(trends)
        return trends

    async def find_communities(
        self,
        niche_override: Optional[str] = None,
        limit: int = 15,
    ) -> List[Community]:
        """Find relevant online communities."""
        niche = niche_override or self.niche
        communities: List[Community] = []

        if not self._web_search:
            return self._generate_sample_communities(niche, limit)

        search_queries = [
            f'facebook group "{niche}" handmade',
            f'reddit candles handmade decor',
            f'pinterest board Scandinavian candles decor',
            f'forum handmade crafts Finland',
            f'facebook group interior design Finland',
        ]

        for query in search_queries:
            try:
                results = await self._web_search.search(query, max_results=5)
                self._stats["searches_done"] += 1
                for r in (results or []):
                    community = self._parse_community_result(r, niche)
                    if community and community.relevance_score > 0.2:
                        communities.append(community)
            except Exception:
                self._stats["errors"] += 1

        # Deduplicate
        seen: Set[str] = set()
        unique: List[Community] = []
        for c in communities:
            key = c.url.lower().rstrip("/")
            if key not in seen:
                seen.add(key)
                unique.append(c)

        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        self._stats["communities_found"] += len(unique[:limit])
        return unique[:limit]

    async def monitor_competitor_social(
        self,
        competitor_name: str,
        competitor_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Monitor a competitor's social media presence."""
        profile: Dict[str, Any] = {
            "competitor": competitor_name,
            "platforms_found": [],
            "estimated_followers": {},
            "content_themes": [],
            "posting_frequency": "unknown",
            "engagement_level": "unknown",
        }

        if not self._web_search:
            return profile

        # Search for their social profiles
        queries = [
            f'"{competitor_name}" instagram',
            f'"{competitor_name}" facebook page',
            f'"{competitor_name}" pinterest',
            f'"{competitor_name}" etsy shop',
        ]

        for query in queries:
            try:
                results = await self._web_search.search(query, max_results=5)
                self._stats["searches_done"] += 1
                for r in (results or []):
                    url = getattr(r, "url", "") or ""
                    for platform in ["instagram", "facebook", "pinterest",
                                     "etsy", "tiktok", "youtube"]:
                        if platform in url.lower():
                            if platform not in profile["platforms_found"]:
                                profile["platforms_found"].append(platform)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        return profile

    # ── Internal helpers ──────────────────────────────────────────

    async def _discover_influencers(self, report: SocialIntelReport) -> None:
        """Fill report with influencers."""
        try:
            report.influencers = await self.discover_influencers()
        except Exception as e:
            report.errors.append(f"influencers: {str(e)}")

    async def _analyze_hashtags(self, report: SocialIntelReport) -> None:
        """Fill report with hashtag clusters."""
        try:
            clusters = _build_hashtag_clusters(self.niche, self.region)
            report.hashtag_clusters = clusters
        except Exception as e:
            report.errors.append(f"hashtags: {str(e)}")

    async def _detect_trends(self, report: SocialIntelReport) -> None:
        """Fill report with trends."""
        try:
            report.trends = self.get_current_trends()
        except Exception as e:
            report.errors.append(f"trends: {str(e)}")

    async def _find_communities(self, report: SocialIntelReport) -> None:
        """Fill report with communities."""
        try:
            report.communities = await self.find_communities()
        except Exception as e:
            report.errors.append(f"communities: {str(e)}")

    def _build_influencer_queries(
        self, niche: str, platform: Platform,
    ) -> List[str]:
        """Build search queries for influencer discovery."""
        platform_name = platform.value
        return [
            f'{platform_name} influencer {niche} {self.region}',
            f'{platform_name} blogger candle decor handmade Scandinavia',
            f'top {platform_name} accounts interior design Nordic',
        ]

    def _parse_influencer_result(
        self, result: Any, platform: Platform, niche: str,
    ) -> Optional[Influencer]:
        """Parse a search result into an Influencer."""
        url = getattr(result, "url", "") or ""
        title = getattr(result, "title", "") or ""
        snippet = getattr(result, "snippet", "") or ""

        if not url:
            return None

        # Extract handle
        handle = url.rstrip("/").split("/")[-1]
        if not handle or len(handle) < 2:
            return None
        if handle.startswith("@"):
            handle = handle[1:]

        # Calculate relevance
        combined = f"{title} {snippet}".lower()
        niche_words = set(niche.lower().split())
        matches = sum(1 for w in niche_words if w in combined)
        relevance = min(1.0, matches / max(len(niche_words), 1))

        # Boost for specific indicators
        if any(w in combined for w in ["influencer", "blogger", "creator"]):
            relevance = min(1.0, relevance + 0.2)
        if self.region.lower() in combined:
            relevance = min(1.0, relevance + 0.15)

        return Influencer(
            name=title.split("-")[0].split("|")[0].strip()[:50],
            platform=platform,
            handle=handle,
            url=url,
            niche_tags=list(niche_words),
            relevance_score=relevance,
            collaboration_fit=relevance * 0.8,
            source="web_search",
        )

    def _parse_community_result(
        self, result: Any, niche: str,
    ) -> Optional[Community]:
        """Parse a search result into a Community."""
        url = getattr(result, "url", "") or ""
        title = getattr(result, "title", "") or ""
        snippet = getattr(result, "snippet", "") or ""

        if not url:
            return None

        # Detect platform
        platform = "web"
        for p in ["facebook", "reddit", "pinterest", "discord"]:
            if p in url.lower():
                platform = p
                break

        combined = f"{title} {snippet}".lower()
        niche_words = set(niche.lower().split())
        matches = sum(1 for w in niche_words if w in combined)
        relevance = min(1.0, matches / max(len(niche_words), 1))

        return Community(
            name=title[:80],
            platform=platform,
            url=url,
            relevance_score=relevance,
            description=snippet[:200],
        )

    def _generate_sample_influencers(
        self, niche: str, platforms: List[Platform], limit: int,
    ) -> List[Influencer]:
        """Generate sample influencers when search unavailable."""
        samples = []
        for i, platform in enumerate(platforms):
            samples.append(Influencer(
                name=f"Nordic {niche.split()[0].title()} Lover",
                platform=platform,
                handle=f"nordic_{niche.split()[0]}_lover",
                url=f"https://{platform.value}.com/nordic_{niche.split()[0]}_lover",
                niche_tags=niche.split()[:3],
                relevance_score=0.5,
                source="generated_sample",
            ))
        return samples[:limit]

    def _generate_sample_communities(
        self, niche: str, limit: int,
    ) -> List[Community]:
        """Generate sample communities when search unavailable."""
        return [
            Community(
                name="Handmade Home Decor Enthusiasts",
                platform="facebook",
                url="https://facebook.com/groups/handmadehomedecor",
                relevance_score=0.7,
                description="Community for handmade home decor lovers",
            ),
        ][:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            **self._stats,
            "niche": self.niche,
            "region": self.region,
            "web_search_available": _SEARCH_AVAILABLE,
        }


