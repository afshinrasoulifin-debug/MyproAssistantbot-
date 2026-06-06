
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""Victor v7.0 TITAN — Word Embeddings & Semantic Search (Phase 7)

Self-trained word embeddings (Word2Vec CBOW) — NO external APIs or models.
Trains incrementally on all text Victor sees.

- WordEmbeddings: CBOW Word2Vec with negative sampling
- SemanticSearch: cosine similarity over memory embeddings
- WordAnalogy: vector arithmetic for analogies
- HybridRetriever: BM25 + embedding fusion retrieval
"""

import json
import logging
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .nlp import PersianNLP
from .constants import BRAIN_DIR

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. WORD EMBEDDINGS — CBOW Word2Vec with negative sampling
# ═══════════════════════════════════════════════════════════════════

class WordEmbeddings:
    """
    Lightweight Word2Vec CBOW implementation.
    - Trains on all text Victor accumulates (incremental)
    - 64-dimensional embeddings (small but effective)
    - Negative sampling for efficiency
    - Saves/loads from disk
    """

    def __init__(self, dim: int = 64, window: int = 3, min_count: int = 2,
                 learning_rate: float = 0.025, neg_samples: int = 5,
                 brain_dir: Path = None) -> None:
        self.dim = dim
        self.window = window
        self.min_count = min_count
        self.lr = learning_rate
        self.neg_samples = neg_samples
        self.brain_dir = brain_dir or BRAIN_DIR

        # Word → index mapping
        self.word2idx: Dict[str, int] = {}
        self.idx2word: Dict[int, str] = {}
        self.word_counts: Counter = Counter()

        # Weight matrices: W (input) and W' (output)
        self.W: List[List[float]] = []   # vocab_size × dim (input embeddings)
        self.W_out: List[List[float]] = []  # vocab_size × dim (output embeddings)

        # Negative sampling table
        self._neg_table: List[int] = []
        self._trained_tokens = 0

        self._load()

    def _init_vector(self) -> List[float]:
        """Initialize a random vector."""
        return [random.uniform(-0.5, 0.5) / self.dim for _ in range(self.dim)]

    def _build_vocab(self, tokens: List[str]) -> Any:
        """Update vocabulary with new tokens."""
        self.word_counts.update(tokens)
        for word, count in self.word_counts.items():
            if count >= self.min_count and word not in self.word2idx:
                idx = len(self.word2idx)
                self.word2idx[word] = idx
                self.idx2word[idx] = word
                self.W.append(self._init_vector())
                self.W_out.append(self._init_vector())

    def _build_neg_table(self, table_size: int = 10000) -> Any:
        """Build negative sampling table (unigram^0.75 distribution)."""
        if not self.word2idx:
            return
        power = 0.75
        total = sum(
            self.word_counts.get(self.idx2word[i], 1) ** power
            for i in range(len(self.word2idx))
        )
        self._neg_table = []
        for idx in range(len(self.word2idx)):
            word = self.idx2word[idx]
            freq = (self.word_counts.get(word, 1) ** power) / total
            count = int(freq * table_size)
            self._neg_table.extend([idx] * max(1, count))

    def train(self, text: str, epochs: int = 1) -> Any:
        """Train on text (incremental)."""
        tokens = PersianNLP.tokenize(text)
        tokens = [t for t in tokens if t not in PersianNLP.STOPWORDS and len(t) > 1]
        if len(tokens) < 3:
            return

        self._build_vocab(tokens)
        if len(self.word2idx) < 5:
            return

        self._build_neg_table()

        # Convert to indices
        indices = [self.word2idx[t] for t in tokens if t in self.word2idx]
        if len(indices) < 3:
            return

        for _ in range(epochs):
            self._train_epoch(indices)
        self._trained_tokens += len(indices)

    def _train_epoch(self, indices: List[int]) -> Any:
        """One training epoch over token indices."""
        for pos in range(len(indices)):
            target = indices[pos]

            # Context window
            start = max(0, pos - self.window)
            end = min(len(indices), pos + self.window + 1)
            context = [indices[i] for i in range(start, end) if i != pos]
            if not context:
                continue

            # CBOW: average context vectors
            context_vec = [0.0] * self.dim
            for ctx_idx in context:
                for d in range(self.dim):
                    context_vec[d] += self.W[ctx_idx][d]
            n_ctx = len(context)
            for d in range(self.dim):
                context_vec[d] /= n_ctx

            # Positive sample: target word
            self._update(context_vec, target, label=1, context_indices=context)

            # Negative samples
            for _ in range(self.neg_samples):
                if self._neg_table:
                    neg_idx = random.choice(self._neg_table)
                else:
                    neg_idx = random.randint(0, len(self.word2idx) - 1)
                if neg_idx != target:
                    self._update(context_vec, neg_idx, label=0, context_indices=context)

    def _update(self, context_vec: List[float], target: int, label: int,
                context_indices: List[int]) -> Any:
        """Update weights for one sample."""
        # Sigmoid
        dot = sum(context_vec[d] * self.W_out[target][d] for d in range(self.dim))
        dot = max(-10, min(10, dot))  # clip
        sig = 1.0 / (1.0 + math.exp(-dot))

        # Gradient
        error = self.lr * (label - sig)

        # Update output weight
        grad_in = [0.0] * self.dim
        for d in range(self.dim):
            grad_in[d] = error * self.W_out[target][d]
            self.W_out[target][d] += error * context_vec[d]

        # Update input weights (context words)
        for ctx_idx in context_indices:
            for d in range(self.dim):
                self.W[ctx_idx][d] += grad_in[d] / len(context_indices)

    def get_vector(self, word: str) -> Optional[List[float]]:
        """Get embedding vector for a word."""
        idx = self.word2idx.get(word)
        if idx is None:
            # Try stemmed
            stemmed = PersianNLP.stem(word)
            idx = self.word2idx.get(stemmed)
        if idx is not None:
            return self.W[idx][:]
        return None

    def get_sentence_vector(self, text: str) -> Optional[List[float]]:
        """Get average embedding for a sentence."""
        tokens = PersianNLP.tokenize(text)
        tokens = [t for t in tokens if t not in PersianNLP.STOPWORDS]
        vectors = []
        for t in tokens:
            v = self.get_vector(t)
            if v:
                vectors.append(v)
        if not vectors:
            return None
        avg = [0.0] * self.dim
        for v in vectors:
            for d in range(self.dim):
                avg[d] += v[d]
        n = len(vectors)
        return [a / n for a in avg]

    def similarity(self, word_a: str, word_b: str) -> float:
        """Cosine similarity between two words."""
        va = self.get_vector(word_a)
        vb = self.get_vector(word_b)
        if va is None or vb is None:
            return 0.0
        return self._cosine(va, vb)

    def most_similar(self, word: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Find most similar words."""
        vec = self.get_vector(word)
        if vec is None:
            return []
        results = []
        for idx, w in self.idx2word.items():
            if w == word:
                continue
            sim = self._cosine(vec, self.W[idx])
            results.append((w, sim))
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def save(self) -> Any:
        """Save embeddings to disk."""
        emb_dir = self.brain_dir / "embeddings"
        emb_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "dim": self.dim,
            "word2idx": self.word2idx,
            "word_counts": dict(self.word_counts),
            "trained_tokens": self._trained_tokens,
            "W": self.W,
            "W_out": self.W_out,
        }
        path = emb_dir / "word2vec.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        logger.info("Embeddings saved: %d words, %d dims", len(self.word2idx), self.dim)

    def _load(self) -> Any:
        """Load embeddings from disk if available."""
        path = self.brain_dir / "embeddings" / "word2vec.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.dim = data.get("dim", self.dim)
            self.word2idx = data.get("word2idx", {})
            self.idx2word = {int(i): w for w, i in self.word2idx.items()}
            self.word_counts = Counter(data.get("word_counts", {}))
            self._trained_tokens = data.get("trained_tokens", 0)
            self.W = data.get("W", [])
            self.W_out = data.get("W_out", [])
            self._build_neg_table()
            logger.info("Embeddings loaded: %d words", len(self.word2idx))
        except HandlerError as e:
            logger.warning("Failed to load embeddings: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "vocab_size": len(self.word2idx),
            "dimensions": self.dim,
            "trained_tokens": self._trained_tokens,
        }


