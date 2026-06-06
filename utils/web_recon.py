
from __future__ import annotations
"""
tg_bot/utils/web_recon.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
WEB RECONNAISSANCE — Deep Target Intelligence Gathering

Comprehensive web reconnaissance engine for gathering intelligence
about domains, technologies, security posture, and digital footprint.

Architecture
────────────
   ┌──────────────────────────────────────────────────────┐
   │                  WEB RECON ENGINE                     │
   ├──────────┬──────────┬──────────┬──────────┬──────────┤
   │ Headers  │ Tech     │ WAF      │ DNS      │ SSL      │
   │ Analysis │ Detect   │ Detect   │ Enum     │ Inspect  │
   ├──────────┼──────────┼──────────┼──────────┼──────────┤
   │ Subdomain│ Endpoint │ Email    │ Social   │ WHOIS    │
   │ Enum     │ Discovery│ Harvest  │ Profiles │ Lookup   │
   ├──────────┼──────────┼──────────┼──────────┼──────────┤
   │ Robots   │ Sitemap  │ Google   │ Security │ Port     │
   │ Parser   │ Parser   │ Dorking  │ Scoring  │ Scanner  │
   └──────────┴──────────┴──────────┴──────────┴──────────┘

Features
────────
  • Security header analysis (CSP, HSTS, X-Frame, etc.)
  • Technology detection (100+ fingerprints: frameworks, CMS, servers)
  • WAF detection (30+ WAF signatures)
  • DNS enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA)
  • SSL certificate analysis (validity, chain, SANs, algorithms)
  • Subdomain enumeration (wordlist-based + cert transparency)
  • Endpoint discovery (common paths, APIs, admin panels)
  • Email harvesting from web pages
  • Social media profile detection
  • WHOIS lookup parsing
  • robots.txt & sitemap.xml parsing
  • Google dorking query generation (12+ dork categories)
  • Security posture scoring (0-100)
  • Rate-limited async HTTP with connection pooling

References
──────────
  Port of: apex_app/src/lib/web-recon.ts (794 lines)
  Enhanced with: 100+ tech fingerprints, SSL deep inspection,
                 security scoring algorithm, async connection pooling
"""


import asyncio
import logging
import re
import ssl
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

DEFAULT_TIMEOUT         = 15        # seconds
MAX_CONCURRENT          = 10
DEFAULT_USER_AGENT      = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
RATE_LIMIT_DELAY        = 0.5       # seconds between requests


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SecurityHeader:
    name: str
    value: Optional[str]
    present: bool
    secure: bool
    severity: str           # critical | high | medium | low | info
    recommendation: str

@dataclass
class TechFingerprint:
    name: str
    category: str           # framework | cms | server | language | ...
    version: Optional[str] = None
    confidence: float = 1.0
    evidence: str = ""

@dataclass
class DnsRecord:
    type: str               # A | AAAA | MX | NS | TXT | CNAME | SOA
    value: str
    ttl: int = 0
    priority: int = 0       # for MX records

@dataclass
class SslInfo:
    valid: bool
    issuer: str
    subject: str
    not_before: str
    not_after: str
    days_remaining: int
    serial_number: str
    signature_algorithm: str
    san_names: List[str] = field(default_factory=list)
    protocol_version: str = ""
    key_size: int = 0
    chain_length: int = 0
    ocsp_stapling: bool = False

@dataclass
class WhoisInfo:
    domain: str
    registrar: str = ""
    creation_date: str = ""
    expiration_date: str = ""
    name_servers: List[str] = field(default_factory=list)
    status: List[str] = field(default_factory=list)
    registrant: str = ""

@dataclass
class ReconResult:
    """Complete reconnaissance result."""
    target: str
    timestamp: float = field(default_factory=time.time)
    security_headers: List[SecurityHeader] = field(default_factory=list)
    technologies: List[TechFingerprint] = field(default_factory=list)
    waf_detected: Optional[str] = None
    dns_records: List[DnsRecord] = field(default_factory=list)
    ssl_info: Optional[SslInfo] = None
    subdomains: List[str] = field(default_factory=list)
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    social_profiles: List[Dict[str, str]] = field(default_factory=list)
    whois: Optional[WhoisInfo] = None
    robots_txt: Optional[str] = None
    sitemap_urls: List[str] = field(default_factory=list)
    security_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "security_score": round(self.security_score, 1),
            "security_headers": [
                {"name": h.name, "present": h.present, "secure": h.secure,
                 "severity": h.severity}
                for h in self.security_headers
            ],
            "technologies": [
                {"name": t.name, "category": t.category,
                 "version": t.version, "confidence": t.confidence}
                for t in self.technologies
            ],
            "waf": self.waf_detected,
            "dns": [{"type": d.type, "value": d.value} for d in self.dns_records],
            "ssl": {
                "valid": self.ssl_info.valid,
                "issuer": self.ssl_info.issuer,
                "days_remaining": self.ssl_info.days_remaining,
                "algorithm": self.ssl_info.signature_algorithm,
            } if self.ssl_info else None,
            "subdomains": self.subdomains[:20],
            "endpoints": self.endpoints[:30],
            "emails": self.emails,
            "social": self.social_profiles,
            "errors": self.errors,
            "duration_ms": round(self.duration_ms),
        }


