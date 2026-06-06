
"""
web_search_pkg/u_r_l_normalizer.py — URLNormalizer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class URLNormalizer:
    """Normalize URLs for deduplication and comparison."""

    # Tracking parameters to strip
    TRACKING_PARAMS: Set[str] = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term",
        "utm_content", "fbclid", "gclid", "gclsrc", "dclid",
        "zanpid", "msclkid", "mc_cid", "mc_eid", "ref",
        "_ga", "_gid", "yclid", "twclid", "spm",
    }

    @classmethod
    def normalize(cls, url: str) -> str:
        """Normalize a URL for comparison."""
        try:
            parsed = urllib.parse.urlparse(url.lower().strip())

            # Remove tracking parameters
            params = urllib.parse.parse_qs(parsed.query)
            clean_params = {
                k: v for k, v in params.items()
                if k.lower() not in cls.TRACKING_PARAMS
            }

            # Rebuild URL
            clean_query = urllib.parse.urlencode(clean_params, doseq=True)
            path = parsed.path.rstrip("/") or "/"

            return urllib.parse.urlunparse((
                parsed.scheme or "https",
                parsed.netloc,
                path,
                parsed.params,
                clean_query,
                "",  # remove fragment
            ))
        except Exception:
            return url


# ═══════════════════════════════════════════════════════════════════
# SimHash (Near-Duplicate Detection)
# ═══════════════════════════════════════════════════════════════════



