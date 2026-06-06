
from __future__ import annotations
"""
tg_bot/utils/vector_store.py — Vector Database for RAG v9.3
Provides semantic search using vector embeddings.

Backends:
  • In-memory (default, no deps)
  • ChromaDB (pip install chromadb)
  • Qdrant (pip install qdrant-client)
"""
import hashlib
import logging
import math
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass, field

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


@dataclass
class VectorDocument:
    """A document with its vector embedding."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)


class VectorStore:
    """
    Vector similarity search for RAG.
    Uses cosine similarity on simple TF-IDF embeddings by default.
    Upgrades to ChromaDB/Qdrant when available.
    """

    def __init__(self, collection: str = "default", dim: int = 256) -> None:
        self._collection = collection
        self._dim = dim
        self._documents: Dict[str, VectorDocument] = {}
        self._backend = "memory"
        self._chroma = None
        self._vocab: Dict[str, int] = {}
        self._try_backends()

    def _try_backends(self) -> Any:
        """Try to use ChromaDB or Qdrant."""
        try:
            import chromadb
            self._chroma = chromadb.Client()
            self._chroma_col = self._chroma.get_or_create_collection(self._collection)
            self._backend = "chromadb"
            logger.info("Vector store using ChromaDB")
            return
        except ImportError as _exc:
            logger.debug("Suppressed: %s", _exc)
        logger.debug("Vector store using in-memory (install chromadb for better performance)")

    def _simple_embed(self, text: str) -> List[float]:
        """Simple TF-IDF-like embedding (no external deps)."""
        words = text.lower().split()
        for w in words:
            if w not in self._vocab:
                self._vocab[w] = len(self._vocab)
        vec = [0.0] * self._dim
        for w in words:
            idx = self._vocab.get(w, 0) % self._dim
            vec[idx] += 1.0
        # Normalize
        magnitude = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / magnitude for v in vec]

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a)) or 1.0
        mag_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (mag_a * mag_b)

    def add(self, content: str, metadata: Dict = None, doc_id: str = None) -> str:
        """Add a document to the vector store."""
        if not doc_id:
            doc_id = hashlib.md5(content.encode()).hexdigest()[:12]

        embedding = self._simple_embed(content)

        if self._backend == "chromadb" and self._chroma_col:
            self._chroma_col.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata or {}],
            )
        else:
            self._documents[doc_id] = VectorDocument(
                id=doc_id, content=content,
                metadata=metadata or {}, embedding=embedding,
            )
        return doc_id

    def search(self, query: str, top_k: int = 5) -> List[Tuple[VectorDocument, float]]:
        """Search for similar documents."""
        if self._backend == "chromadb" and self._chroma_col:
            results = self._chroma_col.query(
                query_texts=[query],
                n_results=top_k,
            )
            docs = []
            for i, doc_id in enumerate(results["ids"][0]):
                docs.append((
                    VectorDocument(
                        id=doc_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    ),
                    1.0 - (results["distances"][0][i] if results["distances"] else 0),
                ))
            return docs

        # In-memory cosine search
        query_vec = self._simple_embed(query)
        scored = []
        for doc in self._documents.values():
            sim = self._cosine_sim(query_vec, doc.embedding)
            scored.append((doc, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    @property
    def count(self) -> int:
        if self._backend == "chromadb" and self._chroma_col:
            return self._chroma_col.count()
        return len(self._documents)

    @property
    def stats(self) -> dict:
        return {
            "backend": self._backend,
            "documents": self.count,
            "vocab_size": len(self._vocab),
            "collection": self._collection,
        }


_stores: Dict[str, VectorStore] = {}

def get_vector_store(collection: str = "default") -> VectorStore:
    global _stores
    if collection not in _stores:
        _stores[collection] = VectorStore(collection=collection)
    return _stores[collection]


