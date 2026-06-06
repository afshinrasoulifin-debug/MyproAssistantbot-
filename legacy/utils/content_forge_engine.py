
from __future__ import annotations
"""
utils/content_forge_engine.py — Content Forge Engine  v1.0-OMEGA
═══════════════════════════════════════════════════════════════════════
AI-powered multi-language content generation factory.

Capabilities
────────────
  • Multi-Language     — EN, FI, SV, DE, FR content generation
  • Platform Adapt     — format for each platform's requirements
  • SEO Optimization   — keyword integration, meta descriptions
  • A/B Variants       — generate test variants with hypothesis
  • Email Personalize  — deep personalization for outreach
  • Seasonal Calendar  — content calendar with seasonal events
  • Brand Voice        — consistent tone across all output
  • Product Describe   — generate product descriptions per platform

Author: Viktor AI  |  Arki Engine OMEGA
"""


import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════════════

class ContentType(Enum):
    EMAIL_B2B = "email_b2b"
    EMAIL_B2C = "email_b2c"
    PRODUCT_DESC = "product_description"
    SOCIAL_POST = "social_post"
    BLOG_POST = "blog_post"
    AD_COPY = "ad_copy"
    LISTING = "listing"
    NEWSLETTER = "newsletter"
    PRESS_RELEASE = "press_release"


class ContentLanguage(Enum):
    EN = "en"
    FI = "fi"
    SV = "sv"
    DE = "de"
    FR = "fr"


class BrandTone(Enum):
    PROFESSIONAL = "professional"
    WARM = "warm"
    LUXURIOUS = "luxurious"
    FRIENDLY = "friendly"
    MINIMALIST = "minimalist"
    ARTISAN = "artisan"


@dataclass
class BrandVoice:
    """Brand voice configuration."""
    company_name: str = "ArkiObjects"
    tagline: str = "Handcrafted Concrete & Stone — Nordic Minimalism"
    tone: BrandTone = BrandTone.ARTISAN
    values: List[str] = field(default_factory=lambda: [
        "handmade", "sustainable", "Nordic design",
        "minimalist", "unique", "quality craftsmanship",
    ])
    avoid_words: List[str] = field(default_factory=lambda: [
        "cheap", "mass-produced", "factory", "discount",
        "halpa", "teollinen",
    ])
    key_phrases: Dict[str, List[str]] = field(default_factory=lambda: {
        "en": ["handcrafted with care", "Nordic minimalism",
               "each piece is unique", "sustainable materials"],
        "fi": ["käsin valmistettu huolella", "pohjoismainen minimalismi",
               "jokainen tuote on ainutlaatuinen", "kestävät materiaalit"],
        "sv": ["handgjord med omsorg", "nordisk minimalism",
               "varje stycke är unikt", "hållbara material"],
        "de": ["mit Sorgfalt handgefertigt", "nordischer Minimalismus",
               "jedes Stück ist einzigartig", "nachhaltige Materialien"],
        "fr": ["fabriqué à la main avec soin", "minimalisme nordique",
               "chaque pièce est unique", "matériaux durables"],
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name, "tagline": self.tagline,
            "tone": self.tone.value, "values": self.values,
            "avoid_words": self.avoid_words,
        }


@dataclass
class ContentPiece:
    """Generated content piece."""
    content_type: ContentType
    language: ContentLanguage
    subject: str = ""
    body: str = ""
    call_to_action: str = ""
    hashtags: List[str] = field(default_factory=list)
    seo_keywords: List[str] = field(default_factory=list)
    meta_description: str = ""
    variant_id: str = ""
    variant_hypothesis: str = ""
    personalization_tokens: Dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    estimated_read_time: float = 0.0  # minutes
    platform_formatted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type.value,
            "language": self.language.value,
            "subject": self.subject, "body": self.body,
            "call_to_action": self.call_to_action,
            "hashtags": self.hashtags,
            "seo_keywords": self.seo_keywords,
            "meta_description": self.meta_description,
            "variant_id": self.variant_id,
            "variant_hypothesis": self.variant_hypothesis,
            "personalization_tokens": self.personalization_tokens,
            "word_count": self.word_count,
            "estimated_read_time": self.estimated_read_time,
        }


