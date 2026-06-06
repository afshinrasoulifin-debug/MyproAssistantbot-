
"""
memory_store_pkg/helpers.py — standalone functions
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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


def build_search_index(self):
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


def indexed_search(self, query: str, top_k: int = 10):
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



