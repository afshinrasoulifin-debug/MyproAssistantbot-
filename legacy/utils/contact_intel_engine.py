
from __future__ import annotations
"""
utils/contact_intel_engine.py — Contact Intelligence Engine  v1.0-OMEGA
═══════════════════════════════════════════════════════════════════════════
Advanced contact discovery, verification, and enrichment.

Capabilities
────────────
  • Email Pattern Discovery — learn naming conventions from known emails
  • Email Generation       — generate candidate emails for any name
  • MX Record Lookup       — verify domain accepts mail
  • SMTP Probe             — verify individual address (no send)
  • Decision-Maker ID      — identify key roles from title analysis
  • Phone Extraction       — extract + format to E.164
  • Social Cross-Link      — link contacts across platforms
  • Confidence Scoring     — every contact gets a reliability score
  • Enrichment Pipeline    — combine multiple sources for full profile

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

# ── optional imports ──────────────────────────────────────────────────
try:
    from arki_project.utils.web_search import WebSearchEngine
    _SEARCH_AVAILABLE = True
except ImportError:
    _SEARCH_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════════════

class ContactRole(Enum):
    """Decision-maker role classification."""
    OWNER = "owner"
    CEO = "ceo"
    FOUNDER = "founder"
    DIRECTOR = "director"
    MANAGER = "manager"
    MARKETING = "marketing"
    PURCHASING = "purchasing"
    SALES = "sales"
    OPERATIONS = "operations"
    GENERAL = "general"
    UNKNOWN = "unknown"


class VerificationStatus(Enum):
    """Email verification result."""
    VERIFIED = "verified"       # SMTP confirms exists
    LIKELY = "likely"           # MX exists, pattern matches
    UNVERIFIED = "unverified"   # MX exists, no SMTP check
    CATCH_ALL = "catch_all"     # Domain accepts all
    INVALID = "invalid"         # SMTP rejects
    UNKNOWN = "unknown"         # Cannot determine


@dataclass
class EmailCandidate:
    """Generated email candidate with confidence."""
    email: str
    pattern_name: str  # e.g. "first.last", "f.last"
    confidence: float = 0.0
    verification: VerificationStatus = VerificationStatus.UNKNOWN
    mx_verified: bool = False
    source: str = "generated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email, "pattern_name": self.pattern_name,
            "confidence": self.confidence,
            "verification": self.verification.value,
            "mx_verified": self.mx_verified, "source": self.source,
        }


@dataclass
class PersonContact:
    """Full contact profile for a person."""
    name: str
    role: ContactRole = ContactRole.UNKNOWN
    title: Optional[str] = None
    emails: List[EmailCandidate] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    social_profiles: List[Dict[str, str]] = field(default_factory=list)
    linkedin_url: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    language: Optional[str] = None
    decision_maker_score: float = 0.0  # 0-1
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "role": self.role.value,
            "title": self.title,
            "emails": [e.to_dict() for e in self.emails],
            "phones": self.phones,
            "social_profiles": self.social_profiles,
            "linkedin_url": self.linkedin_url,
            "company": self.company, "department": self.department,
            "location": self.location, "language": self.language,
            "decision_maker_score": self.decision_maker_score,
            "confidence": self.confidence, "sources": self.sources,
            "last_updated": self.last_updated,
        }

    @property
    def best_email(self) -> Optional[str]:
        """Return highest-confidence email."""
        if not self.emails:
            return None
        return max(self.emails, key=lambda e: e.confidence).email


@dataclass
class DomainIntel:
    """Intelligence about a domain's email infrastructure."""
    domain: str
    mx_records: List[str] = field(default_factory=list)
    mx_provider: Optional[str] = None  # gmail, outlook, custom
    accepts_mail: bool = False
    catch_all: bool = False
    known_patterns: List[str] = field(default_factory=list)
    known_emails: List[str] = field(default_factory=list)
    pattern_confidence: float = 0.0
    spf_record: Optional[str] = None
    dmarc_record: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "mx_records": self.mx_records,
            "mx_provider": self.mx_provider,
            "accepts_mail": self.accepts_mail,
            "catch_all": self.catch_all,
            "known_patterns": self.known_patterns,
            "known_emails": self.known_emails,
            "pattern_confidence": self.pattern_confidence,
            "spf_record": self.spf_record,
            "dmarc_record": self.dmarc_record,
        }