@dataclass
class ABTestPlan:
    """A/B test configuration."""
    test_name: str
    variants: List[ContentPiece] = field(default_factory=list)
    metric: str = "open_rate"  # open_rate, click_rate, reply_rate
    hypothesis: str = ""
    sample_size: int = 100
    duration_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "variants": [v.to_dict() for v in self.variants],
            "metric": self.metric, "hypothesis": self.hypothesis,
            "sample_size": self.sample_size,
            "duration_days": self.duration_days,
        }


@dataclass
class ContentCalendarEntry:
    """Single entry in content calendar."""
    date: str
    content_type: str
    topic: str
    platform: str
    language: str
    status: str = "planned"  # planned, draft, ready, published
    notes: str = ""
    hashtags: List[str] = field(default_factory=list)
    seasonal_tie: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date, "content_type": self.content_type,
            "topic": self.topic, "platform": self.platform,
            "language": self.language, "status": self.status_code,
            "notes": self.notes, "hashtags": self.hashtags,
            "seasonal_tie": self.seasonal_tie,
        }


# ═══════════════════════════════════════════════════════════════════════
#  Templates — Multi-Language
# ═══════════════════════════════════════════════════════════════════════

_B2B_EMAIL_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "hotel_intro": (
            "Subject: Handcrafted Decor for {company_name} — Unique Nordic Pieces\n\n"
            "Dear {contact_name},\n\n"
            "I'm reaching out from ArkiObjects, a Finnish artisan studio "
            "specializing in handcrafted concrete and stone decorative pieces.\n\n"
            "Our minimalist Scandinavian designs have been featured in boutique "
            "hotels and luxury spaces across the Nordics. Each piece is individually "
            "hand-poured and finished, making them conversation starters for your guests.\n\n"
            "I'd love to share our wholesale catalog — would you have a few minutes "
            "this week for a quick conversation?\n\n"
            "Warm regards,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Finland\n"
            "{website_url}"
        ),
        "restaurant_intro": (
            "Subject: Artisan Table Pieces for {company_name}\n\n"
            "Dear {contact_name},\n\n"
            "Beautiful dining experiences start with beautiful details. "
            "At ArkiObjects, we handcraft concrete candle holders and decorative "
            "pieces that add a unique Nordic touch to any table setting.\n\n"
            "Our pieces are durable, easy to clean, and each one is completely unique. "
            "Many restaurants in Finland already use our items as distinctive "
            "table centerpieces.\n\n"
            "May I send you our restaurant collection catalog?\n\n"
            "Best,\n"
            "{sender_name}\n"
            "ArkiObjects"
        ),
        "spa_intro": (
            "Subject: Create Tranquility with Handcrafted Nordic Pieces — {company_name}\n\n"
            "Dear {contact_name},\n\n"
            "At ArkiObjects, we believe that true relaxation comes from "
            "carefully curated spaces. Our handcrafted concrete and stone "
            "candle holders create the perfect ambiance for wellness environments.\n\n"
            "Each piece embodies the calm simplicity of Scandinavian design. "
            "They're designed to complement any spa or wellness space "
            "with a touch of Nordic elegance.\n\n"
            "Would you be interested in seeing our wellness collection?\n\n"
            "Sincerely,\n"
            "{sender_name}\n"
            "ArkiObjects | Finnish Artisan Design"
        ),
        "generic_intro": (
            "Subject: Unique Handcrafted Decor from Finland — {company_name}\n\n"
            "Dear {contact_name},\n\n"
            "I'm writing from ArkiObjects, a Finnish studio creating handcrafted "
            "concrete and stone decorative pieces with a minimalist Nordic aesthetic.\n\n"
            "Our products range from candle holders to sculptural pieces, "
            "each one hand-poured and individually finished. They make unique "
            "additions to any space seeking that Scandinavian touch.\n\n"
            "I'd love to share our catalog with you. Would that be of interest?\n\n"
            "Kind regards,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Finland"
        ),
    },
    "fi": {
        "hotel_intro": (
            "Aihe: Käsintehtyä pohjoismaista sisustusta {company_name} — ainutlaatuisia kappaleita\n\n"
            "Hyvä {contact_name},\n\n"
            "Olen yhteydessä ArkiObjectsilta, suomalaisesta käsityöpajasta, "
            "joka on erikoistunut käsinvalettuihin betoni- ja kivisiin sisustustuotteisiin.\n\n"
            "Minimalistiset pohjoismaiset muotoilumme ovat löytäneet tiensä "
            "boutique-hotelleihin ja luksustiloihin ympäri Pohjoismaita. "
            "Jokainen kappale on yksilöllisesti käsin valettu ja viimeistelty.\n\n"
            "Haluaisin mielelläni jakaa tukkukatalogin kanssanne — "
            "olisiko teillä hetki aikaa tällä viikolla?\n\n"
            "Ystävällisin terveisin,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Suomi\n"
            "{website_url}"
        ),
        "generic_intro": (
            "Aihe: Käsintehtyjä sisustustuotteita Suomesta — {company_name}\n\n"
            "Hyvä {contact_name},\n\n"
            "Kirjoitan ArkiObjectsilta, suomalaiselta studiolta, joka luo "
            "käsintehtyjä betoni- ja kivi-sisustustuotteita "
            "minimalistisella pohjoismaisella estetiikalla.\n\n"
            "Tuotteemme vaihtelevat kynttilänpidikkeistä veistoksellisiin kappaleisiin, "
            "ja jokainen on käsin valettu ja yksilöllisesti viimeistelty.\n\n"
            "Haluaisin mielelläni jakaa katalogin kanssanne. Kiinnostaisiko?\n\n"
            "Terveisin,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Suomi"
        ),
    },
    "sv": {
        "generic_intro": (
            "Ämne: Unika handgjorda dekorationer från Finland — {company_name}\n\n"
            "Bästa {contact_name},\n\n"
            "Jag skriver från ArkiObjects, en finsk ateljé som skapar "
            "handgjorda dekorativa föremål i betong och sten med en "
            "minimalistisk nordisk estetik.\n\n"
            "Varje stycke är handgjutet och individuellt bearbetat. "
            "De ger en unik skandinavisk touch till alla utrymmen.\n\n"
            "Jag skulle gärna dela vår katalog med er. Är det intressant?\n\n"
            "Med vänlig hälsning,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Finland"
        ),
    },
    "de": {
        "generic_intro": (
            "Betreff: Einzigartige handgefertigte Dekoration aus Finnland — {company_name}\n\n"
            "Sehr geehrte(r) {contact_name},\n\n"
            "Ich schreibe von ArkiObjects, einem finnischen Atelier für "
            "handgefertigte dekorative Stücke aus Beton und Stein im "
            "minimalistischen nordischen Stil.\n\n"
            "Jedes Stück wird individuell von Hand gegossen und fertiggestellt. "
            "Sie verleihen jedem Raum einen einzigartigen skandinavischen Touch.\n\n"
            "Gerne teile ich unseren Katalog mit Ihnen. Hätten Sie Interesse?\n\n"
            "Mit freundlichen Grüßen,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Finnland"
        ),
    },
    "fr": {
        "generic_intro": (
            "Objet: Décoration artisanale unique de Finlande — {company_name}\n\n"
            "Cher(e) {contact_name},\n\n"
            "Je vous écris d'ArkiObjects, un atelier finlandais créant "
            "des pièces décoratives artisanales en béton et pierre dans "
            "un style nordique minimaliste.\n\n"
            "Chaque pièce est coulée à la main et individuellement finalisée. "
            "Elles ajoutent une touche scandinave unique à tout espace.\n\n"
            "Je serais ravi de partager notre catalogue avec vous. Intéressé(e) ?\n\n"
            "Cordialement,\n"
            "{sender_name}\n"
            "ArkiObjects | Pieksämäki, Finlande"
        ),
    },
}

