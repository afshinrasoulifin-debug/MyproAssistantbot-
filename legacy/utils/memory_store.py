
"""
tg_bot/utils/memory_store.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
MEMORY STORE — Long-Term Memory Engine with RAG Pipeline

Persistent memory system enabling Arki to remember across conversations
with semantic search, user profiling, and knowledge management.

Architecture
────────────
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ Store      │───▶│ TF-IDF     │───▶│ Index      │
  │ (memories) │    │ Vectorizer │    │ (search)   │
  └────────────┘    └────────────┘    └────────────┘
        │                                    │
        ▼                                    ▼
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ User       │    │ Auto-Tag   │    │ RAG        │
  │ Profiles   │    │ Engine     │    │ Pipeline   │
  └────────────┘    └────────────┘    └────────────┘
        │                                    │
        ▼                                    ▼
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │ Style      │    │ Forgetting │    │ Context    │
  │ Learning   │    │ Curve      │    │ Builder    │
  └────────────┘    └────────────┘    └────────────┘

Features
────────
  • TF-IDF vector similarity search (no external deps)
  • BM25 scoring as alternative ranking method
  • RAG context builder with token budget management
  • User profiles with style learning (formality, verbosity, technicality)
  • 8 memory types: conversation, fact, preference, skill, result,
    summary, personality, instruction
  • Auto-tagging from content analysis (20+ topic patterns)
  • Importance estimation with content heuristics
  • Memory consolidation (merge highly similar memories)
  • Forgetting curve (Ebbinghaus-inspired decay)
  • Recency & frequency boosting in search
  • Per-user memory isolation
  • JSON export/import with full state preservation
  • Memory statistics & health monitoring
  • Conversation summarization hooks

References
──────────
  Port of: apex_app/src/lib/memory-store.ts (602 lines)
  Enhanced with: BM25 scoring, richer auto-tagger, forgetting curve math,
                 style learning with EMA, memory health stats
"""

from __future__ import annotations

import hashlib
import json
import aiofiles
import logging
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

DEFAULT_MAX_MEMORIES            = 100_000
DEFAULT_MAX_PER_USER            = 10_000
DEFAULT_CONSOLIDATION_THRESHOLD = 0.85
DEFAULT_FORGETTING_RATE         = 0.01      # per hour
DEFAULT_STORAGE_PATH            = os.environ.get("MEMORY_FILE", "./data/memory.json")
RAG_DEFAULT_MAX_TOKENS          = 8000
BM25_K1                         = 1.5
BM25_B                          = 0.75
STYLE_EMA_ALPHA                 = 0.1       # exponential moving average factor
MAX_TAGS_PER_MEMORY             = 15
MAX_TOPICS_PER_USER             = 500


# ═══════════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════════

class MemoryType(str, Enum):
    CONVERSATION    = "conversation"
    FACT            = "fact"
    PREFERENCE      = "preference"
    SKILL           = "skill"
    RESULT          = "result"
    SUMMARY         = "summary"
    PERSONALITY     = "personality"
    INSTRUCTION     = "instruction"


@dataclass
class MemoryMetadata:
    """Metadata attached to each memory entry."""
    source: str = ""
    model: str = ""
    confidence: float = 0.0
    topic: str = ""
    language: str = ""
    sentiment: str = ""             # positive | negative | neutral
    word_count: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "source": self.source, "model": self.model,
            "confidence": self.confidence, "topic": self.topic,
            "language": self.language, "sentiment": self.sentiment,
            "word_count": self.word_count,
        }
        d.update(self.extra)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryMetadata":
        known = {"source", "model", "confidence", "topic", "language",
                 "sentiment", "word_count"}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(
            source=d.get("source", ""),
            model=d.get("model", ""),
            confidence=d.get("confidence", 0.0),
            topic=d.get("topic", ""),
            language=d.get("language", ""),
            sentiment=d.get("sentiment", ""),
            word_count=d.get("word_count", 0),
            extra=extra,
        )


@dataclass
class Memory:
    """A single memory entry."""
    id: str
    type: MemoryType
    content: str
    summary: str = ""
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)
    embedding: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    user_id: str = ""
    conversation_id: str = ""

    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    def staleness_hours(self) -> float:
        return (time.time() - self.last_accessed_at) / 3600

    def retention_score(self, forgetting_rate: float = DEFAULT_FORGETTING_RATE) -> float:
        """
        Ebbinghaus-inspired retention score.
        Higher importance + more access = longer retention.
        """
        freq_boost = 1 + math.log(self.access_count + 1)
        decay = math.exp(-self.staleness_hours() * forgetting_rate)
        return self.importance * freq_boost * decay

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type.value,
            "content": self.content, "summary": self.summary,
            "metadata": self.metadata.to_dict(),
            "embedding": self.embedding,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "importance": self.importance,
            "tags": self.tags, "user_id": self.user_id,
            "conversation_id": self.conversation_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Memory":
        return cls(
            id=d["id"], type=MemoryType(d["type"]),
            content=d["content"], summary=d.get("summary", ""),
            metadata=MemoryMetadata.from_dict(d.get("metadata", {})),
            embedding=d.get("embedding", []),
            created_at=d.get("created_at", time.time()),
            last_accessed_at=d.get("last_accessed_at", time.time()),
            access_count=d.get("access_count", 0),
            importance=d.get("importance", 0.5),
            tags=d.get("tags", []), user_id=d.get("user_id", ""),
            conversation_id=d.get("conversation_id", ""),
        )


