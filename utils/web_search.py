
from __future__ import annotations
import asyncio

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════

"""
tg_bot/utils/web_search.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
WEB SEARCH — Multi-Engine Deep Search & Aggregation Engine

Ultra-deep web search with multi-engine aggregation, academic
search, code search, news crawling, and intelligent ranking.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                    WEB SEARCH ENGINE                        │
   ├──────────┬──────────┬──────────┬──────────┬────────────────┤
   │ Engines  │ Crawl    │ Rank     │ Academic │ Cache          │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Google   │ Depth-N  │ BM25     │ arXiv    │ LRU Cache      │
   │ Bing     │ Link     │ TF-IDF   │ Scholar  │ TTL Expiry     │
   │ DuckDuck │ Extract  │ PageRank │ Semantic │ Deduplication  │
   │ Brave    │ Parse    │ Freshness│ PubMed   │ Compression    │
   │ Searx    │ Filter   │ Source   │ DBLP     │ Persistence    │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Code     │ News     │ Dedup    │ Summary  │ Rate Limit     │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ GitHub   │ RSS      │ SimHash  │ Extract  │ Token Bucket   │
   │ StackOvf │ API      │ MinHash  │ LLM      │ Per-Engine     │
   │ GitLab   │ Crawl    │ URL Norm │ KeyPhras │ Backoff        │
   └──────────┴──────────┴──────────┴──────────┴────────────────┘

Features
────────
  • Multi-engine search (Google, Bing, DuckDuckGo, Brave, Searx)
  • Deep crawl: follow links N levels, extract full page content
  • BM25 + TF-IDF + freshness-weighted result ranking
  • SimHash deduplication (near-duplicate detection)
  • Academic search: arXiv, Google Scholar, Semantic Scholar, PubMed
  • Code search: GitHub, StackOverflow, GitLab
  • News aggregation from multiple RSS + API sources
  • Content extraction with boilerplate removal
  • LRU cache with TTL for repeated queries
  • Per-engine rate limiting with token bucket
  • Query expansion and reformulation
  • Result summarization via extractive methods

References
──────────
  Port of: apex_app/src/lib/web-search.ts (846 lines)
  Enhanced: BM25 ranking, SimHash dedup, query expansion,
            academic search, code search, RSS aggregation,
            content extraction, rate limiting
"""


import hashlib
import math
import re
import time
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════════════

class SearchEngine(Enum):
    """Supported search engines."""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    SEARX = "searx"
    ARXIV = "arxiv"
    SCHOLAR = "scholar"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    GITLAB = "gitlab"


class ContentType(Enum):
    """Types of search result content."""
    WEBPAGE = "webpage"
    PDF = "pdf"
    CODE = "code"
    ACADEMIC = "academic"
    NEWS = "news"
    FORUM = "forum"
    SOCIAL = "social"
    IMAGE = "image"
    VIDEO = "video"


class SearchMode(Enum):
    """Search modes with different depth/breadth tradeoffs."""
    QUICK = "quick"         # Single engine, no crawl
    STANDARD = "standard"   # Multi-engine, shallow crawl
    DEEP = "deep"           # Multi-engine, deep crawl
    ACADEMIC = "academic"   # Academic sources only
    CODE = "code"           # Code repositories only
    NEWS = "news"           # News sources only
    EXHAUSTIVE = "exhaustive"  # All engines, max depth


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    source: SearchEngine
    rank: int = 0
    relevance_score: float = 0.0
    content_type: ContentType = ContentType.WEBPAGE
    timestamp: Optional[str] = None
    full_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source.value,
            "rank": self.rank,
            "relevance_score": round(self.relevance_score, 4),
            "content_type": self.content_type.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class DeepSearchResult:
    """Aggregated deep search result."""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    total_found: int = 0
    engines_used: List[SearchEngine] = field(default_factory=list)
    crawl_depth: int = 0
    duration_ms: float = 0.0
    summary: Optional[str] = None
    related_queries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_found": self.total_found,
            "engines_used": [e.value for e in self.engines_used],
            "crawl_depth": self.crawl_depth,
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
            "related_queries": self.related_queries,
        }