# Product description templates by platform
_PRODUCT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "etsy": {
        "en": (
            "{product_name}\n\n"
            "✦ {short_description}\n\n"
            "Each piece is individually handcrafted in our Finnish studio "
            "using premium concrete and natural stone elements. No two pieces "
            "are exactly alike — that's the beauty of handmade.\n\n"
            "DETAILS:\n"
            "• Material: {material}\n"
            "• Dimensions: {dimensions}\n"
            "• Weight: {weight}\n"
            "• Color: {color}\n\n"
            "CARE:\n"
            "• Wipe clean with a damp cloth\n"
            "• Avoid harsh chemicals\n"
            "• Use on a heat-resistant surface\n\n"
            "SHIPPING:\n"
            "• Ships from Pieksämäki, Finland\n"
            "• Carefully packaged for safe delivery\n"
            "• Processing time: {processing_time}\n\n"
            "♥ Made with love in Finland\n"
            "#handmade #concrete #candle #nordicdesign #scandinavian #minimalist"
        ),
    },
    "tori": {
        "fi": (
            "{product_name}\n\n"
            "{short_description}\n\n"
            "Jokainen kappale on käsin valettu studiollani Pieksämäellä. "
            "Yhtään täysin samanlaista kappaletta ei ole — "
            "se on käsityön kauneus.\n\n"
            "Tiedot:\n"
            "• Materiaali: {material}\n"
            "• Mitat: {dimensions}\n"
            "• Paino: {weight}\n"
            "• Väri: {color}\n\n"
            "Hinta: {price}\n"
            "Nouto Pieksämäki tai postitus (+{shipping_cost})\n\n"
            "Käsintehty Suomessa ♥"
        ),
    },
}