# ═══════════════════════════════════════════════════════════════════
# 2. SEMANTIC SEARCH — Cosine similarity over memory embeddings
# ═══════════════════════════════════════════════════════════════════

class SemanticSearch:
    """
    Search memories using embedding similarity (not just keyword matching).
    Computes sentence embeddings for all memories and queries.
    """

    def __init__(self, embeddings: WordEmbeddings, memory_store: Any) -> None:
        self.embeddings = embeddings
        self.memory = memory_store
        self._cache: Dict[str, List[float]] = {}  # memory_id → embedding

    def index_all(self) -> Any:
        """Pre-compute embeddings for all memories."""
        for mid, mem in self.memory.memories.items():
            vec = self.embeddings.get_sentence_vector(mem.content)
            if vec:
                self._cache[mid] = vec

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Any, float]]:
        """Search memories by semantic similarity."""
        query_vec = self.embeddings.get_sentence_vector(query)
        if query_vec is None:
            return []

        results = []
        for mid, mem_vec in self._cache.items():
            sim = WordEmbeddings._cosine(query_vec, mem_vec)
            if sim > 0.1:
                mem = self.memory.memories.get(mid)
                if mem:
                    results.append((mem, sim))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def find_similar_memories(self, memory_id: str, top_k: int = 5) -> List[Tuple[Any, float]]:
        """Find memories similar to a given memory."""
        vec = self._cache.get(memory_id)
        if vec is None:
            return []

        results = []
        for mid, mem_vec in self._cache.items():
            if mid == memory_id:
                continue
            sim = WordEmbeddings._cosine(vec, mem_vec)
            if sim > 0.1:
                mem = self.memory.memories.get(mid)
                if mem:
                    results.append((mem, sim))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]