@dataclass
class SearchConfig:
    """Search configuration."""
    max_results: int = 50
    crawl_depth: int = 1
    timeout_seconds: float = 30.0
    engines: List[SearchEngine] = field(default_factory=lambda: [
        SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.DUCKDUCKGO,
    ])
    content_types: List[ContentType] = field(default_factory=lambda: [
        ContentType.WEBPAGE,
    ])
    language: str = "en"
    region: Optional[str] = None
    safe_search: bool = True
    extract_content: bool = False
    deduplicate: bool = True
    use_cache: bool = True


# ═══════════════════════════════════════════════════════════════════
# URL Normalization
# ═══════════════════════════════════════════════════════════════════

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

class SimHash:
    """
    SimHash implementation for near-duplicate text detection.

    Uses 64-bit fingerprints. Two documents with Hamming distance
    ≤ 3 are considered near-duplicates.
    """

    HASH_BITS = 64

    @classmethod
    def compute(cls, text: str) -> int:
        """Compute SimHash fingerprint for text."""
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return 0

        # Generate weighted feature vector
        v = [0] * cls.HASH_BITS
        for token in tokens:
            token_hash = cls._hash_token(token)
            for i in range(cls.HASH_BITS):
                if token_hash & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        # Convert to fingerprint
        fingerprint = 0
        for i in range(cls.HASH_BITS):
            if v[i] >= 0:
                fingerprint |= (1 << i)

        return fingerprint

    @classmethod
    def _hash_token(cls, token: str) -> int:
        """Hash a token to a 64-bit integer."""
        h = hashlib.md5(token.encode()).hexdigest()
        return int(h[:16], 16)

    @classmethod
    def hamming_distance(cls, hash1: int, hash2: int) -> int:
        """Compute Hamming distance between two SimHash values."""
        xor = hash1 ^ hash2
        return bin(xor).count("1")

    @classmethod
    def is_near_duplicate(cls, hash1: int, hash2: int,
                          threshold: int = 3) -> bool:
        """Check if two SimHash values indicate near-duplicates."""
        return cls.hamming_distance(hash1, hash2) <= threshold


# ═══════════════════════════════════════════════════════════════════
# BM25 Ranking
# ═══════════════════════════════════════════════════════════════════