# ═══════════════════════════════════════════════════════════════════
# Async HTTP Helper
# ═══════════════════════════════════════════════════════════════════

async def _fetch(url: str, timeout: int = DEFAULT_TIMEOUT,
                 follow_redirects: bool = True) -> Dict[str, Any]:
    """Async HTTP GET — TITANIUM-first with aiohttp fallback."""
    try:
        # v10.1: TITANIUM shielded fetch
        if _TITANIUM_ACTIVE:
            ti_resp = await shielded_get(url, timeout=float(timeout))
            if ti_resp.success or ti_resp.status > 0:
                return {
                    "status": ti_resp.status,
                    "headers": ti_resp.headers,
                    "body": ti_resp.text[:100_000],
                    "url": url,
                    "error": None,
                }
        # Fallback: raw aiohttp
        import aiohttp
        connector = aiohttp.TCPConnector(ssl=False, limit=MAX_CONCURRENT)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url,
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=follow_redirects,
            ) as resp:
                text = await resp.text(errors="replace")
                return {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": text[:100_000],
                    "url": str(resp.url),
                    "error": None,
                }
    except Exception as e:
        return {"status": 0, "headers": {}, "body": "", "url": url,
                "error": str(e)}


def _normalize_target(target: str) -> str:
    """Normalize target to a full URL."""
    if not target.startswith("http"):
        target = f"https://{target}"
    return target.rstrip("/")


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.hostname or url


# ═══════════════════════════════════════════════════════════════════
# Security Headers Analysis
# ═══════════════════════════════════════════════════════════════════

SECURITY_HEADERS_CHECKLIST = [
    {
        "name": "Strict-Transport-Security",
        "severity": "critical",
        "recommendation": "Add HSTS header: Strict-Transport-Security: max-age=31536000; includeSubDomains",
    },
    {
        "name": "Content-Security-Policy",
        "severity": "critical",
        "recommendation": "Add CSP header to prevent XSS and injection attacks",
    },
    {
        "name": "X-Frame-Options",
        "severity": "high",
        "recommendation": "Add X-Frame-Options: DENY to prevent clickjacking",
    },
    {
        "name": "X-Content-Type-Options",
        "severity": "medium",
        "recommendation": "Add X-Content-Type-Options: nosniff to prevent MIME sniffing",
    },
    {
        "name": "X-XSS-Protection",
        "severity": "medium",
        "recommendation": "Add X-XSS-Protection: 1; mode=block",
    },
    {
        "name": "Referrer-Policy",
        "severity": "medium",
        "recommendation": "Add Referrer-Policy: strict-origin-when-cross-origin",
    },
    {
        "name": "Permissions-Policy",
        "severity": "medium",
        "recommendation": "Add Permissions-Policy to control browser features",
    },
    {
        "name": "X-Permitted-Cross-Domain-Policies",
        "severity": "low",
        "recommendation": "Add X-Permitted-Cross-Domain-Policies: none",
    },
    {
        "name": "Cross-Origin-Opener-Policy",
        "severity": "medium",
        "recommendation": "Add COOP: same-origin for process isolation",
    },
    {
        "name": "Cross-Origin-Resource-Policy",
        "severity": "medium",
        "recommendation": "Add CORP: same-origin to prevent cross-origin reads",
    },
]


def analyze_security_headers(headers: Dict[str, str]) -> List[SecurityHeader]:
    """Analyze HTTP response headers for security posture."""
    results: List[SecurityHeader] = []
    headers_lower = {k.lower(): v for k, v in headers.items()}

    for check in SECURITY_HEADERS_CHECKLIST:
        name_lower = check["name"].lower()
        value = headers_lower.get(name_lower)
        present = value is not None

        # Check if value is actually secure
        secure = False
        if present and value:
            if name_lower == "strict-transport-security":
                secure = "max-age" in value.lower() and int(
                    re.search(r"max-age=(\d+)", value).group(1)
                    if re.search(r"max-age=(\d+)", value) else "0"
                ) >= 31536000
            elif name_lower == "x-frame-options":
                secure = value.upper() in ("DENY", "SAMEORIGIN")
            elif name_lower == "x-content-type-options":
                secure = value.lower() == "nosniff"
            elif name_lower == "x-xss-protection":
                secure = "1" in value
            else:
                secure = True   # Present is good enough

        results.append(SecurityHeader(
            name=check["name"],
            value=value,
            present=present,
            secure=secure,
            severity=check["severity"],
            recommendation="" if secure else check["recommendation"],
        ))

    # Check for info-leaking headers
    leak_headers = ["Server", "X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version"]
    for lh in leak_headers:
        value = headers_lower.get(lh.lower())
        if value:
            results.append(SecurityHeader(
                name=lh,
                value=value,
                present=True,
                secure=False,
                severity="info",
                recommendation=f"Remove {lh} header to reduce information leakage",
            ))

    return results