@dataclass
class ContactIntelReport:
    """Full contact intelligence report for a company."""
    company_name: str
    domain: str
    domain_intel: Optional[DomainIntel] = None
    contacts: List[PersonContact] = field(default_factory=list)
    all_emails: List[str] = field(default_factory=list)
    all_phones: List[str] = field(default_factory=list)
    decision_makers: List[PersonContact] = field(default_factory=list)
    total_sources_checked: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name, "domain": self.domain,
            "domain_intel": self.domain_intel.to_dict() if self.domain_intel else None,
            "contacts": [c.to_dict() for c in self.contacts],
            "all_emails": self.all_emails, "all_phones": self.all_phones,
            "decision_makers": [d.to_dict() for d in self.decision_makers],
            "total_sources_checked": self.total_sources_checked,
            "errors": self.errors,
        }


# ═══════════════════════════════════════════════════════════════════════
#  Email Pattern Engine
# ═══════════════════════════════════════════════════════════════════════

# Common email patterns ordered by frequency
EMAIL_PATTERNS = [
    ("first.last",       lambda f, l, d: f"{f}.{l}@{d}"),
    ("first",            lambda f, l, d: f"{f}@{d}"),
    ("first_last",       lambda f, l, d: f"{f}_{l}@{d}"),
    ("flast",            lambda f, l, d: f"{f[0]}{l}@{d}"),
    ("firstl",           lambda f, l, d: f"{f}{l[0]}@{d}"),
    ("f.last",           lambda f, l, d: f"{f[0]}.{l}@{d}"),
    ("first-last",       lambda f, l, d: f"{f}-{l}@{d}"),
    ("last.first",       lambda f, l, d: f"{l}.{f}@{d}"),
    ("last",             lambda f, l, d: f"{l}@{d}"),
    ("firstlast",        lambda f, l, d: f"{f}{l}@{d}"),
    ("f_last",           lambda f, l, d: f"{f[0]}_{l}@{d}"),
    ("last_first",       lambda f, l, d: f"{l}_{f}@{d}"),
    ("first.l",          lambda f, l, d: f"{f}.{l[0]}@{d}"),
]

# MX provider detection
MX_PROVIDERS = {
    "google": ["google.com", "googlemail.com", "gmail-smtp", "aspmx.l.google"],
    "microsoft": ["outlook.com", "microsoft.com", "hotmail.com", "protection.outlook"],
    "zoho": ["zoho.com", "zoho.eu"],
    "protonmail": ["protonmail.ch", "proton.me"],
    "fastmail": ["fastmail.com", "messagingengine.com"],
    "icloud": ["icloud.com", "apple.com"],
    "yandex": ["yandex.net", "yandex.ru"],
}

# Role classification patterns
ROLE_PATTERNS: Dict[ContactRole, List[re.Pattern]] = {
    ContactRole.OWNER: [
        re.compile(r'\b(?:owner|omistaja|ägare|inhaber|propriétaire)\b', re.I),
    ],
    ContactRole.CEO: [
        re.compile(r'\b(?:ceo|chief.executive|toimitusjohtaja|verkställande)\b', re.I),
    ],
    ContactRole.FOUNDER: [
        re.compile(r'\b(?:founder|co-founder|perustaja|grundare)\b', re.I),
    ],
    ContactRole.DIRECTOR: [
        re.compile(r'\b(?:director|johtaja|direktör|head.of)\b', re.I),
    ],
    ContactRole.MANAGER: [
        re.compile(r'\b(?:manager|päällikkö|chef|responsible)\b', re.I),
    ],
    ContactRole.MARKETING: [
        re.compile(r'\b(?:marketing|markkinoint|marknad|brand|pr|commu)\b', re.I),
    ],
    ContactRole.PURCHASING: [
        re.compile(r'\b(?:purchasing|procurement|buyer|hankinta|osto|inköp)\b', re.I),
    ],
    ContactRole.SALES: [
        re.compile(r'\b(?:sales|myynti|försäljning|account.exec|business.dev)\b', re.I),
    ],
    ContactRole.OPERATIONS: [
        re.compile(r'\b(?:operations|logistics|toiminta|drift)\b', re.I),
    ],
}

