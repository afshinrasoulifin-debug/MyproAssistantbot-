
from __future__ import annotations
"""
tg_bot/utils/b2b_hunter_engine.py — Marketing Agent TITAN (L9)
═══════════════════════════════════════════════════════════════
Autonomous B2B prospect discovery engine.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────┐
   │                   B2B HUNTER ENGINE                      │
   ├──────────┬──────────┬──────────┬──────────┬─────────────┤
   │ Sources  │ Extract  │ Enrich   │ Dedup    │ Score       │
   ├──────────┼──────────┼──────────┼──────────┼─────────────┤
   │ Google   │ Name     │ Email    │ SimHash  │ Firmographic│
   │ Maps     │ Address  │ Phone    │ Name+Loc │ Fit         │
   │ TripAdv  │ Website  │ Contact  │ URL Norm │ Category    │
   │ Booking  │ Category │ Decision │ Merge    │ Priority    │
   │ Yelp     │ Rating   │ Maker    │ Flag     │ Queue       │
   │ WebSrch  │ Hours    │ LinkedIn │          │             │
   └──────────┴──────────┴──────────┴──────────┴─────────────┘

Pipeline
────────
  1. Build geo-targeted search queries per category + region
  2. Execute parallel searches across sources
  3. Extract structured business data from results
  4. Enrich with contact info via web_recon.py
  5. Deduplicate via fingerprint (SimHash / name+city hash)
  6. Score via ProspectScoringEngine
  7. Store via MarketingDataBridge

Reuses
──────
  • web_search.py — multi-engine search
  • web_recon.py — email/phone/social extraction
  • anti_detection.py — request fingerprint rotation
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


# ── Existing modules ──
try:
    from arki_project.utils.web_search import WebSearchEngine
    _WEB_SEARCH_AVAILABLE = True
except ImportError:
    _WEB_SEARCH_AVAILABLE = False

try:
    from arki_project.utils.web_recon import WebReconEngine
    _WEB_RECON_AVAILABLE = True
except ImportError:
    _WEB_RECON_AVAILABLE = False

try:
    _ANTI_DETECTION_AVAILABLE = True
except ImportError:
    _ANTI_DETECTION_AVAILABLE = False

# ── OMEGA modules ──
try:
    from utils.deep_recon_engine import DeepReconEngine
    _DEEP_RECON_AVAILABLE = True
except ImportError:
    _DEEP_RECON_AVAILABLE = False

try:
    from utils.contact_intel_engine import ContactIntelEngine
    _CONTACT_INTEL_AVAILABLE = True
except ImportError:
    _CONTACT_INTEL_AVAILABLE = False

try:
    from utils.competitor_radar_engine import CompetitorRadarEngine
    _COMPETITOR_RADAR_AVAILABLE = True
except ImportError:
    _COMPETITOR_RADAR_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class HuntResult:
    """Result from a single hunt operation."""
    prospects_found: int = 0
    prospects_new: int = 0
    prospects_duplicate: int = 0
    errors: List[str] = field(default_factory=list)
    queries_executed: int = 0
    duration_seconds: float = 0.0
    region: str = ""
    category: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prospects_found": self.prospects_found,
            "prospects_new": self.prospects_new,
            "prospects_duplicate": self.prospects_duplicate,
            "errors": self.errors,
            "queries_executed": self.queries_executed,
            "duration_seconds": round(self.duration_seconds, 1),
            "region": self.region,
            "category": self.category,
        }


@dataclass
class RawProspect:
    """Raw business data extracted from search results before enrichment."""
    business_name: str = ""
    business_type: str = ""
    website: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    region: str = ""
    rating: float = 0.0
    review_count: int = 0
    phone: str = ""
    email: str = ""
    source: str = ""
    source_url: str = ""
    source_query: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# B2B Hunter Engine
# ═══════════════════════════════════════════════════════════

class B2BHunterEngine:
    """
    Autonomous B2B prospect discovery engine.

    Hunts for business prospects across multiple sources,
    extracts contact information, scores, and stores them.
    """

    def __init__(
        self,
        *,
        max_results_per_query: int = 50,
        search_radius_km: int = 100,
        cooldown_hours: float = 24.0,
        max_concurrent: int = 3,
    ) -> None:
        self._max_results = max_results_per_query
        self._radius_km = search_radius_km
        self._cooldown_hours = cooldown_hours
        self._max_concurrent = max_concurrent
        self._last_hunt: Dict[str, float] = {}  # region:category → timestamp
        self._web_search = WebSearchEngine() if _WEB_SEARCH_AVAILABLE else None
        self._web_recon = WebReconEngine() if _WEB_RECON_AVAILABLE else None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        # OMEGA deep-intel engines
        self._deep_recon = DeepReconEngine() if _DEEP_RECON_AVAILABLE else None
        self._contact_intel = ContactIntelEngine() if _CONTACT_INTEL_AVAILABLE else None

    # ── Main Hunt Entry Point ────────────────────────────

    async def hunt(
        self,
        region: str,
        category: Dict[str, Any],
        *,
        data_bridge=None,
        scoring_engine=None,
    ) -> HuntResult:
        """
        Execute a full B2B hunting operation for a region + category.

        Args:
            region: Target market region dict (from config_marketing)
            category: B2B category dict (from config_marketing)
            data_bridge: MarketingDataBridge instance for storage
            scoring_engine: ProspectScoringEngine for scoring

        Returns:
            HuntResult with operation summary
        """
        start = time.monotonic()
        region_name = region if isinstance(region, str) else region.get("region", "Unknown")
        cat_id = category.get("id", "unknown")
        result = HuntResult(region=region_name, category=cat_id)

        # Cooldown check
        hunt_key = f"{region_name}:{cat_id}"
        last = self._last_hunt.get(hunt_key, 0)
        if time.time() - last < self._cooldown_hours * 3600:
            remaining_h = round((self._cooldown_hours * 3600 - (time.time() - last)) / 3600, 1)
            result.errors.append(f"Cooldown active: {remaining_h}h remaining")
            return result

        logger.info("🔍 Starting B2B hunt: %s / %s", region_name, cat_id)

        try:
            # Step 1: Build search queries
            queries = self._build_queries(region_name, category)
            result.queries_executed = len(queries)

            # Step 2: Execute searches
            raw_prospects = await self._execute_searches(queries, result)

            # Step 3: Deduplicate
            unique_prospects = self._deduplicate(raw_prospects)
            result.prospects_duplicate = len(raw_prospects) - len(unique_prospects)

            # Step 4: Enrich with contact data
            enriched = await self._enrich_prospects(unique_prospects)

            # Step 5: Score and store
            for prospect_data in enriched:
                stored = await self._store_prospect(
                    prospect_data, region_name, cat_id,
                    data_bridge=data_bridge,
                    scoring_engine=scoring_engine,
                )
                if stored:
                    result.prospects_new += 1

            result.prospects_found = len(raw_prospects)
            self._last_hunt[hunt_key] = time.time()

        except Exception as exc:
            logger.error("Hunt error [%s/%s]: %s", region_name, cat_id, exc)
            result.errors.append(str(exc))

        result.duration_seconds = time.monotonic() - start
        logger.info(
            "✅ Hunt complete: %s/%s — %d found, %d new, %d dups, %.1fs",
            region_name, cat_id,
            result.prospects_found, result.prospects_new,
            result.prospects_duplicate, result.duration_seconds,
        )

        return result

    async def hunt_all_regions(
        self,
        regions: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        *,
        data_bridge=None,
        scoring_engine=None,
        max_parallel_regions: int = 2,
    ) -> List[HuntResult]:
        """
        Hunt across all regions and categories.
        Executes region hunts with limited parallelism.
        """
        results = []
        sem = asyncio.Semaphore(max_parallel_regions)

        async def hunt_region_category(reg: Any, cat: Any) -> Any:
            async with sem:
                return await self.hunt(
                    reg, cat,
                    data_bridge=data_bridge,
                    scoring_engine=scoring_engine,
                )

        tasks = []
        for region in regions:
            for category in categories:
                tasks.append(hunt_region_category(region, category))

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for r in completed:
                if isinstance(r, HuntResult):
                    results.append(r)
                elif isinstance(r, Exception):
                    logger.error("Hunt task failed: %s", r)

        return results

    # ── Query Building ───────────────────────────────────

    def _build_queries(self, region: str, category: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Build a set of search queries for a region + category.

        Creates queries for each search term in the category,
        combined with the region for geo-targeting.
        """
        queries = []
        search_terms = category.get("search_terms", [])
        cat_name = category.get("name_en", "business")

        for term in search_terms:
            # Primary query: term + region
            queries.append({
                "query": f"{term} in {region}",
                "type": "general",
                "term": term,
            })

            # Specific query: term + "handmade decor supplier"
            queries.append({
                "query": f"{term} {region} interior design decoration",
                "type": "decor_focused",
                "term": term,
            })

            # Contact-focused query
            queries.append({
                "query": f"{term} {region} contact email",
                "type": "contact_focused",
                "term": term,
            })

        # Category-specific query
        queries.append({
            "query": f"best {cat_name} {region} for artisan products",
            "type": "artisan_focused",
            "term": cat_name,
        })

        return queries

    # ── Search Execution ─────────────────────────────────

    async def _execute_searches(
        self,
        queries: List[Dict[str, str]],
        result: HuntResult,
    ) -> List[RawProspect]:
        """Execute searches across all queries and extract prospects."""
        raw_prospects = []

        for q in queries:
            try:
                async with self._semaphore:
                    prospects = await self._search_and_extract(q)
                    raw_prospects.extend(prospects)
            except Exception as exc:
                logger.warning("Search error for '%s': %s", q["query"], exc)
                result.errors.append(f"Search '{q['query'][:50]}': {exc}")

            # Anti-detection: small delay between queries
            await asyncio.sleep(1.5)

        return raw_prospects

    async def _search_and_extract(self, query: Dict[str, str]) -> List[RawProspect]:
        """Execute a single search query and extract business data."""
        prospects = []

        if self._web_search is None:
            logger.warning("WebSearchEngine not available")
            return prospects

        try:
            # Use the existing web_search engine
            _deep_result = await self._web_search.search(
                query["query"],
            )
            search_results = getattr(_deep_result, 'results', [])

            for sr in search_results:
                prospect = self._extract_business_from_result(sr, query)
                if prospect and prospect.business_name:
                    prospects.append(prospect)

        except Exception as exc:
            logger.warning("Search execution error: %s", exc)

        return prospects

    def _extract_business_from_result(
        self,
        search_result: Any,
        query: Dict[str, str],
    ) -> Optional[RawProspect]:
        """Extract structured business data from a search result."""
        try:
            title = ""
            url = ""
            snippet = ""

            if isinstance(search_result, dict):
                title = search_result.get("title", "")
                url = search_result.get("url", "")
                snippet = search_result.get("snippet", "")
            elif hasattr(search_result, "title"):
                title = getattr(search_result, "title", "")
                url = getattr(search_result, "url", "")
                snippet = getattr(search_result, "snippet", "")
            else:
                return None

            if not title:
                return None

            # Filter out non-business results
            skip_patterns = [
                r"wikipedia\.org", r"yelp\.com/topic",
                r"tripadvisor\.\w+/Tourism", r"\.pdf$",
            ]
            for pat in skip_patterns:
                if re.search(pat, url, re.I):
                    return None

            # Extract city from query context
            query_text = query.get("query", "")
            city_match = re.search(r"in\s+(\w[\w\s]+?)(?:\s+\w+\s+\w+)?$", query_text)

            prospect = RawProspect(
                business_name=self._clean_business_name(title),
                business_type=query.get("term", ""),
                website=url,
                source="web_search",
                source_url=url,
                source_query=query["query"],
            )

            # Try to extract phone/email from snippet
            phone_match = re.search(r"[\+]?[\d\s\-\(\)]{10,}", snippet)
            if phone_match:
                prospect.phone = phone_match.group().strip()

            email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", snippet)
            if email_match:
                prospect.email = email_match.group()

            return prospect

        except Exception:
            return None

    @staticmethod
    def _clean_business_name(raw_name: str) -> str:
        """Clean and normalize a business name from search results."""
        # Remove common suffixes from titles
        name = re.sub(r"\s*[-–|·]\s*(Booking|TripAdvisor|Yelp|Google|Reviews?).*$", "", raw_name, flags=re.I)
        name = re.sub(r"\s*\(.*?\)\s*$", "", name)
        name = name.strip()
        return name[:256] if name else ""

    # ── Deduplication ────────────────────────────────────

    def _deduplicate(self, prospects: List[RawProspect]) -> List[RawProspect]:
        """Deduplicate prospects by normalized name + website."""
        seen: Set[str] = set()
        unique = []

        for p in prospects:
            # Fingerprint: normalized name + website domain
            name_norm = re.sub(r"[^a-z0-9]", "", p.business_name.lower())
            domain = ""
            if p.website:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(p.website).netloc.lower()
                except Exception:
                    domain = p.website.lower()

            fp = f"{name_norm}|{domain}"
            if fp not in seen:
                seen.add(fp)
                unique.append(p)

        logger.debug("Dedup: %d → %d unique", len(prospects), len(unique))
        return unique

    # ── Contact Enrichment ───────────────────────────────

    async def _enrich_prospects(
        self,
        prospects: List[RawProspect],
    ) -> List[Dict[str, Any]]:
        """
        Enrich raw prospects with contact data via web_recon.

        For each prospect with a website, attempts to extract:
        - Email addresses
        - Phone numbers
        - Social media profiles
        - Contact person names & roles
        """
        enriched = []

        for prospect in prospects:
            data = self._raw_to_dict(prospect)

            if prospect.website and self._web_recon:
                try:
                    async with self._semaphore:
                        recon_data = await self._web_recon.full_recon(prospect.website)

                    # Extract emails
                    if not data.get("email"):
                        emails = recon_data.get("emails", [])
                        if emails:
                            # Prefer info@ or contact@ emails
                            priority_emails = [
                                e for e in emails
                                if any(p in e.lower() for p in ["info", "contact", "hello", "sales"])
                            ]
                            data["email"] = priority_emails[0] if priority_emails else emails[0]

                    # Extract phone
                    if not data.get("phone"):
                        phones = recon_data.get("phones", [])
                        if phones:
                            data["phone"] = phones[0]

                    # Social profiles
                    socials = recon_data.get("social_profiles", {})
                    if socials:
                        data["extra_data"] = {"social_profiles": socials}

                except Exception as exc:
                    logger.debug("Recon failed for %s: %s", prospect.website, exc)

                # ── OMEGA: Deep Recon enrichment ──────────────
                if self._deep_recon and prospect.website:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(prospect.website).netloc.lower()
                        if domain.startswith("www."):
                            domain = domain[4:]
                        deep_report = await self._deep_recon.full_recon(
                            domain, depth="standard"
                        )
                        deep_dict = deep_report.to_dict() if hasattr(deep_report, 'to_dict') else {}
                        # Merge tech stack info
                        tech = deep_dict.get("technology_stack", {})
                        if tech:
                            data.setdefault("extra_data", {})["tech_stack"] = tech
                        # Merge security posture
                        sec = deep_dict.get("security_assessment", {})
                        if sec:
                            data.setdefault("extra_data", {})["security_posture"] = sec
                        # Merge DNS / infrastructure
                        dns = deep_dict.get("dns_records", {})
                        if dns:
                            data.setdefault("extra_data", {})["dns_intel"] = dns
                    except Exception as exc:
                        logger.debug("Deep recon failed for %s: %s", prospect.website, exc)

                # ── OMEGA: Contact Intelligence enrichment ────
                if self._contact_intel and prospect.website:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(prospect.website).netloc.lower()
                        if domain.startswith("www."):
                            domain = domain[4:]
                        contact_report = await self._contact_intel.discover_contacts(
                            company_name=prospect.business_name,
                            domain=domain,
                            known_emails=[data["email"]] if data.get("email") else None,
                        )
                        # Use decision-maker contacts
                        if contact_report.decision_makers:
                            dm = contact_report.decision_makers[0]
                            if not data.get("contact_person"):
                                data["contact_person"] = dm.name
                            if not data.get("contact_role"):
                                data["contact_role"] = dm.role.value if hasattr(dm.role, 'value') else str(dm.role)
                            if not data.get("email") and dm.best_email:
                                data["email"] = dm.best_email
                            data.setdefault("extra_data", {})["decision_makers"] = [
                                d.to_dict() for d in contact_report.decision_makers[:3]
                            ]
                        # Additional emails
                        if contact_report.all_emails:
                            data.setdefault("extra_data", {})["all_emails"] = contact_report.all_emails[:5]
                        # Additional phones
                        if contact_report.all_phones:
                            if not data.get("phone") and contact_report.all_phones:
                                data["phone"] = contact_report.all_phones[0]
                        # Domain MX intel
                        if contact_report.domain_intel:
                            data.setdefault("extra_data", {})["domain_intel"] = contact_report.domain_intel.to_dict()
                    except Exception as exc:
                        logger.debug("Contact intel failed for %s: %s", prospect.business_name, exc)

                # Anti-detection delay
                await asyncio.sleep(2.0)

            enriched.append(data)

        return enriched

    # ── Storage ──────────────────────────────────────────

    async def _store_prospect(
        self,
        prospect_data: Dict[str, Any],
        region: str,
        category: str,
        *,
        data_bridge=None,
        scoring_engine=None,
    ) -> bool:
        """Score and store a prospect via the data bridge."""
        if data_bridge is None:
            return False

        # Score if engine available
        if scoring_engine:
            try:
                breakdown = await scoring_engine.score_prospect(prospect_data)
                prospect_data["score"] = breakdown.total
                prospect_data["score_factors"] = breakdown.to_dict()
            except Exception:
                prospect_data["score"] = 0.0

        prospect_data.setdefault("country", region)

        # Store
        pid = await data_bridge.create_prospect(prospect_data)
        if pid:
            # Log event
            await data_bridge.log_event(
                "prospect_found",
                prospect_id=pid,
                data={"region": region, "category": category, "source": prospect_data.get("source")},
                outcome="success",
            )
            # Record GDPR basis
            await data_bridge.record_consent(
                pid,
                lawful_basis="legitimate_interest",
                purpose="b2b_outreach",
                consent_method="implied_b2b",
            )
            return True
        return False

    @staticmethod
    def _raw_to_dict(raw: RawProspect) -> Dict[str, Any]:
        """Convert a RawProspect to a dict for the data bridge."""
        return {
            "business_name": raw.business_name,
            "business_type": raw.business_type,
            "website": raw.website,
            "email": raw.email,
            "phone": raw.phone,
            "city": raw.city,
            "country": raw.country,
            "region": raw.region,
            "source": raw.source,
            "source_url": raw.source_url,
            "source_query": raw.source_query,
            "language": "en",
            "extra_data": raw.extra_data,
        }

    # ── Statistics ────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get hunter engine statistics."""
        return {
            "hunt_history_count": len(self._last_hunt),
            "last_hunts": {
                k: datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
                for k, v in self._last_hunt.items()
            },
            "max_results_per_query": self._max_results,
            "search_radius_km": self._radius_km,
            "cooldown_hours": self._cooldown_hours,
            "web_search_available": _WEB_SEARCH_AVAILABLE,
            "web_recon_available": _WEB_RECON_AVAILABLE,
            "anti_detection_available": _ANTI_DETECTION_AVAILABLE,
        }