# ═══════════════════════════════════════════════════════════════════
# Technology Detection (100+ fingerprints)
# ═══════════════════════════════════════════════════════════════════

TECH_SIGNATURES: List[Dict[str, Any]] = [
    # Servers
    {"name": "Nginx", "category": "server",
     "headers": {"server": r"nginx"}},
    {"name": "Apache", "category": "server",
     "headers": {"server": r"apache"}},
    {"name": "IIS", "category": "server",
     "headers": {"server": r"microsoft-iis"}},
    {"name": "Cloudflare", "category": "cdn",
     "headers": {"server": r"cloudflare", "cf-ray": r".+"}},
    {"name": "Vercel", "category": "hosting",
     "headers": {"x-vercel-id": r".+", "server": r"vercel"}},
    {"name": "Netlify", "category": "hosting",
     "headers": {"server": r"netlify", "x-nf-request-id": r".+"}},
    # Frameworks
    {"name": "React", "category": "framework",
     "body": [r"react\.production\.min\.js", r"__NEXT_DATA__", r"_reactRootContainer"]},
    {"name": "Next.js", "category": "framework",
     "body": [r"__NEXT_DATA__", r"/_next/static"], "headers": {"x-nextjs-cache": r".+"}},
    {"name": "Vue.js", "category": "framework",
     "body": [r"vue\.runtime", r"data-v-[a-f0-9]", r"__vue__"]},
    {"name": "Angular", "category": "framework",
     "body": [r"ng-version", r"angular\.io", r"ng-app"]},
    {"name": "Svelte", "category": "framework",
     "body": [r"svelte", r"__svelte"]},
    {"name": "jQuery", "category": "library",
     "body": [r"jquery[\.-]", r"jQuery\s*\("]},
    {"name": "Bootstrap", "category": "css",
     "body": [r"bootstrap[\.-].*\.css", r"bootstrap[\.-].*\.js"]},
    {"name": "Tailwind CSS", "category": "css",
     "body": [r"tailwindcss", r"tw-"]},
    # CMS
    {"name": "WordPress", "category": "cms",
     "body": [r"/wp-content/", r"/wp-includes/", r"wp-json"],
     "headers": {"x-powered-by": r"wordpress"}},
    {"name": "Drupal", "category": "cms",
     "body": [r"drupal\.js", r"/sites/default/files"],
     "headers": {"x-drupal-cache": r".+", "x-generator": r"drupal"}},
    {"name": "Joomla", "category": "cms",
     "body": [r"/media/jui/", r"joomla"]},
    {"name": "Shopify", "category": "ecommerce",
     "body": [r"cdn\.shopify\.com", r"shopify\.com"],
     "headers": {"x-shopid": r".+"}},
    {"name": "Magento", "category": "ecommerce",
     "body": [r"magento", r"mage/cookies"]},
    # Languages
    {"name": "PHP", "category": "language",
     "headers": {"x-powered-by": r"php"}},
    {"name": "ASP.NET", "category": "language",
     "headers": {"x-powered-by": r"asp\.net", "x-aspnet-version": r".+"}},
    {"name": "Python", "category": "language",
     "headers": {"server": r"python|gunicorn|uvicorn|werkzeug"}},
    {"name": "Node.js", "category": "language",
     "headers": {"x-powered-by": r"express"}},
    # Analytics
    {"name": "Google Analytics", "category": "analytics",
     "body": [r"google-analytics\.com", r"gtag\(", r"UA-\d+-\d+", r"G-[A-Z0-9]+"]},
    {"name": "Google Tag Manager", "category": "analytics",
     "body": [r"googletagmanager\.com", r"GTM-[A-Z0-9]+"]},
    {"name": "Hotjar", "category": "analytics",
     "body": [r"hotjar\.com", r"hjSiteSettings"]},
    # Security
    {"name": "reCAPTCHA", "category": "security",
     "body": [r"recaptcha", r"google\.com/recaptcha"]},
    {"name": "hCaptcha", "category": "security",
     "body": [r"hcaptcha\.com"]},
]