# Social post templates
_SOCIAL_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "instagram": {
        "en": [
            "Every piece tells a story. 🕯️\n\n"
            "Handcrafted in our Finnish studio, this {product_type} "
            "brings Nordic minimalism to your space.\n\n"
            "Each one is unique — just like your home.\n\n"
            "{hashtags}",

            "The art of imperfection. ✨\n\n"
            "No two pieces are the same. That's what makes "
            "handmade special.\n\n"
            "Crafted with care in Pieksämäki, Finland.\n\n"
            "{hashtags}",
        ],
        "fi": [
            "Jokainen kappale kertoo tarinan. 🕯️\n\n"
            "Käsin valmistettu studiollani Pieksämäellä.\n"
            "Jokainen on ainutlaatuinen — aivan kuten kotisi.\n\n"
            "{hashtags}",
        ],
    },
    "pinterest": {
        "en": [
            "{product_name} — Handcrafted Nordic {product_type} | "
            "Minimalist Home Decor | Finnish Design | "
            "Concrete Candle Holder | Sustainable & Unique",
        ],
    },
}

# SEO keywords by language
_SEO_KEYWORDS: Dict[str, List[str]] = {
    "en": [
        "handmade candles Finland", "concrete candle holder",
        "Nordic minimalist decor", "Scandinavian home accessories",
        "artisan candle holder", "unique home decor",
        "handcrafted stone decor", "Finnish design",
        "minimalist candle", "concrete home decor",
    ],
    "fi": [
        "käsintehty kynttilänjalka", "betonikynttilänjalka",
        "pohjoismainen sisustus", "käsintehty sisustus",
        "suomalainen design", "minimalistinen sisustus",
        "käsinvalettu betoni", "kiviset sisustustuotteet",
    ],
}