@dataclass
class UserProfile:
    """Tracks user behavior, preferences, and communication style."""
    user_id: str
    display_name: str = ""
    language: str = ""
    preferences: Dict[str, Any] = field(default_factory=dict)
    topics: List[Dict[str, Any]] = field(default_factory=list)
    style: Dict[str, float] = field(default_factory=lambda: {
        "formality": 0.5,
        "verbosity": 0.5,
        "technicality": 0.5,
        "emotionality": 0.5,
        "avg_message_length": 50.0,
    })
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    total_interactions: int = 0
    memory_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "language": self.language,
            "preferences": self.preferences,
            "topics": self.topics,
            "style": self.style,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "total_interactions": self.total_interactions,
            "memory_ids": self.memory_ids,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    """A single search result with score and explanation."""
    memory: Memory
    score: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory.id,
            "score": round(self.score, 4),
            "reason": self.reason,
            "type": self.memory.type.value,
            "content_preview": self.memory.content[:200],
        }


# ═══════════════════════════════════════════════════════════════════
# TF-IDF Vector Engine (No External Dependencies)
# ═══════════════════════════════════════════════════════════════════

class TFIDFEngine:
    """
    Pure-Python TF-IDF implementation with cosine similarity.
    Supports incremental document addition and on-the-fly queries.
    """

    # Common stop words (English + Persian)
    STOP_WORDS: Set[str] = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "must", "can", "could", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "out",
        "about", "than", "that", "this", "these", "those", "it", "its",
        "and", "but", "or", "nor", "not", "no", "so", "if", "then",
        "which", "who", "whom", "what", "where", "when", "how", "all",
        "each", "every", "both", "few", "more", "most", "other", "some",
        "such", "only", "same", "also", "just", "very", "too",
        # Persian
        "و", "در", "به", "از", "که", "این", "را", "با", "است", "آن",
        "یک", "بر", "هم", "تا", "برای", "نیز", "شده", "می", "ها",
    }

    def __init__(self) -> None:
        self._vocabulary: Dict[str, int] = {}      # word → index
        self._idf: Dict[str, float] = {}            # word → IDF score
        self._document_count: int = 0
        self._document_freq: Dict[str, int] = defaultdict(int)  # word → doc count

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into normalized words, removing stop words."""
        text = text.lower()
        text = re.sub(r"[^\w\s\u0600-\u06FF\u4e00-\u9fff]", " ", text)
        tokens = text.split()
        return [t for t in tokens if len(t) > 2 and t not in self.STOP_WORDS]

    def add_document(self, text: str) -> List[float]:
        """Add a document, update IDF, return TF-IDF vector."""
        tokens = self._tokenize(text)
        self._document_count += 1

        # Update document frequency
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self._document_freq[token] += 1
            if token not in self._vocabulary:
                self._vocabulary[token] = len(self._vocabulary)

        # Recompute IDF for all terms
        for word, df in self._document_freq.items():
            self._idf[word] = math.log((self._document_count + 1) / (df + 1)) + 1

        return self._compute_vector(tokens)

    def _compute_vector(self, tokens: Union[List[str], str]) -> List[float]:
        """Compute TF-IDF vector for a set of tokens."""
        if isinstance(tokens, str):
            tokens = self._tokenize(tokens)

        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        vector = [0.0] * len(self._vocabulary)
        for word, count in tf.items():
            idx = self._vocabulary.get(word)
            if idx is not None:
                normalized_tf = count / max(1, max_tf)
                idf_score = self._idf.get(word, 1.0)
                vector[idx] = normalized_tf * idf_score

        return vector

    def query_vector(self, text: str) -> List[float]:
        """Compute vector for a query string (does not add to corpus)."""
        return self._compute_vector(text)

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Cosine similarity between two vectors."""
        max_len = max(len(a), len(b))
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0

        for i in range(max_len):
            ai = a[i] if i < len(a) else 0.0
            bi = b[i] if i < len(b) else 0.0
            dot += ai * bi
            norm_a += ai * ai
            norm_b += bi * bi

        denom = math.sqrt(norm_a) * math.sqrt(norm_b)
        return dot / max(1e-10, denom) if denom > 0 else 0.0

    def bm25_score(self, query_tokens: List[str], doc_tokens: List[str],
                   avg_doc_len: float) -> float:
        """BM25 relevance score (Okapi BM25)."""
        doc_tf = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        score = 0.0

        for term in set(query_tokens):
            if term not in self._document_freq:
                continue
            tf = doc_tf.get(term, 0)
            df = self._document_freq[term]
            idf = math.log((self._document_count - df + 0.5) / (df + 0.5) + 1)
            tf_norm = (tf * (BM25_K1 + 1)) / (
                tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / max(avg_doc_len, 1))
            )
            score += idf * tf_norm

        return score

    @property
    def vocab_size(self) -> int:
        return len(self._vocabulary)

    @property
    def doc_count(self) -> int:
        return self._document_count


