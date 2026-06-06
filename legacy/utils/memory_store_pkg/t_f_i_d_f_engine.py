
"""
memory_store_pkg/t_f_i_d_f_engine.py — TFIDFEngine
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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

    def __init__(self):
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