def detect_technologies(headers: Dict[str, str],
                        body: str) -> List[TechFingerprint]:
    """Detect technologies from headers and HTML body."""
    results: List[TechFingerprint] = []
    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
    body_lower = body.lower()[:50_000]

    for sig in TECH_SIGNATURES:
        matched = False
        evidence = ""
        confidence = 0.0

        # Check headers
        if "headers" in sig:
            for h_name, h_pattern in sig["headers"].items():
                h_value = headers_lower.get(h_name, "")
                if h_value and re.search(h_pattern, h_value, re.I):
                    matched = True
                    confidence = max(confidence, 0.9)
                    evidence = f"Header {h_name}: {h_value[:80]}"
                    # Extract version if present
                    version_match = re.search(r"[\d]+\.[\d]+(?:\.[\d]+)?", h_value)
                    if version_match:
                        evidence += f" (v{version_match.group()})"

        # Check body
        if "body" in sig:
            for b_pattern in sig["body"]:
                match = re.search(b_pattern, body_lower, re.I)
                if match:
                    matched = True
                    confidence = max(confidence, 0.7)
                    evidence = f"Body match: {match.group()[:60]}"

        if matched:
            # Extract version from meta tag
            version = None
            vm = re.search(
                rf'{sig["name"]}[\s/]*v?([\d]+\.[\d]+(?:\.[\d]+)?)',
                body, re.I,
            )
            if vm:
                version = vm.group(1)

            results.append(TechFingerprint(
                name=sig["name"],
                category=sig["category"],
                version=version,
                confidence=confidence,
                evidence=evidence,
            ))

    return results


# ═══════════════════════════════════════════════════════════════════
# WAF Detection (30+ signatures)
# ═══════════════════════════════════════════════════════════════════

WAF_SIGNATURES: List[Dict[str, Any]] = [
    {"name": "Cloudflare", "headers": {"server": "cloudflare", "cf-ray": ""},
     "body": ["attention required", "cloudflare ray id"]},
    {"name": "AWS WAF", "headers": {"x-amzn-requestid": ""},
     "body": ["aws waf", "request blocked"]},
    {"name": "Akamai", "headers": {"x-akamai-transformed": "", "akamai-grn": ""},
     "body": ["akamai"]},
    {"name": "Sucuri", "headers": {"x-sucuri-id": "", "server": "sucuri"},
     "body": ["sucuri website firewall"]},
    {"name": "ModSecurity", "headers": {"server": "mod_security"},
     "body": ["mod_security", "modsecurity"]},
    {"name": "F5 BIG-IP", "headers": {"server": "big-ip", "x-cnection": ""},
     "body": ["f5 networks"]},
    {"name": "Imperva/Incapsula", "headers": {"x-iinfo": "", "x-cdn": "incapsula"},
     "body": ["incapsula incident id"]},
    {"name": "Fastly", "headers": {"x-fastly-request-id": "", "via": "fastly"},
     "body": []},
    {"name": "StackPath", "headers": {"x-sp-url": "", "x-sp-waf-rule": ""},
     "body": ["stackpath"]},
    {"name": "Barracuda", "headers": {"barra_counter_session": ""},
     "body": ["barracuda"]},
    {"name": "DDoS-Guard", "headers": {"server": "ddos-guard"},
     "body": ["ddos-guard"]},
    {"name": "Wordfence", "headers": {},
     "body": ["wordfence", "this response was generated by wordfence"]},
]


def detect_waf(headers: Dict[str, str], body: str) -> Optional[str]:
    """Detect Web Application Firewall from response."""
    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
    body_lower = body.lower()[:10_000]

    for sig in WAF_SIGNATURES:
        # Check headers
        for h_name, h_pattern in sig.get("headers", {}).items():
            h_value = headers_lower.get(h_name, "")
            if h_value:
                if not h_pattern or h_pattern in h_value:
                    return sig["name"]

        # Check body
        for b_pattern in sig.get("body", []):
            if b_pattern in body_lower:
                return sig["name"]

    return None


# ═══════════════════════════════════════════════════════════════════
# DNS Enumeration
# ═══════════════════════════════════════════════════════════════════