# ═══════════════════════════════════════════════════════════════════
# Auto-Tagging Engine
# ═══════════════════════════════════════════════════════════════════

# Pattern → tag mapping (expanded from TS original)
TAG_PATTERNS: List[Dict[str, Any]] = [
    {"tag": "code",       "patterns": [r"```", r"\bfunction\s", r"\bclass\s", r"\bimport\s",
                                       r"\bdef\s", r"\bconst\s", r"\blet\s", r"\bvar\s",
                                       r"\basync\s", r"\bawait\b"]},
    {"tag": "security",   "patterns": [r"\bsecurity\b", r"\bvuln", r"\bexploit\b",
                                       r"\bhack\b", r"\bpentest\b", r"\bfirewall\b",
                                       r"\binjection\b", r"\bxss\b", r"\bsqli\b"]},
    {"tag": "networking", "patterns": [r"\bport\b", r"\btcp\b", r"\budp\b", r"\bdns\b",
                                       r"\bhttp\b", r"\bip\s", r"\bsubnet\b", r"\bsocket\b"]},
    {"tag": "web",        "patterns": [r"\bwebsite\b", r"\bhtml\b", r"\bcss\b",
                                       r"\bjavascript\b", r"\breact\b", r"\bvue\b",
                                       r"\bangular\b", r"\bfrontend\b"]},
    {"tag": "api",        "patterns": [r"\bapi\b", r"\bendpoint\b", r"\brest\b",
                                       r"\bgraphql\b", r"\bgrpc\b", r"\bwebhook\b"]},
    {"tag": "database",   "patterns": [r"\bdatabase\b", r"\bsql\b", r"\bmongodb\b",
                                       r"\bredis\b", r"\bpostgres\b", r"\bmysql\b",
                                       r"\bsqlite\b"]},
    {"tag": "ai",         "patterns": [r"\bai\b", r"\bmachine.?learning\b", r"\bneural\b",
                                       r"\bmodel\b", r"\bgpt\b", r"\bllm\b", r"\btransformer\b",
                                       r"\bembedding\b", r"\bvector\b"]},
    {"tag": "crypto",     "patterns": [r"\bencrypt", r"\bdecrypt", r"\bcipher\b",
                                       r"\bhash\b", r"\btoken\b", r"\baes\b",
                                       r"\brsa\b", r"\bhmac\b"]},
    {"tag": "devops",     "patterns": [r"\bdocker\b", r"\bkubernetes\b", r"\bdeploy\b",
                                       r"\bci.?cd\b", r"\bpipeline\b", r"\bterraform\b"]},
    {"tag": "linux",      "patterns": [r"\blinux\b", r"\bubuntu\b", r"\bbash\b",
                                       r"\bterminal\b", r"\bshell\b", r"\bsudo\b"]},
    {"tag": "python",     "patterns": [r"\bpython\b", r"\bpip\b", r"\bdjango\b",
                                       r"\bflask\b", r"\bfastapi\b"]},
    {"tag": "data",       "patterns": [r"\bdata\b", r"\bcsv\b", r"\bjson\b", r"\bexcel\b",
                                       r"\bpandas\b", r"\banalysis\b", r"\bstatistics\b"]},
    {"tag": "automation", "patterns": [r"\bautomation\b", r"\bscript\b", r"\bcron\b",
                                       r"\bscheduler\b", r"\bworkflow\b"]},
    {"tag": "finance",    "patterns": [r"\bfinance\b", r"\btrading\b", r"\bstock\b",
                                       r"\bcrypto\b", r"\bbitcoin\b", r"\bpayment\b"]},
    {"tag": "math",       "patterns": [r"\bmath\b", r"\bequation\b", r"\bformula\b",
                                       r"\bcalculate\b", r"\balgebra\b", r"\bcalculus\b"]},
    {"tag": "image",      "patterns": [r"\bimage\b", r"\bphoto\b", r"\bpicture\b",
                                       r"\bpng\b", r"\bjpeg\b", r"\bsvg\b"]},
    {"tag": "audio",      "patterns": [r"\baudio\b", r"\bvoice\b", r"\bspeech\b",
                                       r"\bmp3\b", r"\bwav\b", r"\btranscri"]},
    {"tag": "research",   "patterns": [r"\bresearch\b", r"\bpaper\b", r"\bstudy\b",
                                       r"\bacademic\b", r"\bjournal\b", r"\bcitation\b"]},
    {"tag": "testing",    "patterns": [r"\btest\b", r"\bunit.?test\b", r"\bpytest\b",
                                       r"\bjest\b", r"\bcoverage\b", r"\bqa\b"]},
    {"tag": "mobile",     "patterns": [r"\bmobile\b", r"\bandroid\b", r"\bios\b",
                                       r"\bswift\b", r"\bkotlin\b", r"\bflutter\b"]},
]


