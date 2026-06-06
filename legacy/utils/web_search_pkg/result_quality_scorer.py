
"""
web_search_pkg/result_quality_scorer.py — ResultQualityScorer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ResultQualityScorer:
    """Score search result quality for ranking."""

    # Domain authority tiers
    TIER_1 = {"github.com", "stackoverflow.com", "docs.python.org", "arxiv.org",
              "developer.mozilla.org", "en.wikipedia.org", "medium.com"}
    TIER_2 = {"dev.to", "realpython.com", "towardsdatascience.com", "hackernoon.com"}

    @classmethod
    def score(cls, url: str, title: str, snippet: str) -> float:
        """Score a result 0.0-1.0 based on quality signals."""
        score = 0.5  # Base score

        # Domain authority
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            if domain in cls.TIER_1:
                score += 0.3
            elif domain in cls.TIER_2:
                score += 0.15
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        # Content signals
        if len(snippet) > 100:
            score += 0.1
        if len(title) > 20:
            score += 0.05

        # Freshness signals (year in title)
        import re
        years = re.findall(r"20[2-3]\d", title)
        if years:
            score += 0.05

        return min(score, 1.0)