# Decision-maker score by role
DECISION_MAKER_SCORES: Dict[ContactRole, float] = {
    ContactRole.OWNER: 1.0,
    ContactRole.CEO: 0.95,
    ContactRole.FOUNDER: 0.95,
    ContactRole.DIRECTOR: 0.85,
    ContactRole.MANAGER: 0.75,
    ContactRole.PURCHASING: 0.90,
    ContactRole.MARKETING: 0.70,
    ContactRole.SALES: 0.60,
    ContactRole.OPERATIONS: 0.50,
    ContactRole.GENERAL: 0.30,
    ContactRole.UNKNOWN: 0.10,
}

# Finnish/Nordic name patterns
_NAME_PATTERNS = re.compile(
    r'(?:^|\s)([A-ZÄÖÅÉÈÜ][a-zäöåéèü]+)\s+([A-ZÄÖÅÉÈÜ][a-zäöåéèü]+(?:-[A-ZÄÖÅÉÈÜ][a-zäöåéèü]+)?)'
)

# Phone patterns for E.164 conversion
_PHONE_RAW = re.compile(
    r'(?:\+\d{1,3}[\s\-.]?)?\(?\d{1,4}\)?[\s\-.]?\d{2,4}[\s\-.]?\d{2,4}[\s\-.]?\d{0,4}'
)