def auto_tag(content: str) -> List[str]:
    """Extract tags from content using pattern matching."""
    lower = content.lower()
    tags: List[str] = []

    for entry in TAG_PATTERNS:
        if any(re.search(p, lower) for p in entry["patterns"]):
            tags.append(entry["tag"])

    return tags[:MAX_TAGS_PER_MEMORY]


def detect_language(text: str) -> str:
    """Simple language detection based on character ranges."""
    has_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", text))
    has_hangul = bool(re.search(r"[\uac00-\ud7af]", text))
    has_thai = bool(re.search(r"[\u0e00-\u0e7f]", text))

    if has_arabic:
        return "Arabic/Persian"
    elif has_cjk:
        return "Chinese"
    elif has_cyrillic:
        return "Russian/Cyrillic"
    elif has_hangul:
        return "Korean"
    elif has_thai:
        return "Thai"
    else:
        return "English/Latin"


def detect_sentiment(text: str) -> str:
    """Simple keyword-based sentiment detection."""
    lower = text.lower()
    pos_words = {"good", "great", "excellent", "amazing", "awesome", "love",
                 "happy", "perfect", "best", "wonderful", "fantastic", "thank",
                 "عالی", "ممنون", "خوب", "عالیه", "بهترین"}
    neg_words = {"bad", "terrible", "awful", "hate", "worst", "horrible",
                 "angry", "frustrated", "annoying", "stupid", "broken",
                 "بد", "افتضاح", "ضعیف", "مزخرف"}

    words = set(re.findall(r"\w+", lower))
    pos = len(words & pos_words)
    neg = len(words & neg_words)

    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


# ═══════════════════════════════════════════════════════════════════
# Importance Estimation
# ═══════════════════════════════════════════════════════════════════

def estimate_importance(content: str, mem_type: MemoryType) -> float:
    """
    Estimate memory importance 0-1 based on type and content signals.
    """
    # Type-based baseline
    type_scores: Dict[MemoryType, float] = {
        MemoryType.INSTRUCTION:   0.90,
        MemoryType.PREFERENCE:    0.80,
        MemoryType.SKILL:         0.75,
        MemoryType.FACT:          0.70,
        MemoryType.PERSONALITY:   0.70,
        MemoryType.SUMMARY:       0.60,
        MemoryType.RESULT:        0.50,
        MemoryType.CONVERSATION:  0.40,
    }
    importance = type_scores.get(mem_type, 0.50)

    # Content-based adjustments
    lower = content.lower()

    # Length bonus (longer = likely more detailed)
    if len(content) > 500:
        importance += 0.05
    if len(content) > 1000:
        importance += 0.05

    # Urgency/importance keywords
    urgency_words = {"important", "critical", "always", "never", "must",
                     "required", "essential", "urgent", "priority",
                     "مهم", "ضروری", "حتما", "فوری"}
    if any(w in lower for w in urgency_words):
        importance += 0.10

    # Contains code (structured information)
    if "```" in content or re.search(r"\bdef\s|\bclass\s|\bfunction\s", content):
        importance += 0.05

    # Contains URLs (external references)
    if re.search(r"https?://", content):
        importance += 0.03

    # Contains numbers/data
    if re.search(r"\d{3,}", content):
        importance += 0.02

    return min(importance, 1.0)


# ═══════════════════════════════════════════════════════════════════
# Memory Store — Core Engine
# ═══════════════════════════════════════════════════════════════════