# ═══════════════════════════════════════════════════════════════════
# 3. WORD ANALOGY — Vector arithmetic
# ═══════════════════════════════════════════════════════════════════

class WordAnalogy:
    """
    Solve analogies using vector arithmetic:
    king - man + woman = queen
    i.e., vec(B) - vec(A) + vec(C) = vec(?)
    """

    def __init__(self, embeddings: WordEmbeddings) -> None:
        self.embeddings = embeddings

    def solve(self, word_a: str, word_b: str, word_c: str,
              top_k: int = 5) -> List[Tuple[str, float]]:
        """
        A is to B as C is to ?
        Result = vec(B) - vec(A) + vec(C)
        """
        va = self.embeddings.get_vector(word_a)
        vb = self.embeddings.get_vector(word_b)
        vc = self.embeddings.get_vector(word_c)

        if va is None or vb is None or vc is None:
            return []

        # Target vector: B - A + C
        dim = self.embeddings.dim
        target = [vb[d] - va[d] + vc[d] for d in range(dim)]

        # Find closest words
        exclude = {word_a.lower(), word_b.lower(), word_c.lower()}
        results = []
        for idx, word in self.embeddings.idx2word.items():
            if word.lower() in exclude:
                continue
            sim = WordEmbeddings._cosine(target, self.embeddings.W[idx])
            results.append((word, sim))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]


# ═══════════════════════════════════════════════════════════════════
# 4. HYBRID RETRIEVER — BM25 + Embedding fusion
# ═══════════════════════════════════════════════════════════════════

class HybridRetriever:
    """
    Combines BM25 keyword retrieval with semantic embedding search.
    Uses Reciprocal Rank Fusion (RRF) to merge results.
    """

    def __init__(self, memory_store: Any, semantic_search: SemanticSearch,
                 bm25_weight: float = 0.5, semantic_weight: float = 0.5) -> None:
        self.memory = memory_store
        self.semantic = semantic_search
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight

    def retrieve(self, query: str, top_k: int = 10) -> List[Tuple[Any, float]]:
        """
        Hybrid retrieval: merge BM25 and semantic results using RRF.
        """
        # BM25 results
        bm25_results = self.memory.recall(query, top_k=top_k * 2)

        # Semantic results
        semantic_results = self.semantic.search(query, top_k=top_k * 2)

        # Reciprocal Rank Fusion
        rrf_scores: Dict[str, float] = defaultdict(float)
        mem_lookup: Dict[str, Any] = {}

        k = 60  # RRF constant

        for rank, mem in enumerate(bm25_results):
            rrf_scores[mem.id] += self.bm25_weight * (1.0 / (k + rank + 1))
            mem_lookup[mem.id] = mem

        for rank, (mem, _sim) in enumerate(semantic_results):
            rrf_scores[mem.id] += self.semantic_weight * (1.0 / (k + rank + 1))
            mem_lookup[mem.id] = mem

        # Sort by fused score
        ranked = sorted(rrf_scores.items(), key=lambda x: -x[1])
        return [(mem_lookup[mid], score) for mid, score in ranked[:top_k] if mid in mem_lookup]