# Seasonal content calendar events
_SEASONAL_EVENTS: Dict[int, List[Dict[str, str]]] = {
    1: [{"name": "New Year", "focus": "fresh_start_decor"}],
    2: [{"name": "Valentine's Day", "focus": "romantic_gifts"}],
    3: [{"name": "International Women's Day", "focus": "gifts_for_her"}],
    4: [{"name": "Easter", "focus": "spring_decor"}],
    5: [{"name": "Mother's Day", "focus": "mother_gifts"},
        {"name": "Helsinki Design Week Prep", "focus": "design_showcase"}],
    6: [{"name": "Juhannus", "focus": "midsummer_decor"},
        {"name": "Wedding Season", "focus": "wedding_decor"}],
    7: [{"name": "Summer Sale", "focus": "outdoor_living"}],
    8: [{"name": "Back to Cozy", "focus": "autumn_prep"}],
    9: [{"name": "Helsinki Design Week", "focus": "design_showcase"},
        {"name": "Autumn Markets", "focus": "market_prep"}],
    10: [{"name": "Halloween", "focus": "dark_aesthetics"}],
    11: [{"name": "Black Friday", "focus": "sales_campaign"},
         {"name": "Christmas Prep", "focus": "gift_guides"}],
    12: [{"name": "Christmas", "focus": "holiday_gifts"},
         {"name": "Christmas Markets", "focus": "market_presence"},
         {"name": "New Year Eve", "focus": "celebration_decor"}],
}


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════