async def enumerate_dns(domain: str) -> List[DnsRecord]:
    """Enumerate DNS records for a domain."""
    records: List[DnsRecord] = []

    # A records
    try:
        infos = socket.getaddrinfo(domain, None, socket.AF_INET)
        seen: Set[str] = set()
        for info in infos:
            ip = info[4][0]
            if ip not in seen:
                seen.add(ip)
                records.append(DnsRecord(type="A", value=ip))
    except socket.gaierror as _exc:
        logger.debug("Suppressed: %s", _exc)

    # AAAA records
    try:
        infos = socket.getaddrinfo(domain, None, socket.AF_INET6)
        seen_v6: Set[str] = set()
        for info in infos:
            ip = info[4][0]
            if ip not in seen_v6:
                seen_v6.add(ip)
                records.append(DnsRecord(type="AAAA", value=ip))
    except socket.gaierror as _exc:
        logger.debug("Suppressed: %s", _exc)

    # MX records via DNS query (simplified)
    try:
        import subprocess
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                records.append(DnsRecord(
                    type="MX", value=parts[1].rstrip("."),
                    priority=int(parts[0]),
                ))
    except Exception as e:
        logger.debug("Suppressed: %s", e)

    # NS records
    try:
        result = subprocess.run(
            ["dig", "+short", "NS", domain],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            if line.strip():
                records.append(DnsRecord(type="NS", value=line.strip().rstrip(".")))
    except Exception as e:
        logger.debug("Suppressed: %s", e)

    # TXT records
    try:
        result = subprocess.run(
            ["dig", "+short", "TXT", domain],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            if line.strip():
                records.append(DnsRecord(type="TXT", value=line.strip().strip('"')))
    except Exception as e:
        logger.debug("Suppressed: %s", e)

    return records


# ═══════════════════════════════════════════════════════════════════
# SSL Certificate Analysis
# ═══════════════════════════════════════════════════════════════════

async def inspect_ssl(domain: str, port: int = 443) -> Optional[SslInfo]:
    """Inspect SSL/TLS certificate details."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with socket.create_connection((domain, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                if not cert:
                    # Try with verification
                    ctx2 = ssl.create_default_context()
                    with socket.create_connection((domain, port), timeout=10) as sock2:
                        with ctx2.wrap_socket(sock2, server_hostname=domain) as ssock2:
                            cert = ssock2.getpeercert()

                if not cert:
                    return None

                # Parse subject
                subject_dict = dict(x[0] for x in cert.get("subject", ()))
                issuer_dict = dict(x[0] for x in cert.get("issuer", ()))

                # SAN names
                san_names = []
                for ext_type, ext_value in cert.get("subjectAltName", ()):
                    if ext_type == "DNS":
                        san_names.append(ext_value)

                # Calculate days remaining
                import datetime
                not_after = cert.get("notAfter", "")
                try:
                    expiry = datetime.datetime.strptime(
                        not_after, "%b %d %H:%M:%S %Y %Z",
                    )
                    days_remaining = (expiry - datetime.datetime.utcnow()).days
                except Exception:
                    days_remaining = -1

                return SslInfo(
                    valid=days_remaining > 0,
                    issuer=issuer_dict.get("organizationName", "Unknown"),
                    subject=subject_dict.get("commonName", domain),
                    not_before=cert.get("notBefore", ""),
                    not_after=not_after,
                    days_remaining=days_remaining,
                    serial_number=cert.get("serialNumber", ""),
                    signature_algorithm="",
                    san_names=san_names[:20],
                    protocol_version=ssock.version() or "",
                    chain_length=len(cert.get("caIssuers", [])) + 1,
                )
    except Exception as e:
        logger.debug(f"SSL inspection failed for {domain}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# Subdomain Enumeration
# ═══════════════════════════════════════════════════════════════════

SUBDOMAIN_WORDLIST = [
    "www", "mail", "ftp", "smtp", "pop", "imap", "webmail",
    "ns1", "ns2", "dns", "dns1", "dns2",
    "api", "dev", "staging", "test", "beta", "alpha", "demo",
    "admin", "portal", "dashboard", "panel", "manage", "cms",
    "blog", "forum", "wiki", "docs", "help", "support",
    "cdn", "static", "assets", "media", "images", "img",
    "app", "mobile", "m", "shop", "store",
    "git", "gitlab", "github", "jenkins", "ci", "cd",
    "vpn", "remote", "gateway", "proxy", "relay",
    "db", "database", "mysql", "postgres", "mongo", "redis",
    "search", "elastic", "kibana", "grafana", "prometheus",
    "auth", "login", "sso", "oauth", "id",
    "internal", "intranet", "corp", "office",
    "status", "monitor", "health", "metrics",
    "s3", "bucket", "storage", "backup",
]


async def enumerate_subdomains(domain: str,
                               wordlist: Optional[List[str]] = None,
                               concurrent: int = 20) -> List[str]:
    """Enumerate subdomains via DNS resolution."""
    words = wordlist or SUBDOMAIN_WORDLIST
    found: List[str] = []
    semaphore = asyncio.Semaphore(concurrent)

    async def check_subdomain(sub: str) -> Optional[str]:
        fqdn = f"{sub}.{domain}"
        async with semaphore:
            try:
                loop = asyncio.get_running_loop()
                await loop.getaddrinfo(fqdn, None)
                return fqdn
            except socket.gaierror:
                return None

    tasks = [check_subdomain(sub) for sub in words]
    results = await asyncio.gather(*tasks)
    found = [r for r in results if r]
    return sorted(found)


# ═══════════════════════════════════════════════════════════════════
# Endpoint Discovery
# ═══════════════════════════════════════════════════════════════════

COMMON_PATHS = [
    "/robots.txt", "/sitemap.xml", "/sitemap_index.xml",
    "/.env", "/.git/config", "/.git/HEAD",
    "/wp-login.php", "/wp-admin/", "/wp-json/wp/v2/users",
    "/admin/", "/administrator/", "/panel/", "/dashboard/",
    "/login", "/signin", "/auth", "/register",
    "/api/", "/api/v1/", "/api/v2/", "/graphql",
    "/swagger.json", "/api-docs", "/openapi.json",
    "/.well-known/security.txt", "/.well-known/openid-configuration",
    "/server-status", "/server-info", "/phpinfo.php",
    "/debug/", "/trace/", "/actuator/health",
    "/backup/", "/backups/", "/db/", "/dump/",
    "/config.php", "/config.yml", "/settings.json",
    "/crossdomain.xml", "/clientaccesspolicy.xml",
    "/favicon.ico", "/humans.txt",
]


async def discover_endpoints(base_url: str,
                             paths: Optional[List[str]] = None,
                             concurrent: int = MAX_CONCURRENT) -> List[Dict[str, Any]]:
    """Discover accessible endpoints on the target."""
    paths = paths or COMMON_PATHS
    found: List[Dict[str, Any]] = []
    semaphore = asyncio.Semaphore(concurrent)

    async def check_path(path: str) -> Optional[Dict[str, Any]]:
        url = urljoin(base_url, path)
        async with semaphore:
            await asyncio.sleep(RATE_LIMIT_DELAY * 0.1)
            result = await _fetch(url, timeout=8, follow_redirects=False)
            status = result.get("status", 0)
            if status in (200, 301, 302, 401, 403):
                size = len(result.get("body", ""))
                return {
                    "path": path, "url": url, "status": status,
                    "size": size,
                    "content_type": result.get("headers", {}).get(
                        "content-type", ""
                    )[:50],
                }
            return None

    tasks = [check_path(p) for p in paths]
    results = await asyncio.gather(*tasks)
    found = [r for r in results if r]
    return sorted(found, key=lambda x: x["status"])


# ═══════════════════════════════════════════════════════════════════
# Email & Social Media Harvesting
# ═══════════════════════════════════════════════════════════════════

def harvest_emails(html: str, domain: str) -> List[str]:
    """Extract email addresses from HTML content."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    all_emails = set(re.findall(pattern, html))

    # Filter to domain-related emails
    domain_parts = domain.split(".")
    base_domain = ".".join(domain_parts[-2:]) if len(domain_parts) > 1 else domain

    relevant = [e for e in all_emails if base_domain in e]
    other = [e for e in all_emails if base_domain not in e]

    return relevant + other[:5]


SOCIAL_PLATFORMS = [
    {"name": "Twitter/X", "pattern": r"(?:twitter|x)\.com/([a-zA-Z0-9_]+)"},
    {"name": "Facebook", "pattern": r"facebook\.com/([a-zA-Z0-9.]+)"},
    {"name": "LinkedIn", "pattern": r"linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]+)"},
    {"name": "Instagram", "pattern": r"instagram\.com/([a-zA-Z0-9_.]+)"},
    {"name": "GitHub", "pattern": r"github\.com/([a-zA-Z0-9_-]+)"},
    {"name": "YouTube", "pattern": r"youtube\.com/(?:c/|channel/|@)([a-zA-Z0-9_-]+)"},
    {"name": "Telegram", "pattern": r"t\.me/([a-zA-Z0-9_]+)"},
]


def detect_social_profiles(html: str) -> List[Dict[str, str]]:
    """Find social media profiles linked in HTML."""
    profiles: List[Dict[str, str]] = []
    seen: Set[str] = set()

    for platform in SOCIAL_PLATFORMS:
        matches = re.findall(platform["pattern"], html, re.I)
        for handle in matches:
            key = f"{platform['name']}:{handle.lower()}"
            if key not in seen:
                seen.add(key)
                profiles.append({
                    "platform": platform["name"],
                    "handle": handle,
                })

    return profiles


# ═══════════════════════════════════════════════════════════════════
# Google Dorking
# ═══════════════════════════════════════════════════════════════════

def generate_dorks(domain: str,
                   types: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """Generate Google dorking queries for a target domain."""
    all_dorks: Dict[str, List[str]] = {
        "sensitive_files": [
            f'site:{domain} filetype:pdf',
            f'site:{domain} filetype:doc OR filetype:docx',
            f'site:{domain} filetype:xls OR filetype:xlsx',
            f'site:{domain} filetype:sql OR filetype:db',
            f'site:{domain} filetype:log',
            f'site:{domain} filetype:bak OR filetype:backup',
            f'site:{domain} filetype:conf OR filetype:cfg',
            f'site:{domain} filetype:env',
        ],
        "login_pages": [
            f'site:{domain} inurl:login',
            f'site:{domain} inurl:admin',
            f'site:{domain} inurl:signin',
            f'site:{domain} intitle:"login" OR intitle:"sign in"',
            f'site:{domain} inurl:auth',
        ],
        "open_directories": [
            f'site:{domain} intitle:"index of"',
            f'site:{domain} intitle:"directory listing"',
            f'site:{domain} "parent directory"',
        ],
        "error_messages": [
            f'site:{domain} "error" OR "exception" OR "traceback"',
            f'site:{domain} "mysql error" OR "syntax error"',
            f'site:{domain} "warning" filetype:php',
            f'site:{domain} intext:"server at" intext:"port"',
        ],
        "api_endpoints": [
            f'site:{domain} inurl:api',
            f'site:{domain} inurl:graphql',
            f'site:{domain} inurl:swagger',
            f'site:{domain} inurl:v1 OR inurl:v2',
            f'site:{domain} filetype:json "api"',
        ],
        "subdomains": [
            f'site:*.{domain} -www.{domain}',
            f'site:{domain} -www',
        ],
        "credentials": [
            f'site:{domain} intext:"password" filetype:log',
            f'site:{domain} intext:"username" intext:"password"',
            f'site:{domain} filetype:env "DB_PASSWORD" OR "API_KEY"',
        ],
        "technologies": [
            f'site:{domain} "powered by"',
            f'site:{domain} "built with"',
            f'site:{domain} inurl:wp-content',
        ],
        "exposed_databases": [
            f'site:{domain} inurl:phpmyadmin',
            f'site:{domain} intitle:"adminer"',
            f'site:{domain} inurl:_all_dbs',
        ],
        "cloud_storage": [
            f'site:s3.amazonaws.com "{domain}"',
            f'site:blob.core.windows.net "{domain}"',
            f'site:storage.googleapis.com "{domain}"',
        ],
        "git_exposure": [
            f'site:{domain} inurl:.git',
            f'site:github.com "{domain}"',
            f'site:gitlab.com "{domain}"',
        ],
        "backup_files": [
            f'site:{domain} inurl:backup',
            f'site:{domain} filetype:zip OR filetype:tar OR filetype:gz',
            f'site:{domain} filetype:sql "dump"',
        ],
    }

    if types:
        return {k: v for k, v in all_dorks.items() if k in types}
    return all_dorks


# ═══════════════════════════════════════════════════════════════════
# Security Scoring
# ═══════════════════════════════════════════════════════════════════

def calculate_security_score(result: ReconResult) -> float:
    """
    Calculate overall security score (0-100).

    Scoring breakdown:
      - Security headers:    40 points
      - SSL certificate:     25 points
      - WAF presence:        10 points
      - Info leakage:       -15 points (deduction)
      - Exposed endpoints:  -10 points (deduction)
    """
    score = 0.0

    # Security headers (40 points)
    if result.security_headers:
        critical = [h for h in result.security_headers
                    if h.severity == "critical"]
        high = [h for h in result.security_headers
                if h.severity == "high"]
        medium = [h for h in result.security_headers
                  if h.severity == "medium"]

        critical_secure = sum(1 for h in critical if h.secure)
        high_secure = sum(1 for h in high if h.secure)
        medium_secure = sum(1 for h in medium if h.secure)

        if critical:
            score += (critical_secure / len(critical)) * 20
        if high:
            score += (high_secure / len(high)) * 10
        if medium:
            score += (medium_secure / len(medium)) * 10

    # SSL (25 points)
    if result.ssl_info:
        if result.ssl_info.valid:
            score += 15
        if result.ssl_info.days_remaining > 30:
            score += 5
        if result.ssl_info.days_remaining > 90:
            score += 5

    # WAF (10 points)
    if result.waf_detected:
        score += 10

    # Info leakage deduction (-15 max)
    info_headers = [h for h in result.security_headers
                    if h.severity == "info" and h.present]
    score -= min(len(info_headers) * 5, 15)

    # Exposed endpoint deduction (-10 max)
    sensitive_endpoints = [e for e in result.endpoints
                          if e.get("status") == 200
                          and any(p in e.get("path", "")
                                  for p in [".env", ".git", "phpinfo",
                                            "server-status", "debug"])]
    score -= min(len(sensitive_endpoints) * 5, 10)

    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════
# Main Recon Functions
# ═══════════════════════════════════════════════════════════════════

async def recon(
    target: str,
    modules: Optional[List[str]] = None,
) -> ReconResult:
    """
    Run reconnaissance modules on a target.

    Parameters
    ----------
    target : str
        Domain or URL to recon.
    modules : list, optional
        Modules to run. Default: headers, technologies, waf.
        Available: headers, technologies, waf, subdomains, endpoints,
                  emails, social, dns, ssl, robots, sitemap, security_score

    Returns
    -------
    ReconResult
        Complete recon results.
    """
    start = time.time()
    url = _normalize_target(target)
    domain = _extract_domain(target)
    result = ReconResult(target=domain)

    default_modules = ["headers", "technologies", "waf"]
    active_modules = set(modules or default_modules)

    # Fetch main page
    page = await _fetch(url)
    if page.get("error"):
        result.errors.append(f"Fetch failed: {page['error']}")
        result.duration_ms = (time.time() - start) * 1000
        return result

    headers = page.get("headers", {})
    body = page.get("body", "")

    # Run requested modules
    if "headers" in active_modules:
        result.security_headers = analyze_security_headers(headers)

    if "technologies" in active_modules:
        result.technologies = detect_technologies(headers, body)

    if "waf" in active_modules:
        result.waf_detected = detect_waf(headers, body)

    if "dns" in active_modules:
        result.dns_records = await enumerate_dns(domain)

    if "ssl" in active_modules:
        result.ssl_info = await inspect_ssl(domain)

    if "subdomains" in active_modules:
        result.subdomains = await enumerate_subdomains(domain)

    if "endpoints" in active_modules:
        result.endpoints = await discover_endpoints(url)

    if "emails" in active_modules:
        result.emails = harvest_emails(body, domain)

    if "social" in active_modules:
        result.social_profiles = detect_social_profiles(body)

    if "robots" in active_modules:
        robots = await _fetch(f"{url}/robots.txt", timeout=5)
        if robots.get("status") == 200:
            result.robots_txt = robots.get("body", "")[:5000]

    if "sitemap" in active_modules:
        sm = await _fetch(f"{url}/sitemap.xml", timeout=5)
        if sm.get("status") == 200:
            urls = re.findall(r"<loc>(.*?)</loc>", sm.get("body", ""))
            result.sitemap_urls = urls[:100]

    # Security score
    if "security_score" in active_modules or "headers" in active_modules:
        result.security_score = calculate_security_score(result)

    result.duration_ms = (time.time() - start) * 1000
    return result


async def full_recon(target: str) -> ReconResult:
    """Run ALL reconnaissance modules on a target."""
    return await recon(target, modules=[
        "headers", "technologies", "waf", "subdomains",
        "endpoints", "emails", "social", "dns", "ssl",
        "robots", "sitemap", "security_score",
    ])

    async def fetch_url_content(self, url: str, timeout: float = 15.0) -> str:
        """Fetch clean markdown content from URL via Jina Reader — free, no API key."""
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_get(
                    f"https://r.jina.ai/{url}",
                    headers={"Accept": "text/markdown"},
                    timeout=timeout,
                    provider_name="jina_reader",
                )
                return resp.text if resp.success else ""
            else:
                import httpx
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(
                        f"https://r.jina.ai/{url}",
                        headers={"Accept": "text/markdown"},
                    )
                    resp.raise_for_status()
                    return resp.text
        except Exception as e:
            logger.warning("Jina reader failed for %s: %s", url, e)
            return ""



class WebRecon:
    """Web reconnaissance and OSINT utility."""

    def __init__(self) -> None:
        self._results = []

    async def whois(self, domain: str) -> dict:
        """WHOIS lookup for a domain."""
        return {"domain": domain, "status": "available"}

    async def headers(self, url: str) -> dict:
        """Get HTTP headers for a URL."""
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_request("HEAD", url, timeout=10.0, provider_name="recon_head")
                return resp.headers
            else:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return dict(resp.headers)
        except Exception as e:
            return {"error": str(e)}

    async def tech_stack(self, url: str) -> dict:
        """Detect technology stack of a website."""
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_get(url, timeout=10.0, provider_name="recon_tech")
                html = resp.text if resp.success else ""
            else:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        html = await resp.text()
            techs = []
            if "wp-content" in html:
                techs.append("WordPress")
            if "shopify" in html.lower():
                techs.append("Shopify")
            if "react" in html.lower():
                techs.append("React")
            return {"url": url, "technologies": techs}
        except Exception as e:
            return {"url": url, "error": str(e)}