class MemoryStore:
    """
    Central memory management system with TF-IDF search,
    user profiling, auto-tagging, and RAG pipeline.
    """

    def __init__(
        self,
        max_memories: int = DEFAULT_MAX_MEMORIES,
        max_per_user: int = DEFAULT_MAX_PER_USER,
        consolidation_threshold: float = DEFAULT_CONSOLIDATION_THRESHOLD,
        forgetting_rate: float = DEFAULT_FORGETTING_RATE,
        auto_summarize: bool = True,
        storage_path: str = DEFAULT_STORAGE_PATH,
    ) -> None:
        self._memories: Dict[str, Memory] = {}
        self._user_profiles: Dict[str, UserProfile] = {}
        self._tfidf = TFIDFEngine()

        self._max_memories = max_memories
        self._max_per_user = max_per_user
        self._consolidation_threshold = consolidation_threshold
        self._forgetting_rate = forgetting_rate
        self._auto_summarize = auto_summarize
        self._storage_path = storage_path

        # Statistics
        self._total_stores = 0
        self._total_searches = 0
        self._total_consolidations = 0
        self._total_evictions = 0

    # ── Store ──────────────────────────────────────────────────────

    def store(
        self,
        content: str,
        mem_type: MemoryType,
        user_id: str = "",
        conversation_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None,
        summary: str = "",
    ) -> Memory:
        """
        Store a new memory. Auto-tags, computes embedding,
        updates user profile, consolidates duplicates.
        """
        mem_id = f"mem_{int(time.time()*1000)}_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"

        # Build metadata
        meta = MemoryMetadata.from_dict(metadata or {})
        meta.word_count = len(content.split())
        if not meta.language:
            meta.language = detect_language(content)
        if not meta.sentiment:
            meta.sentiment = detect_sentiment(content)

        # Auto-tag
        computed_tags = tags if tags else auto_tag(content)

        # Compute embedding
        embedding = self._tfidf.add_document(content)

        # Estimate importance
        imp = importance if importance is not None else estimate_importance(content, mem_type)

        memory = Memory(
            id=mem_id,
            type=mem_type,
            content=content,
            summary=summary,
            metadata=meta,
            embedding=embedding,
            importance=imp,
            tags=computed_tags,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        self._memories[mem_id] = memory
        self._total_stores += 1

        # Update user profile
        if user_id:
            self._update_user_profile(user_id, memory)

        # Evict if over limit
        if len(self._memories) > self._max_memories:
            self._evict_old_memories()

        # Consolidate duplicates
        if self._auto_summarize:
            self._maybe_consolidate(memory)

        logger.debug(f"Stored memory {mem_id} [{mem_type.value}] "
                     f"tags={computed_tags} imp={imp:.2f}")
        return memory

    # ── Search ─────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        mem_type: Optional[Union[MemoryType, List[MemoryType]]] = None,
        min_importance: float = 0.0,
        tags: Optional[List[str]] = None,
        recency_weight: float = 0.3,
        method: str = "tfidf",          # "tfidf" or "bm25"
    ) -> List[SearchResult]:
        """
        Search memories by semantic similarity with optional filters.

        Parameters
        ----------
        query : str
            Search query text.
        limit : int
            Maximum results to return.
        user_id : str, optional
            Filter to specific user.
        mem_type : MemoryType or list, optional
            Filter to specific memory types.
        min_importance : float
            Minimum importance threshold.
        tags : list, optional
            Filter to memories with any of these tags.
        recency_weight : float
            How much to boost recent memories (0=ignore, 1=strong).
        method : str
            Scoring method: "tfidf" (cosine) or "bm25".
        """
        self._total_searches += 1
        query_vector = self._tfidf.query_vector(query)
        query_tokens = self._tfidf._tokenize(query)

        # Compute average doc length for BM25
        avg_doc_len = (sum(m.metadata.word_count for m in self._memories.values())
                       / max(len(self._memories), 1))

        results: List[SearchResult] = []

        for memory in self._memories.values():
            # Apply filters
            if user_id and memory.user_id != user_id:
                continue
            if mem_type:
                types = [mem_type] if isinstance(mem_type, MemoryType) else mem_type
                if memory.type not in types:
                    continue
            if memory.importance < min_importance:
                continue
            if tags and not any(t in memory.tags for t in tags):
                continue

            # Compute base score
            if method == "bm25":
                doc_tokens = self._tfidf._tokenize(memory.content)
                score = self._tfidf.bm25_score(query_tokens, doc_tokens, avg_doc_len)
                # Normalize BM25 to 0-1 range (approximate)
                score = min(score / 20.0, 1.0)
            else:
                score = (TFIDFEngine.cosine_similarity(query_vector, memory.embedding)
                         if memory.embedding else 0.0)

            # Boost by importance
            score *= (0.5 + memory.importance * 0.5)

            # v10: Enhanced recency scoring with temporal decay
            if recency_weight > 0:
                hours_old = memory.staleness_hours()
                # Stronger decay for very old memories (> 7 days)
                if hours_old > 168:
                    decay_factor = 0.02
                elif hours_old > 24:
                    decay_factor = 0.01
                else:
                    decay_factor = 0.005
                recency_boost = math.exp(-hours_old * recency_weight * decay_factor)
                score *= (0.4 + recency_boost * 0.6)

            # Boost by access frequency
            score *= (1 + math.log(memory.access_count + 1) * 0.1)

            # Tag overlap bonus
            if query_tokens:
                tag_overlap = len(set(memory.tags) & set(query_tokens))
                score *= (1 + tag_overlap * 0.05)

            if score > 0.01:
                reason_parts = [f"sim={score:.3f}"]
                if memory.importance > 0.7:
                    reason_parts.append("high-importance")
                if memory.staleness_hours() < 1:
                    reason_parts.append("recent")
                results.append(SearchResult(
                    memory=memory,
                    score=score,
                    reason=" | ".join(reason_parts),
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        top_results = results[:limit]

        # Update access tracking
        for r in top_results:
            r.memory.last_accessed_at = time.time()
            r.memory.access_count += 1

        return top_results

    # ── RAG Pipeline ───────────────────────────────────────────────

    def build_rag_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        max_tokens: int = RAG_DEFAULT_MAX_TOKENS,
        include_profile: bool = True,
    ) -> str:
        """
        Build context string for RAG injection into LLM prompts.
        Retrieves relevant memories and formats them with token budget.
        """
        results = self.search(
            query, limit=15, user_id=user_id, recency_weight=0.5,
        )

        if not results and not include_profile:
            return ""

        parts: List[str] = []
        token_estimate = 0

        # User profile context
        if include_profile and user_id:
            profile_ctx = self.get_user_context(user_id)
            if profile_ctx:
                parts.append(profile_ctx)
                token_estimate += len(profile_ctx) // 4

        # Memory entries
        if results:
            parts.append("## RELEVANT MEMORIES\n")
            token_estimate += 5

            type_emoji: Dict[MemoryType, str] = {
                MemoryType.CONVERSATION: "💬",
                MemoryType.FACT: "📌",
                MemoryType.PREFERENCE: "⚙️",
                MemoryType.SKILL: "🛠️",
                MemoryType.RESULT: "📊",
                MemoryType.SUMMARY: "📝",
                MemoryType.PERSONALITY: "👤",
                MemoryType.INSTRUCTION: "📋",
            }

            for r in results:
                age = self._format_age(r.memory.created_at)
                emoji = type_emoji.get(r.memory.type, "•")
                display = r.memory.summary or r.memory.content[:300]
                entry = f"{emoji} [{r.memory.type.value}] ({age})\n{display}"

                if r.memory.tags:
                    entry += f"\nTags: {', '.join(r.memory.tags)}"

                entry_tokens = len(entry) // 4
                if token_estimate + entry_tokens > max_tokens:
                    break

                parts.append(entry)
                token_estimate += entry_tokens

        return "\n\n".join(parts)

    # ── User Profiles ──────────────────────────────────────────────

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing or create new user profile."""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile(user_id=user_id)
        return self._user_profiles[user_id]

    def _update_user_profile(self, user_id: str, memory: Memory) -> None:
        """Update user profile based on new memory."""
        profile = self.get_or_create_profile(user_id)
        profile.last_seen = time.time()
        profile.total_interactions += 1

        if len(profile.memory_ids) < self._max_per_user:
            profile.memory_ids.append(memory.id)

        # Update topics
        for tag in memory.tags:
            existing = next((t for t in profile.topics if t["topic"] == tag), None)
            if existing:
                existing["frequency"] += 1
                existing["last_seen"] = time.time()
            else:
                profile.topics.append({
                    "topic": tag, "frequency": 1, "last_seen": time.time(),
                })

        # Sort topics by frequency, trim
        profile.topics.sort(key=lambda t: t["frequency"], reverse=True)
        if len(profile.topics) > MAX_TOPICS_PER_USER:
            profile.topics = profile.topics[:MAX_TOPICS_PER_USER]

        # Language detection
        if memory.metadata.language:
            profile.language = memory.metadata.language

        # Display name from metadata
        if memory.metadata.extra.get("display_name"):
            profile.display_name = memory.metadata.extra["display_name"]

        # Style learning (exponential moving average)
        if memory.type == MemoryType.CONVERSATION:
            word_count = memory.metadata.word_count
            content_lower = memory.content.lower()

            # Verbosity: based on message length
            verbosity_signal = min(word_count / 200.0, 1.0)
            profile.style["verbosity"] = (
                profile.style["verbosity"] * (1 - STYLE_EMA_ALPHA)
                + verbosity_signal * STYLE_EMA_ALPHA
            )

            # Technicality: based on tech word density
            tech_words = len(re.findall(
                r"\b(api|function|class|module|config|server|database|query|"
                r"algorithm|framework|protocol|endpoint|deploy|container|"
                r"async|await|import|pipeline|infrastructure)\b",
                content_lower,
            ))
            tech_signal = min(tech_words / 5.0, 1.0)
            profile.style["technicality"] = (
                profile.style["technicality"] * (1 - STYLE_EMA_ALPHA)
                + tech_signal * STYLE_EMA_ALPHA
            )

            # Formality: based on greeting/emoji patterns
            informal_signals = len(re.findall(
                r"[😀-🙏💀-💯🔥-🧠]|lol|haha|omg|\bhi\b|\bhey\b|\byo\b",
                content_lower,
            ))
            formality_signal = max(0, 1.0 - informal_signals * 0.2)
            profile.style["formality"] = (
                profile.style["formality"] * (1 - STYLE_EMA_ALPHA)
                + formality_signal * STYLE_EMA_ALPHA
            )

            # Emotionality: based on exclamation marks and caps
            exclaim = content_lower.count("!") + content_lower.count("؟")
            caps_ratio = sum(1 for c in memory.content if c.isupper()) / max(len(memory.content), 1)
            emotion_signal = min((exclaim * 0.2 + caps_ratio * 2), 1.0)
            profile.style["emotionality"] = (
                profile.style["emotionality"] * (1 - STYLE_EMA_ALPHA)
                + emotion_signal * STYLE_EMA_ALPHA
            )

            # Average message length (running average)
            profile.style["avg_message_length"] = (
                profile.style["avg_message_length"] * (1 - STYLE_EMA_ALPHA)
                + word_count * STYLE_EMA_ALPHA
            )

    def get_user_context(self, user_id: str) -> str:
        """Build human-readable context string for a user."""
        profile = self._user_profiles.get(user_id)
        if not profile:
            return ""

        lines = ["## USER PROFILE"]
        if profile.display_name:
            lines.append(f"Name: {profile.display_name}")
        if profile.language:
            lines.append(f"Language: {profile.language}")
        lines.append(f"Interactions: {profile.total_interactions}")
        lines.append(
            f"Style: formality={profile.style.get('formality', 0.5):.2f}, "
            f"verbosity={profile.style.get('verbosity', 0.5):.2f}, "
            f"technicality={profile.style.get('technicality', 0.5):.2f}, "
            f"emotionality={profile.style.get('emotionality', 0.5):.2f}"
        )

        if profile.topics:
            top = profile.topics[:10]
            lines.append(f"Top topics: {', '.join(t['topic'] for t in top)}")

        if profile.preferences:
            lines.append(f"Preferences: {json.dumps(profile.preferences, ensure_ascii=False)}")

        return "\n".join(lines)

    # ── Consolidation ──────────────────────────────────────────────

    def _maybe_consolidate(self, new_memory: Memory) -> None:
        """Merge very similar memories to avoid duplication."""
        similar = self.search(
            new_memory.content, limit=3,
            mem_type=new_memory.type,
            user_id=new_memory.user_id or None,
            recency_weight=0,
        )

        for result in similar:
            if result.memory.id == new_memory.id:
                continue
            if result.score > self._consolidation_threshold:
                # Merge: keep newer, absorb older's data
                new_memory.importance = max(
                    new_memory.importance, result.memory.importance,
                )
                new_memory.access_count += result.memory.access_count
                new_memory.tags = list(set(new_memory.tags + result.memory.tags))[:MAX_TAGS_PER_MEMORY]

                # Remove old memory
                self._memories.pop(result.memory.id, None)
                self._total_consolidations += 1
                logger.debug(f"Consolidated {result.memory.id} → {new_memory.id}")

    # ── Eviction (Forgetting Curve) ────────────────────────────────

    def _evict_old_memories(self) -> None:
        """Remove lowest-retention memories to stay under limit."""
        scored = [
            (m.id, m.retention_score(self._forgetting_rate))
            for m in self._memories.values()
        ]
        scored.sort(key=lambda x: x[1])

        # Remove bottom 10%
        to_remove = max(1, int(self._max_memories * 0.10))
        for i in range(min(to_remove, len(scored))):
            mem_id = scored[i][0]
            self._memories.pop(mem_id, None)
            self._total_evictions += 1

        logger.info(f"Evicted {to_remove} memories (total: {len(self._memories)})")

    # ── Export / Import ────────────────────────────────────────────

    def export_data(self) -> dict:
        """Export all memories and profiles as serializable dict."""
        return {
            "memories": [m.to_dict() for m in self._memories.values()],
            "profiles": [p.to_dict() for p in self._user_profiles.values()],
            "stats": self.get_stats(),
        }

    def import_data(self, data: dict) -> int:
        """Import memories and profiles from exported data."""
        count = 0
        for md in data.get("memories", []):
            try:
                m = Memory.from_dict(md)
                self._memories[m.id] = m
                if m.content:
                    self._tfidf.add_document(m.content)
                count += 1
            except Exception as exc:
                logger.warning(f"Failed to import memory: {exc}")

        for pd in data.get("profiles", []):
            try:
                p = UserProfile.from_dict(pd)
                self._user_profiles[p.user_id] = p
            except Exception as exc:
                logger.warning(f"Failed to import profile: {exc}")

        logger.info(f"Imported {count} memories, {len(data.get('profiles', []))} profiles")
        return count

    def save_to_disk(self, path: Optional[str] = None) -> str:
        """Save memory store to JSON file."""
        path = path or self._storage_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = self.export_data()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self._memories)} memories to {path}")
        return path

    def load_from_disk(self, path: Optional[str] = None) -> int:
        """Load memory store from JSON file."""
        path = path or self._storage_path
        if not os.path.exists(path):
            logger.info(f"No memory file at {path}")
            return 0
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.import_data(data)


    async def async_save_to_disk(self, path: Optional[str] = None) -> str:
        """Async version of save_to_disk."""
        path = path or self._storage_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = self.export_data()
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"Saved {len(self._memories)} memories to {path}")
        return path

    async def async_load_from_disk(self, path: Optional[str] = None) -> int:
        """Async version of load_from_disk."""
        path = path or self._storage_path
        if not os.path.exists(path):
            logger.info(f"No memory file at {path}")
            return 0
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            raw = await f.read()
        data = json.loads(raw)
        return self.import_data(data)

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get memory store statistics."""
        if not self._memories:
            return {"total_memories": 0, "total_users": 0}

        type_count: Dict[str, int] = defaultdict(int)
        total_importance = 0.0
        for m in self._memories.values():
            type_count[m.type.value] += 1
            total_importance += m.importance

        created_times = [m.created_at for m in self._memories.values()]

        return {
            "total_memories": len(self._memories),
            "total_users": len(self._user_profiles),
            "by_type": dict(type_count),
            "avg_importance": round(total_importance / len(self._memories), 3),
            "vocab_size": self._tfidf.vocab_size,
            "oldest_memory_hours": round((time.time() - min(created_times)) / 3600, 1),
            "newest_memory_hours": round((time.time() - max(created_times)) / 3600, 1),
            "total_stores": self._total_stores,
            "total_searches": self._total_searches,
            "total_consolidations": self._total_consolidations,
            "total_evictions": self._total_evictions,
        }

    # ── CRUD ───────────────────────────────────────────────────────

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        return self._memories.get(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None

    def clear_user(self, user_id: str) -> int:
        """Delete all memories for a user."""
        to_delete = [mid for mid, m in self._memories.items()
                     if m.user_id == user_id]
        for mid in to_delete:
            del self._memories[mid]
        self._user_profiles.pop(user_id, None)
        return len(to_delete)

    def clear(self) -> None:
        """Clear all memories and profiles."""
        self._memories.clear()
        self._user_profiles.clear()

    # ── Utilities ──────────────────────────────────────────────────

    @staticmethod
    def _format_age(timestamp: float) -> str:
        diff = time.time() - timestamp
        mins = int(diff / 60)
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        return f"{months}mo ago"


# ═══════════════════════════════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════════════════════════════

global_memory = MemoryStore()

# v9.1: Enhanced RAG indexing
def build_search_index(self) -> Any:
    """Build inverted index for faster RAG search."""
    self._search_index = {}
    for key, memories in getattr(self, '_store', {}).items():
        if isinstance(memories, list):
            for i, mem in enumerate(memories):
                content = str(mem.get('content', '') if isinstance(mem, dict) else mem)
                words = set(content.lower().split())
                for word in words:
                    if len(word) > 2:
                        if word not in self._search_index:
                            self._search_index[word] = []
                        self._search_index[word].append((key, i))
    return len(self._search_index)

def indexed_search(self, query: str, top_k: int = 10) -> Any:
    """Fast indexed search using inverted index."""
    if not hasattr(self, '_search_index'):
        self.build_search_index()

    query_words = set(query.lower().split())
    scores = {}
    for word in query_words:
        if word in self._search_index:
            for key, idx in self._search_index[word]:
                scores[(key, idx)] = scores.get((key, idx), 0) + 1

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for (key, idx), score in ranked:
        store = getattr(self, '_store', {})
        if key in store and isinstance(store[key], list) and idx < len(store[key]):
            results.append({"key": key, "index": idx, "score": score, "data": store[key][idx]})
    return results


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Memory Intelligence
# ══════════════════════════════════════════════════════════════

class SemanticIndex:
    """Simple keyword-based semantic search (no ML deps required)."""

    def __init__(self) -> None:
        self._index: dict[str, set[str]] = {}  # keyword -> set of memory_ids

    def index_content(self, memory_id: str, content: str) -> Any:
        """Index content by keywords for semantic retrieval."""
        import re
        words = set(re.findall(r'\b\w{3,}\b', content.lower()))
        for w in words:
            if w not in self._index:
                self._index[w] = set()
            self._index[w].add(memory_id)

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search by keyword overlap (TF-IDF-like scoring)."""
        import re, math
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        if not query_words:
            return []

        scores: dict[str, float] = {}
        total_docs = len(set.union(*self._index.values())) if self._index else 1

        for word in query_words:
            if word not in self._index:
                continue
            matching = self._index[word]
            idf = math.log(total_docs / (len(matching) + 1)) + 1
            for mid in matching:
                scores[mid] = scores.get(mid, 0) + idf

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


class AutoTagger:
    """Auto-generate tags for memories based on content."""

    # Common stop words
    _STOP = {
        "the", "and", "for", "are", "but", "not", "you", "all",
        "can", "had", "her", "was", "one", "our", "out", "has",
        "have", "been", "will", "with", "this", "that", "from",
        "they", "what", "about", "which", "when", "make", "like",
        "time", "just", "know", "take", "come", "more", "some",
        "than", "them", "very", "into", "over", "such", "also",
    }

    @classmethod
    def generate_tags(cls, content: str, max_tags: int = 5) -> list[str]:
        """Extract key terms from content as tags."""
        import re
        from collections import Counter
        words = re.findall(r'\b\w{4,}\b', content.lower())
        filtered = [w for w in words if w not in cls._STOP and not w.isdigit()]
        common = Counter(filtered).most_common(max_tags)
        return [w for w, _ in common]


class MemoryCluster:
    """Group related memories into clusters."""

    def __init__(self) -> None:
        self._clusters: dict[str, list[str]] = {}  # cluster_name -> memory_ids

    def add_to_cluster(self, cluster: str, memory_id: str) -> None:
        if cluster not in self._clusters:
            self._clusters[cluster] = []
        if memory_id not in self._clusters[cluster]:
            self._clusters[cluster].append(memory_id)

    def auto_cluster(self, memory_id: str, tags: list[str]) -> Any:
        """Auto-assign to cluster based on tags."""
        for tag in tags:
            self.add_to_cluster(tag, memory_id)

    def get_cluster(self, cluster: str) -> list[str]:
        return self._clusters.get(cluster, [])

    def all_clusters(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._clusters.items()}