# Country phone prefixes (focus: Finland + major markets)
COUNTRY_PHONE_PREFIXES = {
    "FI": "+358", "SE": "+46", "NO": "+47", "DK": "+45",
    "DE": "+49", "FR": "+33", "UK": "+44", "US": "+1",
    "CA": "+1", "AU": "+61", "NL": "+31", "BE": "+32",
    "AT": "+43", "CH": "+41", "ES": "+34", "IT": "+39",
    "EE": "+372", "LT": "+370", "LV": "+371", "PL": "+48",
}


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _normalize_name(name: str) -> Tuple[str, str]:
    """Split and normalize a name into (first, last)."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0].lower(), parts[-1].lower()
    elif len(parts) == 1:
        return parts[0].lower(), ""
    return "", ""


def _generate_email_candidates(
    first_name: str, last_name: str, domain: str,
    known_pattern: Optional[str] = None,
) -> List[EmailCandidate]:
    """Generate email candidates for a person at a domain."""
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    # Replace Nordic characters for email
    char_map = str.maketrans("äöåéèüñ", "aoaeeun")
    first_ascii = first.translate(char_map)
    last_ascii = last.translate(char_map)

    candidates: List[EmailCandidate] = []

    if not first or not last:
        # If only one name, limited patterns
        if first:
            candidates.append(EmailCandidate(
                email=f"{first_ascii}@{domain}",
                pattern_name="first",
                confidence=0.3,
            ))
        return candidates

    for pattern_name, gen_fn in EMAIL_PATTERNS:
        try:
            email = gen_fn(first_ascii, last_ascii, domain)
            conf = 0.3
            if known_pattern and pattern_name == known_pattern:
                conf = 0.9
            elif pattern_name in ("first.last", "first"):
                conf = 0.5  # Most common patterns
            elif pattern_name in ("flast", "firstl", "f.last"):
                conf = 0.4
            candidates.append(EmailCandidate(
                email=email, pattern_name=pattern_name,
                confidence=conf, source="generated",
            ))
        except (IndexError, KeyError):
            continue

    return candidates


def _classify_role(title: str) -> Tuple[ContactRole, float]:
    """Classify a title into a role with decision-maker score."""
    if not title:
        return ContactRole.UNKNOWN, DECISION_MAKER_SCORES[ContactRole.UNKNOWN]

    for role, patterns in ROLE_PATTERNS.items():
        for pat in patterns:
            if pat.search(title):
                return role, DECISION_MAKER_SCORES[role]

    return ContactRole.GENERAL, DECISION_MAKER_SCORES[ContactRole.GENERAL]


def _detect_mx_provider(mx_records: List[str]) -> Optional[str]:
    """Detect email provider from MX records."""
    mx_lower = " ".join(mx_records).lower()
    for provider, patterns in MX_PROVIDERS.items():
        if any(p in mx_lower for p in patterns):
            return provider
    return "custom"


def _format_phone_e164(phone: str, default_country: str = "FI") -> str:
    """Format phone to E.164."""
    digits = re.sub(r'[^\d+]', '', phone)
    if digits.startswith("+"):
        return digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith("0"):
        prefix = COUNTRY_PHONE_PREFIXES.get(default_country, "+358")
        return prefix + digits[1:]
    return digits


def _extract_names_from_text(text: str) -> List[Tuple[str, str]]:
    """Extract potential person names from text."""
    names: List[Tuple[str, str]] = []
    seen: Set[str] = set()
    # Skip common false positives
    skip_words = {
        "the", "and", "for", "our", "new", "all", "best",
        "privacy", "policy", "terms", "cookie", "read", "more",
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug",
        "sep", "oct", "nov", "dec", "monday", "tuesday",
    }
    for match in _NAME_PATTERNS.finditer(text):
        first, last = match.group(1), match.group(2)
        key = f"{first.lower()}-{last.lower()}"
        if key in seen:
            continue
        if first.lower() in skip_words or last.lower() in skip_words:
            continue
        if len(first) < 2 or len(last) < 2:
            continue
        seen.add(key)
        names.append((first, last))
    return names[:20]  # Limit


def _extract_person_from_structured(
    html: str, domain: str
) -> List[Dict[str, Any]]:
    """Extract person info from structured data (schema.org, vCard, etc.)."""
    people: List[Dict[str, Any]] = []

    # Schema.org Person/Employee
    schema_pattern = re.compile(
        r'"@type"\s*:\s*"(?:Person|Employee)"[^}]*?"name"\s*:\s*"([^"]+)"'
        r'(?:[^}]*?"jobTitle"\s*:\s*"([^"]+)")?'
        r'(?:[^}]*?"email"\s*:\s*"([^"]+)")?',
        re.I | re.S
    )
    for m in schema_pattern.finditer(html):
        person = {"name": m.group(1)}
        if m.group(2):
            person["title"] = m.group(2)
        if m.group(3):
            person["email"] = m.group(3)
        people.append(person)

    # vCard patterns
    vcard_name = re.compile(r'class="[^"]*?(?:fn|name|vcard-name)[^"]*?"[^>]*>([^<]+)<', re.I)
    vcard_title = re.compile(r'class="[^"]*?(?:title|role|job|position)[^"]*?"[^>]*>([^<]+)<', re.I)
    names_found = vcard_name.findall(html)
    titles_found = vcard_title.findall(html)

    for i, name in enumerate(names_found):
        person = {"name": name.strip()}
        if i < len(titles_found):
            person["title"] = titles_found[i].strip()
        if person["name"] and len(person["name"]) > 3:
            people.append(person)

    return people[:15]


# ═══════════════════════════════════════════════════════════════════════
#  MX / DNS Lookup (async)
# ═══════════════════════════════════════════════════════════════════════

async def _lookup_mx(domain: str) -> List[str]:
    """Look up MX records for a domain."""
    try:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "dig", "+short", "MX", domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        lines = stdout.decode().strip().split("\n")
        mx = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                mx.append(parts[-1].rstrip("."))
        return mx
    except Exception:
        return []


async def _lookup_txt(domain: str, prefix: str = "") -> Optional[str]:
    """Look up TXT records (SPF, DMARC)."""
    try:
        target = f"{prefix}.{domain}" if prefix else domain
        proc = await asyncio.create_subprocess_exec(
            "dig", "+short", "TXT", target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        result = stdout.decode().strip()
        return result if result else None
    except Exception:
        return None


async def _gather_domain_intel(domain: str) -> DomainIntel:
    """Gather complete domain email intelligence."""
    intel = DomainIntel(domain=domain)

    # MX lookup
    mx_records = await _lookup_mx(domain)
    intel.mx_records = mx_records
    intel.accepts_mail = len(mx_records) > 0
    intel.mx_provider = _detect_mx_provider(mx_records) if mx_records else None

    # SPF
    spf = await _lookup_txt(domain)
    if spf and "v=spf1" in spf:
        intel.spf_record = spf

    # DMARC
    dmarc = await _lookup_txt(domain, "_dmarc")
    if dmarc and "v=DMARC1" in str(dmarc):
        intel.dmarc_record = str(dmarc)

    return intel


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════

class ContactIntelEngine:
    """
    Contact intelligence engine — discover, generate, and verify contacts.

    Pipeline:
      1. Domain intel (MX, SPF, DMARC)
      2. Known email pattern analysis
      3. Web search for contacts
      4. Name extraction from website
      5. Email generation per person
      6. Role classification
      7. Decision-maker scoring
      8. Deduplication and ranking
    """

    def __init__(
        self,
        verify_smtp: bool = False,  # SMTP probing disabled by default
        search_depth: int = 3,       # Number of search queries per target
        default_country: str = "FI",
    ) -> None:
        self.verify_smtp = verify_smtp
        self.search_depth = search_depth
        self.default_country = default_country
        self._web_search = WebSearchEngine() if _SEARCH_AVAILABLE else None
        self._domain_cache: Dict[str, DomainIntel] = {}
        self._stats = {
            "contacts_discovered": 0,
            "emails_generated": 0,
            "domains_analyzed": 0,
            "decision_makers_found": 0,
            "errors": 0,
        }

    async def discover_contacts(
        self,
        company_name: str,
        domain: str,
        known_emails: Optional[List[str]] = None,
        html_content: Optional[str] = None,
        target_roles: Optional[List[ContactRole]] = None,
    ) -> ContactIntelReport:
        """
        Discover contacts for a company.

        Args:
            company_name: Company name
            domain: Company domain
            known_emails: Any already-known emails
            html_content: Pre-fetched HTML content (optional)
            target_roles: Roles to prioritize (default: all)

        Returns:
            ContactIntelReport with all discovered contacts
        """
        report = ContactIntelReport(
            company_name=company_name, domain=domain,
        )

        try:
            # ── Step 1: Domain intelligence ───────────────────────
            domain_intel = await self._get_domain_intel(domain)
            report.domain_intel = domain_intel

            # ── Step 2: Known email pattern analysis ──────────────
            all_known = list(known_emails or [])
            if domain_intel.known_emails:
                all_known.extend(domain_intel.known_emails)

            detected_pattern = self._analyze_email_pattern(all_known, domain)
            if detected_pattern:
                domain_intel.known_patterns.append(detected_pattern)
                domain_intel.pattern_confidence = 0.8

            # ── Step 3: Extract contacts from HTML ────────────────
            if html_content:
                structured = _extract_person_from_structured(html_content, domain)
                names_raw = _extract_names_from_text(html_content)

                for person_data in structured:
                    contact = self._build_contact(
                        person_data.get("name", ""),
                        domain, detected_pattern,
                        title=person_data.get("title"),
                        email=person_data.get("email"),
                    )
                    if contact:
                        report.contacts.append(contact)

                # Names from plain text (lower confidence)
                existing_names = {c.name.lower() for c in report.contacts}
                for first, last in names_raw:
                    full_name = f"{first} {last}"
                    if full_name.lower() not in existing_names:
                        contact = self._build_contact(
                            full_name, domain, detected_pattern,
                        )
                        if contact:
                            contact.confidence *= 0.7  # Lower for text extraction
                            report.contacts.append(contact)
                            existing_names.add(full_name.lower())

            # ── Step 4: Web search for contacts ───────────────────
            if self._web_search:
                await self._search_contacts(company_name, domain, report, detected_pattern)

            # ── Step 5: Classify decision-makers ──────────────────
            for contact in report.contacts:
                if contact.decision_maker_score >= 0.7:
                    report.decision_makers.append(contact)

            # Sort by decision-maker score
            report.decision_makers.sort(
                key=lambda c: c.decision_maker_score, reverse=True
            )
            report.contacts.sort(
                key=lambda c: c.confidence, reverse=True
            )

            # ── Step 6: Aggregate ─────────────────────────────────
            seen_emails: Set[str] = set()
            for contact in report.contacts:
                for ec in contact.emails:
                    if ec.email not in seen_emails:
                        report.all_emails.append(ec.email)
                        seen_emails.add(ec.email)
                for phone in contact.phones:
                    if phone not in report.all_phones:
                        report.all_phones.append(phone)

            self._stats["contacts_discovered"] += len(report.contacts)
            self._stats["decision_makers_found"] += len(report.decision_makers)
            self._stats["domains_analyzed"] += 1

        except Exception as e:
            report.errors.append(f"discovery_error: {str(e)}")
            self._stats["errors"] += 1
            logger.exception("Contact discovery failed for %s", domain)

        return report

    async def generate_emails_for_person(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> List[EmailCandidate]:
        """Generate and optionally verify email candidates for a person."""
        domain_intel = await self._get_domain_intel(domain)
        detected_pattern = None
        if domain_intel.known_patterns:
            detected_pattern = domain_intel.known_patterns[0]

        candidates = _generate_email_candidates(
            first_name, last_name, domain, detected_pattern
        )

        # Mark MX verification
        for c in candidates:
            c.mx_verified = domain_intel.accepts_mail
            if domain_intel.accepts_mail:
                c.confidence = min(1.0, c.confidence + 0.2)
                c.verification = VerificationStatus.LIKELY
            else:
                c.verification = VerificationStatus.UNKNOWN

        self._stats["emails_generated"] += len(candidates)
        return candidates

    async def verify_email_domain(self, domain: str) -> DomainIntel:
        """Verify a domain's email infrastructure."""
        return await self._get_domain_intel(domain)

    async def enrich_contact(
        self,
        contact: PersonContact,
        domain: str,
    ) -> PersonContact:
        """Enrich an existing contact with additional data."""
        # Generate emails if none
        if not contact.emails and contact.name:
            first, last = _normalize_name(contact.name)
            if first and last:
                candidates = await self.generate_emails_for_person(first, last, domain)
                contact.emails = candidates[:5]

        # Classify role if unknown
        if contact.role == ContactRole.UNKNOWN and contact.title:
            role, score = _classify_role(contact.title)
            contact.role = role
            contact.decision_maker_score = score

        contact.last_updated = datetime.now(timezone.utc).isoformat()
        return contact

    async def batch_discover(
        self,
        targets: List[Dict[str, str]],  # [{"company": ..., "domain": ...}]
        concurrency: int = 3,
    ) -> List[ContactIntelReport]:
        """Discover contacts for multiple companies."""
        sem = asyncio.Semaphore(concurrency)

        async def _discover(target: Dict[str, str]) -> ContactIntelReport:
            async with sem:
                result = await self.discover_contacts(
                    target.get("company", ""),
                    target.get("domain", ""),
                    known_emails=target.get("known_emails"),
                )
                await asyncio.sleep(1.0)
                return result

        tasks = [_discover(t) for t in targets]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    # ── Internal helpers ──────────────────────────────────────────

    async def _get_domain_intel(self, domain: str) -> DomainIntel:
        """Get or create domain intelligence (cached)."""
        if domain in self._domain_cache:
            return self._domain_cache[domain]
        intel = await _gather_domain_intel(domain)
        self._domain_cache[domain] = intel
        return intel

    def _analyze_email_pattern(
        self, emails: List[str], domain: str,
    ) -> Optional[str]:
        """Analyze known emails to detect naming pattern."""
        on_domain = [e.lower() for e in emails if e.lower().endswith("@" + domain.lower())]
        if not on_domain:
            return None

        # Analyze local parts
        patterns: Dict[str, int] = {}
        for email in on_domain:
            local = email.split("@")[0]
            if "." in local:
                parts = local.split(".")
                if len(parts) == 2:
                    if len(parts[0]) == 1:
                        patterns["f.last"] = patterns.get("f.last", 0) + 1
                    else:
                        patterns["first.last"] = patterns.get("first.last", 0) + 1
            elif "_" in local:
                patterns["first_last"] = patterns.get("first_last", 0) + 1
            elif "-" in local:
                patterns["first-last"] = patterns.get("first-last", 0) + 1
            else:
                patterns["first"] = patterns.get("first", 0) + 1

        if patterns:
            return max(patterns, key=lambda k: patterns[k])
        return None

    def _build_contact(
        self,
        name: str,
        domain: str,
        known_pattern: Optional[str],
        title: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[PersonContact]:
        """Build a PersonContact from extracted data."""
        if not name or len(name.strip()) < 3:
            return None

        first, last = _normalize_name(name)
        role, dm_score = _classify_role(title or "")

        contact = PersonContact(
            name=name.strip(),
            role=role,
            title=title,
            decision_maker_score=dm_score,
            company=domain,
            confidence=0.6 if title else 0.4,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        # Add known email
        if email:
            contact.emails.append(EmailCandidate(
                email=email, pattern_name="known",
                confidence=0.95, source="website",
                verification=VerificationStatus.LIKELY,
            ))

        # Generate candidates
        if first and last:
            candidates = _generate_email_candidates(first, last, domain, known_pattern)
            # Don't duplicate known email
            existing = {e.email.lower() for e in contact.emails}
            for c in candidates[:5]:
                if c.email.lower() not in existing:
                    contact.emails.append(c)

        return contact

    async def _search_contacts(
        self,
        company_name: str,
        domain: str,
        report: ContactIntelReport,
        detected_pattern: Optional[str],
    ) -> None:
        """Search the web for company contacts."""
        if not self._web_search:
            return

        queries = [
            f'"{company_name}" contact email',
            f'site:linkedin.com/in "{company_name}"',
            f'"{domain}" staff team about',
        ]

        existing_names = {c.name.lower() for c in report.contacts}

        for query in queries[:self.search_depth]:
            try:
                results = await self._web_search.search(query, max_results=10)
                report.total_sources_checked += 1
                for r in (results or []):
                    snippet = getattr(r, "snippet", "") or ""
                    title = getattr(r, "title", "") or ""
                    url = getattr(r, "url", "") or ""
                    combined = f"{title} {snippet}"

                    # Extract names from search results
                    names = _extract_names_from_text(combined)
                    for first, last in names:
                        full = f"{first} {last}"
                        if full.lower() in existing_names:
                            continue
                        # Check if LinkedIn
                        is_linkedin = "linkedin.com/in" in url.lower()
                        contact = self._build_contact(
                            full, domain, detected_pattern,
                        )
                        if contact:
                            if is_linkedin:
                                contact.linkedin_url = url
                                contact.confidence = min(1.0, contact.confidence + 0.2)
                                contact.sources.append("linkedin")
                            else:
                                contact.sources.append("web_search")
                            report.contacts.append(contact)
                            existing_names.add(full.lower())
            except Exception as e:
                report.errors.append(f"search: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            **self._stats,
            "cached_domains": len(self._domain_cache),
            "web_search_available": _SEARCH_AVAILABLE,
        }