class ContentForgeEngine:
    """
    Content generation factory — multi-language, multi-platform,
    SEO-optimized, brand-consistent content.
    """

    def __init__(
        self,
        brand_voice: Optional[BrandVoice] = None,
        ai_client: Any = None,
    ) -> None:
        self.brand = brand_voice or BrandVoice()
        self._ai_client = ai_client
        self._stats = {
            "emails_generated": 0,
            "social_posts_generated": 0,
            "product_descs_generated": 0,
            "ab_tests_created": 0,
            "calendar_entries_created": 0,
            "errors": 0,
        }

    async def generate_b2b_email(
        self,
        prospect: Dict[str, Any],
        language: ContentLanguage = ContentLanguage.EN,
        industry: str = "generic",
        followup_number: int = 0,
        sender_name: str = "ArkiObjects Team",
    ) -> ContentPiece:
        """
        Generate a personalized B2B outreach email.

        Args:
            prospect: {"name": ..., "company": ..., "title": ..., "domain": ...}
            language: Target language
            industry: hotel, restaurant, spa, gallery, generic
            followup_number: 0=first contact, 1+=followup
            sender_name: Sender name

        Returns:
            ContentPiece with personalized email
        """
        lang = language.value
        templates = _B2B_EMAIL_TEMPLATES.get(lang, _B2B_EMAIL_TEMPLATES["en"])

        # Select template by industry
        template_key = f"{industry}_intro" if f"{industry}_intro" in templates else "generic_intro"
        template = templates.get(template_key, templates.get("generic_intro", ""))

        # Personalize
        tokens = {
            "company_name": prospect.get("company", "your company"),
            "contact_name": prospect.get("name", "Sir/Madam"),
            "sender_name": sender_name,
            "website_url": f"https://arkiobjects.fi",
        }

        body = template
        for key, value in tokens.items():
            body = body.replace(f"{{{key}}}", value)

        # Followup modifications
        if followup_number > 0:
            body = self._modify_for_followup(body, followup_number, lang)

        # Extract subject from body
        subject = ""
        if body.startswith("Subject:") or body.startswith("Aihe:") or body.startswith("Ämne:") or body.startswith("Betreff:") or body.startswith("Objet:"):
            lines = body.split("\n", 1)
            subject = lines[0].split(":", 1)[1].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

        piece = ContentPiece(
            content_type=ContentType.EMAIL_B2B,
            language=language,
            subject=subject,
            body=body,
            call_to_action="Reply to schedule a quick call or request catalog",
            personalization_tokens=tokens,
            word_count=len(body.split()),
            estimated_read_time=len(body.split()) / 200,
        )

        self._stats["emails_generated"] += 1
        return piece

    async def generate_product_description(
        self,
        product: Dict[str, Any],
        platform: str = "etsy",
        language: ContentLanguage = ContentLanguage.EN,
    ) -> ContentPiece:
        """Generate a product description for a specific platform."""
        lang = language.value
        platform_templates = _PRODUCT_TEMPLATES.get(platform, {})
        template = platform_templates.get(lang)

        if not template:
            # Fallback to English Etsy template
            template = _PRODUCT_TEMPLATES.get("etsy", {}).get("en", "")

        tokens = {
            "product_name": product.get("name", "Handcrafted Piece"),
            "short_description": product.get("description", "A unique handcrafted piece"),
            "material": product.get("material", "Premium concrete"),
            "dimensions": product.get("dimensions", "varies"),
            "weight": product.get("weight", "varies"),
            "color": product.get("color", "Natural concrete gray"),
            "price": product.get("price", ""),
            "processing_time": product.get("processing_time", "3-5 business days"),
            "shipping_cost": product.get("shipping_cost", "varies"),
        }

        body = template
        for key, value in tokens.items():
            body = body.replace(f"{{{key}}}", str(value))

        seo_kw = _SEO_KEYWORDS.get(lang, _SEO_KEYWORDS["en"])[:5]

        piece = ContentPiece(
            content_type=ContentType.PRODUCT_DESC,
            language=language,
            subject=tokens["product_name"],
            body=body,
            seo_keywords=seo_kw,
            personalization_tokens=tokens,
            word_count=len(body.split()),
            platform_formatted=True,
        )

        self._stats["product_descs_generated"] += 1
        return piece

    async def generate_social_post(
        self,
        platform: str = "instagram",
        language: ContentLanguage = ContentLanguage.EN,
        product_type: str = "candle holder",
        hashtags: Optional[List[str]] = None,
        variant_index: int = 0,
    ) -> ContentPiece:
        """Generate a social media post."""
        lang = language.value
        platform_templates = _SOCIAL_TEMPLATES.get(platform, {})
        templates_list = platform_templates.get(lang, [])

        if not templates_list:
            templates_list = _SOCIAL_TEMPLATES.get("instagram", {}).get("en", [""])

        template = templates_list[variant_index % len(templates_list)]

        ht = hashtags or [
            "#handmadecandles", "#nordicdesign", "#concretecandles",
            "#scandinaviandesign", "#minimalist", "#homedecor",
            "#finnishdesign", "#artisan", "#handcrafted",
        ]

        body = template.replace("{product_type}", product_type)
        body = body.replace("{product_name}", f"Nordic {product_type.title()}")
        body = body.replace("{hashtags}", " ".join(ht[:15]))

        piece = ContentPiece(
            content_type=ContentType.SOCIAL_POST,
            language=language,
            body=body,
            hashtags=ht,
            word_count=len(body.split()),
            platform_formatted=True,
            variant_id=f"v{variant_index}",
        )

        self._stats["social_posts_generated"] += 1
        return piece

    async def generate_ab_variants(
        self,
        content_type: ContentType,
        base_params: Dict[str, Any],
        num_variants: int = 2,
        test_variable: str = "subject_line",
    ) -> ABTestPlan:
        """Generate A/B test variants."""
        variants: List[ContentPiece] = []

        if content_type == ContentType.EMAIL_B2B:
            for i in range(num_variants):
                prospect = dict(base_params.get("prospect", {}))
                piece = await self.generate_b2b_email(
                    prospect,
                    language=ContentLanguage(base_params.get("language", "en")),
                    industry=base_params.get("industry", "generic"),
                )
                # Modify for variant
                if test_variable == "subject_line" and i > 0:
                    piece.subject = self._vary_subject(piece.subject, i)
                elif test_variable == "cta" and i > 0:
                    piece.call_to_action = self._vary_cta(piece.call_to_action, i)

                piece.variant_id = f"variant_{chr(65 + i)}"
                piece.variant_hypothesis = self._generate_hypothesis(test_variable, i)
                variants.append(piece)
        else:
            for i in range(num_variants):
                piece = await self.generate_social_post(
                    variant_index=i,
                    language=ContentLanguage(base_params.get("language", "en")),
                )
                piece.variant_id = f"variant_{chr(65 + i)}"
                variants.append(piece)

        plan = ABTestPlan(
            test_name=f"AB_{content_type.value}_{test_variable}",
            variants=variants,
            metric="open_rate" if content_type == ContentType.EMAIL_B2B else "engagement_rate",
            hypothesis=f"Testing {test_variable} impact on {content_type.value}",
            sample_size=base_params.get("sample_size", 100),
        )

        self._stats["ab_tests_created"] += 1
        return plan

    def generate_content_calendar(
        self,
        weeks_ahead: int = 4,
        posts_per_week: int = 3,
        languages: Optional[List[ContentLanguage]] = None,
    ) -> List[ContentCalendarEntry]:
        """Generate a content calendar for upcoming weeks."""
        languages = languages or [ContentLanguage.EN, ContentLanguage.FI]
        now = datetime.now(timezone.utc)
        entries: List[ContentCalendarEntry] = []

        platforms = ["instagram", "pinterest", "facebook"]
        content_types = ["product_photo", "behind_scenes", "lifestyle", "educational"]

        for week in range(weeks_ahead):
            week_start = now + timedelta(weeks=week)
            for post_idx in range(posts_per_week):
                post_date = week_start + timedelta(days=post_idx * 2 + 1)
                month = post_date.month

                # Get seasonal events
                seasonal = _SEASONAL_EVENTS.get(month, [])
                seasonal_tie = seasonal[0]["name"] if seasonal else ""

                lang = languages[post_idx % len(languages)]
                platform = platforms[post_idx % len(platforms)]
                ct = content_types[post_idx % len(content_types)]

                topic = self._generate_topic(ct, month, seasonal_tie)

                entry = ContentCalendarEntry(
                    date=post_date.strftime("%Y-%m-%d"),
                    content_type=ct,
                    topic=topic,
                    platform=platform,
                    language=lang.value,
                    seasonal_tie=seasonal_tie,
                    hashtags=self._get_relevant_hashtags(ct, lang.value)[:10],
                )
                entries.append(entry)

        self._stats["calendar_entries_created"] += len(entries)
        return entries

    def get_seo_keywords(
        self,
        language: ContentLanguage = ContentLanguage.EN,
        focus: str = "general",
    ) -> List[str]:
        """Get SEO keywords for a language and focus area."""
        base = _SEO_KEYWORDS.get(language.value, _SEO_KEYWORDS["en"])
        if focus == "product":
            return base[:5]
        elif focus == "brand":
            return [kw for kw in base if "finnish" in kw.lower() or "nordic" in kw.lower()]
        return base

    def validate_brand_voice(self, text: str) -> Dict[str, Any]:
        """Check text against brand voice guidelines."""
        issues: List[str] = []
        text_lower = text.lower()

        # Check for avoided words
        for word in self.brand.avoid_words:
            if word.lower() in text_lower:
                issues.append(f"Avoid word detected: '{word}'")

        # Check tone alignment
        tone_ok = True
        if self.brand.tone in (BrandTone.LUXURIOUS, BrandTone.PROFESSIONAL):
            casual_words = ["lol", "omg", "btw", "gonna", "wanna"]
            for cw in casual_words:
                if cw in text_lower:
                    issues.append(f"Casual word '{cw}' doesn't match {self.brand.tone.value} tone")
                    tone_ok = False

        # Check for value keywords
        value_present = sum(1 for v in self.brand.values if v.lower() in text_lower)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "tone_aligned": tone_ok,
            "brand_values_mentioned": value_present,
            "brand_values_total": len(self.brand.values),
        }

    # ── Internal helpers ──────────────────────────────────────────

    def _modify_for_followup(self, body: str, followup_num: int, lang: str) -> str:
        """Modify email body for followup sequence."""
        prefixes = {
            "en": {
                1: "I wanted to follow up on my previous message. ",
                2: "Just checking in — I shared some information about our handcrafted pieces. ",
                3: "Final note — I'd love to connect before moving on. ",
            },
            "fi": {
                1: "Halusin palata edelliseen viestiini. ",
                2: "Tarkistin vain — jaoin aiemmin tietoa käsintehtyistä tuotteistamme. ",
                3: "Viimeinen viesti — olisin mielelläni yhteydessä. ",
            },
        }
        lang_prefixes = prefixes.get(lang, prefixes["en"])
        prefix = lang_prefixes.get(min(followup_num, 3), "")

        lines = body.split("\n", 1)
        if len(lines) > 1:
            return lines[0] + "\n" + prefix + lines[1]
        return prefix + body

    def _vary_subject(self, subject: str, variant: int) -> str:
        """Create subject line variant."""
        variations = [
            lambda s: f"Quick question: {s}",
            lambda s: f"[For you] {s}",
            lambda s: s.replace("—", "→"),
        ]
        if variant - 1 < len(variations):
            return variations[variant - 1](subject)
        return subject

    def _vary_cta(self, cta: str, variant: int) -> str:
        """Create CTA variant."""
        variants = [
            "Would a 5-minute call work this week?",
            "Reply 'YES' and I'll send the catalog right away",
            "Check out our collection: arkiobjects.fi",
        ]
        return variants[(variant - 1) % len(variants)]

    def _generate_hypothesis(self, variable: str, variant: int) -> str:
        """Generate test hypothesis."""
        hypotheses = {
            "subject_line": [
                "Baseline: standard subject",
                "Question format increases open rate",
                "Personalization tag increases open rate",
            ],
            "cta": [
                "Baseline: standard CTA",
                "Low-commitment CTA increases reply rate",
                "Direct action CTA increases click rate",
            ],
        }
        options = hypotheses.get(variable, ["Testing variant"])
        return options[variant % len(options)]

    def _generate_topic(self, content_type: str, month: int, seasonal: str) -> str:
        """Generate content topic."""
        topics = {
            "product_photo": f"Product showcase — {'seasonal ' + seasonal if seasonal else 'signature piece'}",
            "behind_scenes": "Workshop tour — making process",
            "lifestyle": f"Lifestyle — {'seasonal: ' + seasonal if seasonal else 'Nordic home styling'}",
            "educational": "Material story — why concrete is special",
        }
        return topics.get(content_type, "General content")

    def _get_relevant_hashtags(self, content_type: str, lang: str) -> List[str]:
        """Get hashtags relevant to content type."""
        base = ["#handmade", "#nordicdesign", "#concrete",
                "#scandinavian", "#homedecor", "#artisan"]
        type_specific = {
            "product_photo": ["#productphotography", "#stilllife", "#flatlay"],
            "behind_scenes": ["#makerslife", "#behindthescenes", "#studiolife"],
            "lifestyle": ["#hygge", "#cozyhome", "#interiordesign"],
            "educational": ["#craftsman", "#howto", "#handmadeprocess"],
        }
        return base + type_specific.get(content_type, [])

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            **self._stats,
            "brand": self.brand.company_name,
            "has_ai_client": self._ai_client is not None,
        }