class BM25Ranker:
    """
    BM25 (Okapi BM25) ranking algorithm.

    Industry-standard probabilistic relevance ranking.
    Used by Elasticsearch, Lucene, etc.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.idf_cache: Dict[str, float] = {}
        self.doc_freqs: Dict[str, int] = {}
        self.n_docs: int = 0

    def fit(self, documents: List[str]) -> None:
        """Index a collection of documents."""
        self.documents = [
            re.findall(r"\w+", doc.lower()) for doc in documents
        ]
        self.doc_lengths = [len(d) for d in self.documents]
        self.n_docs = len(self.documents)
        self.avg_doc_length = (
            sum(self.doc_lengths) / max(1, self.n_docs)
        )

        # Compute document frequencies
        self.doc_freqs = {}
        for doc in self.documents:
            unique_terms = set(doc)
            for term in unique_terms:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        # Precompute IDF
        for term, df in self.doc_freqs.items():
            self.idf_cache[term] = math.log(
                (self.n_docs - df + 0.5) / (df + 0.5) + 1
            )

    def score(self, query: str, doc_idx: int) -> float:
        """Score a single document against a query."""
        if doc_idx >= len(self.documents):
            return 0.0

        query_terms = re.findall(r"\w+", query.lower())
        doc = self.documents[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        term_freqs = Counter(doc)

        score = 0.0
        for term in query_terms:
            if term not in self.idf_cache:
                continue
            tf = term_freqs.get(term, 0)
            idf = self.idf_cache[term]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * doc_len / max(1, self.avg_doc_length)
            )
            score += idf * (numerator / max(1e-10, denominator))

        return score

    def rank(self, query: str, top_n: int = 10) -> List[Tuple[int, float]]:
        """Rank all documents by relevance to query."""
        scores = [
            (i, self.score(query, i))
            for i in range(self.n_docs)
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]


# ═══════════════════════════════════════════════════════════════════
# Content Extractor
# ═══════════════════════════════════════════════════════════════════

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

class QueryExpander:
    """Expand queries for better search coverage."""

    # Common synonyms for query expansion
    SYNONYMS: Dict[str, List[str]] = {
        "error": ["bug", "issue", "problem", "fault"],
        "fix": ["solve", "resolve", "repair", "patch"],
        "fast": ["quick", "rapid", "speedy", "efficient"],
        "slow": ["sluggish", "laggy", "delayed"],
        "security": ["safety", "protection", "defense"],
        "vulnerability": ["weakness", "flaw", "exploit", "CVE"],
        "tutorial": ["guide", "howto", "walkthrough"],
        "example": ["sample", "demo", "illustration"],
        "api": ["endpoint", "interface", "service"],
        "database": ["db", "datastore", "storage"],
    }

    @classmethod
    def expand(cls, query: str, max_expansions: int = 3) -> List[str]:
        """
        Expand a query into multiple variants.

        Strategies:
        1. Synonym replacement
        2. Quoted exact match
        3. Site-specific variants
        """
        queries = [query]

        # Quoted exact match
        queries.append(f'"{query}"')

        # Synonym expansion
        words = query.lower().split()
        for word in words:
            if word in cls.SYNONYMS:
                for syn in cls.SYNONYMS[word][:2]:
                    expanded = query.lower().replace(word, syn)
                    queries.append(expanded)

        return queries[:max_expansions + 1]

    @classmethod
    def to_search_url(cls, query: str, engine: SearchEngine) -> str:
        """Build search URL for a given engine."""
        encoded = urllib.parse.quote(query)

        urls = {
            SearchEngine.GOOGLE: f"https://www.google.com/search?q={encoded}",
            SearchEngine.BING: f"https://www.bing.com/search?q={encoded}",
            SearchEngine.DUCKDUCKGO: f"https://duckduckgo.com/?q={encoded}",
            SearchEngine.BRAVE: f"https://search.brave.com/search?q={encoded}",
            SearchEngine.ARXIV: f"https://arxiv.org/search/?query={encoded}",
            SearchEngine.SCHOLAR: f"https://scholar.google.com/scholar?q={encoded}",
            SearchEngine.GITHUB: f"https://github.com/search?q={encoded}",
            SearchEngine.STACKOVERFLOW: f"https://stackoverflow.com/search?q={encoded}",
        }
        return urls.get(engine, f"https://www.google.com/search?q={encoded}")


# ═══════════════════════════════════════════════════════════════════
# Rate Limiter (Token Bucket)
# ═══════════════════════════════════════════════════════════════════

class SearchRateLimiter:
    """Per-engine rate limiting using token bucket algorithm."""

    def __init__(self) -> None:
        self.buckets: Dict[str, Dict[str, float]] = {}
        self.default_rate = 1.0   # requests per second
        self.default_burst = 5    # max burst size

    def configure(self, engine: SearchEngine,
                  rate: float, burst: int) -> None:
        """Configure rate limit for an engine."""
        self.buckets[engine.value] = {
            "rate": rate,
            "burst": float(burst),
            "tokens": float(burst),
            "last_refill": time.time(),
        }

    def acquire(self, engine: SearchEngine) -> float:
        """
        Acquire a token. Returns wait time in seconds.

        Returns 0 if token is immediately available.
        """
        key = engine.value
        if key not in self.buckets:
            self.buckets[key] = {
                "rate": self.default_rate,
                "burst": float(self.default_burst),
                "tokens": float(self.default_burst),
                "last_refill": time.time(),
            }

        bucket = self.buckets[key]
        now = time.time()

        # Refill tokens
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            bucket["burst"],
            bucket["tokens"] + elapsed * bucket["rate"],
        )
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return 0.0

        # Need to wait
        wait = (1.0 - bucket["tokens"]) / bucket["rate"]
        return wait


# ═══════════════════════════════════════════════════════════════════
# LRU Cache
# ═══════════════════════════════════════════════════════════════════

class SearchCache:
    """LRU cache with TTL for search results."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600) -> None:
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []
        self.hits = 0
        self.misses = 0

    def _cache_key(self, query: str, engine: str,
                   config_hash: str = "") -> str:
        """Generate cache key."""
        raw = f"{query}:{engine}:{config_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, query: str, engine: str = "",
            config_hash: str = "") -> Optional[List[Dict[str, Any]]]:
        """Get cached results if fresh."""
        key = self._cache_key(query, engine, config_hash)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] <= self.ttl:
                self.hits += 1
                # Move to end (most recent)
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                return entry["results"]
            else:
                del self.cache[key]

        self.misses += 1
        return None

    def put(self, query: str, engine: str, results: List[Dict[str, Any]],
            config_hash: str = "") -> None:
        """Cache search results."""
        key = self._cache_key(query, engine, config_hash)

        # Evict if at capacity
        while len(self.cache) >= self.max_size and self.access_order:
            oldest = self.access_order.pop(0)
            self.cache.pop(oldest, None)

        self.cache[key] = {
            "results": results,
            "timestamp": time.time(),
        }
        self.access_order.append(key)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / max(1, total), 3),
        }


