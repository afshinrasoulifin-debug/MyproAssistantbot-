
"""
web_search_pkg/content_extractor.py — ContentExtractor
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ContentExtractor:
    """Extract clean content from HTML with boilerplate removal."""

    # Tags that typically contain main content
    CONTENT_TAGS = {"p", "article", "section", "main", "div"}
    # Tags to remove entirely
    REMOVE_TAGS = {
        "script", "style", "nav", "footer", "header",
        "aside", "noscript", "iframe", "svg",
    }

    @classmethod
    def extract_text(cls, html: str) -> str:
        """Extract clean text from HTML."""
        # Remove tags we don't want
        for tag in cls.REMOVE_TAGS:
            html = re.sub(
                rf"<{tag}[^>]*>.*?</{tag}>",
                "", html, flags=re.DOTALL | re.IGNORECASE,
            )

        # Remove all remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Decode HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")

        # Clean whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def extract_links(cls, html: str, base_url: str = "") -> List[Dict[str, str]]:
        """Extract all links from HTML."""
        links = []
        for match in re.finditer(
            r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html, re.IGNORECASE | re.DOTALL,
        ):
            href = match.group(1)
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()

            if href.startswith("/") and base_url:
                href = base_url.rstrip("/") + href
            elif not href.startswith("http"):
                continue

            links.append({"url": href, "text": text})

        return links

    @classmethod
    def extract_metadata(cls, html: str) -> Dict[str, str]:
        """Extract metadata from HTML head."""
        meta: Dict[str, str] = {}

        # Title
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL,
        )
        if title_match:
            meta["title"] = title_match.group(1).strip()

        # Meta tags
        for match in re.finditer(
            r'<meta\s+[^>]*(?:name|property)=["\']([^"\']+)["\']'
            r'[^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        ):
            meta[match.group(1)] = match.group(2)

        return meta


# ═══════════════════════════════════════════════════════════════════
# Query Expansion
# ═══════════════════════════════════════════════════════════════════



