
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/search_privacy.py — Search Privacy Layer v3.3
═══════════════════════════════════════════════════════════════
Strips tracking parameters, anonymizes queries, and ensures
search requests can't be traced back to individual users.
"""
import hashlib, logging, re, time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

# Known tracking parameters to strip from URLs
TRACKING_PARAMS = {
    # Google
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "gclsrc", "dclid", "gbraid", "wbraid",
    # Facebook
    "fbclid", "fb_action_ids", "fb_action_types", "fb_ref", "fb_source",
    # Microsoft
    "msclkid",
    # General
    "ref", "ref_", "referrer", "source", "campaign_id",
    "mc_cid", "mc_eid",  # Mailchimp
    "yclid",  # Yandex
    "_hsenc", "_hsmi", "hsa_cam",  # HubSpot
    "igshid",  # Instagram
    "si",  # Spotify
    "feature", "app",  # YouTube
    "s_kwcid", "ef_id",  # Adobe
    "wickedid", "wicked_source",
    # Analytics
    "_ga", "_gl", "_gid", "ga_source", "ga_medium",
    "click_id", "clickid", "tracking_id",
}

# Patterns that indicate a redirect/tracking URL
REDIRECT_PATTERNS = [
    r"google\.com/url\?",
    r"facebook\.com/l\.php",
    r"t\.co/",
    r"bit\.ly/",
    r"linktr\.ee/",
    r"click\..*\.com",
    r"track\.",
    r"redirect\.",
]

def strip_tracking_params(url: str) -> str:
    """Remove all known tracking parameters from URL."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=False)
        clean_params = {
            k: v for k, v in params.items()
            if k.lower() not in TRACKING_PARAMS
        }
        clean_query = urlencode(clean_params, doseq=True)
        # Also strip fragment tracking
        fragment = parsed.fragment
        if any(t in fragment.lower() for t in ["utm", "ref", "track", "campaign"]):
            fragment = ""
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, clean_query, fragment,
        ))
    except ArkiBaseError:
        return url

def clean_urls_in_text(text: str) -> str:
    """Find and clean all URLs in text."""
    url_pattern = r'https?://[^\s<>"\'\)\]]+' 
    def replacer(match: Any) -> Any:
        return strip_tracking_params(match.group(0))
    return re.sub(url_pattern, replacer, text)

def is_tracking_redirect(url: str) -> bool:
    """Check if URL is a known tracking redirect."""
    for pattern in REDIRECT_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def extract_real_url(redirect_url: str) -> str:
    """Try to extract the real destination from a redirect URL."""
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    # Common redirect param names
    for key in ["url", "u", "q", "dest", "destination", "target", "redirect", "goto"]:
        if key in params:
            return params[key][0]
    return redirect_url

def anonymize_search_query(query: str) -> str:
    """Remove potential PII from search queries before sending to engines."""
    # Strip email patterns
    query = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', query)
    # Strip phone patterns
    query = re.sub(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[PHONE]', query)
    # Strip IP addresses
    query = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', query)
    return query

def get_anonymous_headers() -> Dict[str, str]:
    """Generate headers that minimize tracking."""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

def clean_search_results(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Clean all URLs in search results."""
    cleaned = []
    for r in results:
        url = r.get("url", "")
        if is_tracking_redirect(url):
            url = extract_real_url(url)
        url = strip_tracking_params(url)
        cleaned.append({**r, "url": url})
    return cleaned


class SearchPrivacyLayer:
    """Wraps search operations with privacy protections."""

    def __init__(self) -> None:
        self._query_hashes: Dict[str, float] = {}
        self._stats = {"queries_anonymized": 0, "urls_cleaned": 0, "redirects_resolved": 0}

    def prepare_query(self, query: str, user_id: int = 0) -> str:
        """Anonymize query and track without storing raw text."""
        clean = anonymize_search_query(query)
        self._stats["queries_anonymized"] += 1
        # Store only hash for dedup, never raw query
        qhash = hashlib.sha256(f"{user_id}:{clean}".encode()).hexdigest()[:16]
        self._query_hashes[qhash] = time.time()
        return clean

    def clean_results(self, results: List[Dict]) -> List[Dict]:
        """Strip tracking from all result URLs."""
        cleaned = clean_search_results(results)
        self._stats["urls_cleaned"] += len(results)
        return cleaned

    def get_headers(self) -> Dict[str, str]:
        return get_anonymous_headers()

    @property
    def stats(self) -> Dict[str, Any]:
        return {**self._stats, "unique_queries": len(self._query_hashes)}


_privacy: Optional[SearchPrivacyLayer] = None
def get_search_privacy() -> SearchPrivacyLayer:
    global _privacy
    if _privacy is None:
        _privacy = SearchPrivacyLayer()
    return _privacy