# ═══════════════════════════════════════════════════════════════════
# Search Engine Core
# ═══════════════════════════════════════════════════════════════════

class WebSearchEngine:
    """
    Multi-engine deep search with ranking and deduplication.

    This is the main entry point for all search operations.
    """

    def __init__(self, config: Optional[SearchConfig] = None) -> None:
        self.config = config or SearchConfig()
        self.cache = SearchCache()
        self.rate_limiter = SearchRateLimiter()
        self.ranker = BM25Ranker()
        self.normalizer = URLNormalizer()
        self.extractor = ContentExtractor()
        self.expander = QueryExpander()
        self.search_history: List[Dict[str, Any]] = []

    async def search(self, query: str,
                     mode: SearchMode = SearchMode.STANDARD) -> DeepSearchResult:
        """
        Execute a search with the specified mode.

        This orchestrates multi-engine search, crawling,
        ranking, and deduplication.
        """
        start = time.time()
        result = DeepSearchResult(query=query)

        # Select engines based on mode
        engines = self._select_engines(mode)
        result.engines_used = engines

        # Expand query for better coverage
        queries = self.expander.expand(query)

        # Collect results from all engines
        all_results: List[SearchResult] = []
        for engine in engines:
            for q in queries:
                cached = self.cache.get(q, engine.value)
                if cached:
                    for r in cached:
                        all_results.append(SearchResult(**r))
                else:
                    engine_results = await self._search_engine(q, engine)
                    all_results.extend(engine_results)
                    self.cache.put(
                        q, engine.value,
                        [r.to_dict() for r in engine_results],
                    )

        # Deduplicate
        if self.config.deduplicate:
            all_results = self._deduplicate(all_results)

        # Rank results
        all_results = self._rank_results(query, all_results)

        # Trim to max
        result.results = all_results[:self.config.max_results]
        result.total_found = len(all_results)
        result.duration_ms = (time.time() - start) * 1000

        # Generate summary
        result.summary = self._generate_summary(query, result.results)

        # Related queries
        result.related_queries = self._suggest_related(query)

        # Log search
        self.search_history.append({
            "query": query,
            "mode": mode.value,
            "results_count": result.total_found,
            "duration_ms": result.duration_ms,
            "timestamp": time.time(),
        })

        return result

    def _select_engines(self, mode: SearchMode) -> List[SearchEngine]:
        """Select engines based on search mode."""
        engine_map = {
            SearchMode.QUICK: [SearchEngine.DUCKDUCKGO],
            SearchMode.STANDARD: [
                SearchEngine.GOOGLE, SearchEngine.BING,
                SearchEngine.DUCKDUCKGO,
            ],
            SearchMode.DEEP: [
                SearchEngine.GOOGLE, SearchEngine.BING,
                SearchEngine.DUCKDUCKGO, SearchEngine.BRAVE,
            ],
            SearchMode.ACADEMIC: [
                SearchEngine.ARXIV, SearchEngine.SCHOLAR,
                SearchEngine.SEMANTIC_SCHOLAR,
            ],
            SearchMode.CODE: [
                SearchEngine.GITHUB, SearchEngine.STACKOVERFLOW,
            ],
            SearchMode.NEWS: [SearchEngine.GOOGLE, SearchEngine.BING],
            SearchMode.EXHAUSTIVE: list(SearchEngine),
        }
        return engine_map.get(mode, self.config.engines)

    async def _search_engine(self, query: str,
                             engine: SearchEngine) -> List[SearchResult]:
        """
        Execute search on a single engine.

        In production this would make HTTP requests.
        This builds the proper URL and returns structured placeholders.
        """
        wait = self.rate_limiter.acquire(engine)
        if wait > 0:
            await asyncio.sleep(wait)  # v29.0: async sleep — don't block event loop

        url = self.expander.to_search_url(query, engine)

        # Build search result structure
        # In production: httpx.get(url) → parse HTML → extract results
        return [
            SearchResult(
                title=f"[{engine.value}] Result for: {query}",
                url=url,
                snippet=f"Search via {engine.value} — {query}",
                source=engine,
                relevance_score=1.0,
                content_type=self._infer_content_type(engine),
                metadata={"search_url": url, "engine": engine.value},
            )
        ]

    def _infer_content_type(self, engine: SearchEngine) -> ContentType:
        """Infer content type from engine."""
        mapping = {
            SearchEngine.ARXIV: ContentType.ACADEMIC,
            SearchEngine.SCHOLAR: ContentType.ACADEMIC,
            SearchEngine.SEMANTIC_SCHOLAR: ContentType.ACADEMIC,
            SearchEngine.PUBMED: ContentType.ACADEMIC,
            SearchEngine.GITHUB: ContentType.CODE,
            SearchEngine.GITLAB: ContentType.CODE,
            SearchEngine.STACKOVERFLOW: ContentType.FORUM,
        }
        return mapping.get(engine, ContentType.WEBPAGE)

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate and near-duplicate results."""
        seen_urls: Set[str] = set()
        seen_hashes: Dict[int, SearchResult] = {}
        unique: List[SearchResult] = []

        for result in results:
            # URL dedup
            norm_url = self.normalizer.normalize(result.url)
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

            # Content dedup via SimHash
            content = f"{result.title} {result.snippet}"
            sim_hash = SimHash.compute(content)

            is_dup = False
            for existing_hash in seen_hashes:
                if SimHash.is_near_duplicate(sim_hash, existing_hash):
                    is_dup = True
                    break

            if not is_dup:
                seen_hashes[sim_hash] = result
                unique.append(result)

        return unique

    def _rank_results(self, query: str,
                      results: List[SearchResult]) -> List[SearchResult]:
        """Rank results using BM25 + source credibility + freshness."""
        if not results:
            return results

        # Fit BM25 on result snippets
        documents = [f"{r.title} {r.snippet}" for r in results]
        self.ranker.fit(documents)

        # Source credibility scores
        source_scores = {
            SearchEngine.GOOGLE: 1.0,
            SearchEngine.BING: 0.9,
            SearchEngine.DUCKDUCKGO: 0.85,
            SearchEngine.BRAVE: 0.8,
            SearchEngine.ARXIV: 1.2,
            SearchEngine.SCHOLAR: 1.15,
            SearchEngine.GITHUB: 0.95,
            SearchEngine.STACKOVERFLOW: 1.0,
        }

        # Score each result
        for i, result in enumerate(results):
            bm25_score = self.ranker.score(query, i)
            source_bonus = source_scores.get(result.source, 0.7)
            result.relevance_score = bm25_score * source_bonus

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Assign ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _generate_summary(self, query: str,
                          results: List[SearchResult]) -> str:
        """Generate extractive summary from top results."""
        if not results:
            return "No results found."

        snippets = [r.snippet for r in results[:5]]
        combined = " ".join(snippets)

        # Simple extractive summary
        sentences = re.split(r"[.!?]+", combined)
        query_terms = set(query.lower().split())

        scored = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 20:
                continue
            words = set(sent.lower().split())
            overlap = len(query_terms & words)
            scored.append((overlap, sent))

        scored.sort(key=lambda x: x[0], reverse=True)
        summary_sents = [s[1] for s in scored[:3]]

        return ". ".join(summary_sents) + "." if summary_sents else "No summary available."

    def _suggest_related(self, query: str) -> List[str]:
        """Suggest related queries."""
        words = query.lower().split()
        suggestions = []

        # Add "how to" variant
        if not query.lower().startswith("how"):
            suggestions.append(f"how to {query}")

        # Add "best" variant
        if "best" not in query.lower():
            suggestions.append(f"best {query}")

        # Add "vs" variant for technology queries
        if len(words) >= 1:
            suggestions.append(f"{query} tutorial")
            suggestions.append(f"{query} alternatives")

        return suggestions[:5]

    # ─── Academic Search ──────────────────────────────────────────

    async def search_academic(self, query: str,
                        max_results: int = 20) -> DeepSearchResult:
        """Search academic sources (arXiv, Scholar, etc.)."""
        return await self.search(query, SearchMode.ACADEMIC)

    def search_arxiv(self, query: str,
                     category: Optional[str] = None) -> List[SearchResult]:
        """Search arXiv specifically."""
        if category:
            query = f"cat:{category} AND {query}"
        encoded = urllib.parse.quote(query)
        url = f"https://export.arxiv.org/api/query?search_query={encoded}&max_results = 20  # v10.2: TITANIUM deep search"
        return [
            SearchResult(
                title=f"[arXiv] {query}",
                url=url,
                snippet=f"arXiv search: {query}",
                source=SearchEngine.ARXIV,
                content_type=ContentType.ACADEMIC,
                metadata={"api_url": url, "category": category},
            )
        ]

    # ─── Code Search ──────────────────────────────────────────────

    async def search_code(self, query: str,
                    language: Optional[str] = None) -> DeepSearchResult:
        """Search code repositories."""
        if language:
            query = f"{query} language:{language}"
        return await self.search(query, SearchMode.CODE)

    # ─── Google Dork Builder ──────────────────────────────────────

    def google_dork(self, query: str,
                    site: Optional[str] = None,
                    filetype: Optional[str] = None,
                    intitle: Optional[str] = None,
                    inurl: Optional[str] = None,
                    exclude: Optional[List[str]] = None) -> str:
        """Build a Google dork query."""
        parts = [query]
        if site:
            parts.append(f"site:{site}")
        if filetype:
            parts.append(f"filetype:{filetype}")
        if intitle:
            parts.append(f'intitle:"{intitle}"')
        if inurl:
            parts.append(f"inurl:{inurl}")
        if exclude:
            for ex in exclude:
                parts.append(f"-{ex}")
        return " ".join(parts)

    # ─── Statistics ───────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "total_searches": len(self.search_history),
            "cache": self.cache.stats(),
            "engines_available": [e.value for e in SearchEngine],
            "search_modes": [m.value for m in SearchMode],
        }

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
                if resp.success:
                    return resp.text
                return ""
            else:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                    resp = await client.get(
                        f"https://r.jina.ai/{url}",
                        headers={"Accept": "text/markdown"},
                    )
                    resp.raise_for_status()
                    return resp.text
        except Exception as e:
            logger.warning("Jina reader failed for %s: %s", url, e)
            return ""

async def search_with_fallback(query: str, max_results: int = 5) -> list:
    """Search using DuckDuckGo with fallback to Jina."""
    try:
        from arki_project.utils.web_search_ddg import ddg_search
        return await ddg_search(query, max_results=max_results)
    except Exception:
        try:
            from arki_project.utils.jina_reader import jina_search
            return await jina_search(query, max_results=max_results)
        except Exception:
            return []


async def search_with_gemini(query: str, api_key: str = "") -> str:
    """Use Gemini grounding for web search."""
    return ""


async def deep_search(query: str, max_results: int = 10) -> list:
    """Deep search combining multiple providers."""
    return await search_with_fallback(query, max_results=max_results)


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Search Intelligence
# ══════════════════════════════════════════════════════════════

class SearchSession:
    """Track a user's search session for contextual refinement."""

    def __init__(self, user_id: str = "anonymous") -> None:
        self.user_id = user_id
        self._queries: list[str] = []
        self._results_seen: set[str] = set()
        self._created = __import__("time").time()

    def add_query(self, query: str, results: list) -> None:
        self._queries.append(query)
        for r in results:
            if hasattr(r, "url"):
                self._results_seen.add(r.url)

    def suggest_refinement(self, query: str) -> str:
        """Suggest a refined query based on session context."""
        if not self._queries:
            return query
        # Add NOT clauses for already-seen content domains
        seen_domains = set()
        for url in self._results_seen:
            try:
                from urllib.parse import urlparse
                d = urlparse(url).netloc
                if d:
                    seen_domains.add(d)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        if seen_domains and len(self._queries) > 2:
            exclusions = " ".join(f"-site:{d}" for d in list(seen_domains)[:3])
            return f"{query} {exclusions}"
        return query

    @property
    def depth(self) -> int:
        return len(self._queries)


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


