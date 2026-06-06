
from __future__ import annotations
"""Victor v7.0 TITAN — MemoryStore (TF-IDF + BM25 + Knowledge Graph)"""

import asyncio
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .constants import BM25_K1, BM25_B, FORGETTING_RATE, logger
from .models import Memory, KnowledgeEdge, InferenceRule
from .nlp import PersianNLP

class MemoryStore:
    """
    Persistent memory system v5 with TF-IDF, BM25, and knowledge graph.
    No database needed — pure file-based for portability.
    """

    def __init__(self, brain_dir: Path) -> None:
        self.brain_dir = brain_dir
        self.memories_file = brain_dir / "memories.json"
        self.graph_file = brain_dir / "knowledge_graph.json"
        self.config_file = brain_dir / "config.json"
        self.rules_file = brain_dir / "inference_rules.json"
        self.context_file = brain_dir / "conversation_context.json"
        self.log_file = brain_dir / "interaction_log.jsonl"
        self.corrections_file = brain_dir / "corrections.json"

        # Ensure directories exist
        brain_dir.mkdir(parents=True, exist_ok=True)

        # Core data structures
        self.memories: Dict[str, Memory] = {}
        self.graph_edges: List[KnowledgeEdge] = []
        self.rules: Dict[str, InferenceRule] = {}
        self.conversation_context: List[Dict[str, Any]] = []  # Recent interactions
        self.corrections: List[Dict[str, Any]] = []  # User corrections
        self.config: Dict[str, Any] = {
            "name": "Victor",
            "born_at": "",
            "total_interactions": 0,
            "total_teachings": 0,
            "personality_traits": [],
            "language_preference": "fa",
            "version": "7.0",
        }

        # TF-IDF index (in-memory, rebuilt on load)
        self._idf: Dict[str, float] = {}
        self._doc_count: int = 0
        self._avg_doc_len: float = 0.0
        self._tf_cache: Dict[str, Dict[str, float]] = {}  # mem_id → {term: tf}
        self._tf_cache_max: int = 10000  # v29.0: prevent unbounded growth

        # Auto-learn tracker
        self._query_tracker: Dict[str, int] = {}  # query_hash → count

        self._load()

    def _load(self) -> Any:
        """Load brain state from disk."""
        # Memories
        if self.memories_file.exists():
            try:
                data = json.loads(self.memories_file.read_text(encoding="utf-8"))
                for mid, mdata in data.items():
                    # Handle missing fields from v3 gracefully
                    mdata.setdefault("sentiment", "neutral")
                    mdata.setdefault("language", "fa")
                    mdata.setdefault("embedding", [])
                    self.memories[mid] = Memory(**mdata)
            except Exception as e:
                logger.error("Failed to load memories: %s", e)

        # Knowledge graph
        if self.graph_file.exists():
            try:
                data = json.loads(self.graph_file.read_text(encoding="utf-8"))
                for e in data:
                    e.setdefault("bidirectional", False)
                self.graph_edges = [KnowledgeEdge(**e) for e in data]
            except Exception as e:
                logger.error("Failed to load graph: %s", e)

        # Inference rules
        if self.rules_file.exists():
            try:
                data = json.loads(self.rules_file.read_text(encoding="utf-8"))
                for rid, rdata in data.items():
                    self.rules[rid] = InferenceRule(**rdata)
            except Exception as e:
                logger.error("Failed to load rules: %s", e)

        # Conversation context
        if self.context_file.exists():
            try:
                self.conversation_context = json.loads(
                    self.context_file.read_text(encoding="utf-8")
                )
            except Exception:
                self.conversation_context = []

        # Corrections
        if self.corrections_file.exists():
            try:
                self.corrections = json.loads(
                    self.corrections_file.read_text(encoding="utf-8")
                )
            except Exception:
                self.corrections = []

        # Config
        if self.config_file.exists():
            try:
                self.config.update(
                    json.loads(self.config_file.read_text(encoding="utf-8"))
                )
            except Exception as e:
                logger.error("Failed to load config: %s", e)
        else:
            self.config["born_at"] = datetime.now(timezone.utc).isoformat()
            self._save_config()

        # Rebuild TF-IDF index
        self._rebuild_tfidf_index()

    def _rebuild_tfidf_index(self) -> Any:
        """Rebuild TF-IDF index from all memories."""
        self._tf_cache.clear()
        self._idf.clear()

        if not self.memories:
            self._doc_count = 0
            self._avg_doc_len = 0.0
            self._df_counts = defaultdict(int)
            return

        # Count document frequency for each term
        df: Dict[str, int] = defaultdict(int)
        doc_lengths: List[int] = []

        for mem in self.memories.values():
            tokens = PersianNLP.tokenize(mem.content + " " + mem.topic)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] += 1
            doc_lengths.append(len(tokens))

            # Cache TF for each document
            tf: Dict[str, float] = {}
            total = len(tokens)
            if total > 0:
                counts = Counter(tokens)
                for term, count in counts.items():
                    tf[term] = count / total
            self._tf_cache[mem.id] = tf

        self._doc_count = len(self.memories)
        self._avg_doc_len = sum(doc_lengths) / max(1, len(doc_lengths))

        # Store DF counts for incremental updates
        self._df_counts = dict(df)

        # Calculate IDF
        for term, freq in df.items():
            self._idf[term] = math.log((self._doc_count - freq + 0.5) / (freq + 0.5) + 1)

    # ── Persistence ──

    def _save_memories(self) -> Any:
        """Persist memories to disk."""
        data = {mid: asdict(m) for mid, m in self.memories.items()}
        self.memories_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_graph(self) -> Any:
        """Persist knowledge graph to disk."""
        data = [asdict(e) for e in self.graph_edges]
        self.graph_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_config(self) -> Any:
        """Persist config to disk."""
        self.config_file.write_text(
            json.dumps(self.config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_rules(self) -> Any:
        """Persist inference rules to disk."""
        data = {rid: asdict(r) for rid, r in self.rules.items()}
        self.rules_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_context(self) -> Any:
        """Persist conversation context to disk."""
        # Keep only last N interactions
        self.conversation_context = self.conversation_context[-CONTEXT_WINDOW_SIZE:]
        self.context_file.write_text(
            json.dumps(self.conversation_context, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_corrections(self) -> Any:
        """Persist corrections to disk."""
        self.corrections_file.write_text(
            json.dumps(self.corrections[-100:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Async I/O wrappers (Phase 4) ──

    async def async_save_all(self) -> Any:
        """Non-blocking save of all data files using thread pool."""
        await asyncio.to_thread(self._save_all_sync)

    def _save_all_sync(self) -> Any:
        """Save all data files (blocking — use async_save_all in async context)."""
        self._save_memories()
        self._save_graph()
        self._save_config()
        self._save_rules()
        self._save_context()
        self._save_corrections()

    async def async_store(self, content: str, topic: str, memory_type: str = "fact",
                          keywords: List[str] = None, source: str = "admin") -> "Memory":
        """Async wrapper for store() — runs blocking I/O in thread pool."""
        return await asyncio.to_thread(
            self.store, content, topic, memory_type, keywords, source
        )

    def log_interaction(self, user_input: str, response: str, action: str = "chat") -> None:
        """Log every interaction for learning and context."""
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "ts": now,
            "input": user_input,
            "response": response[:500],
            "action": action,
        }

        # Append to log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Update conversation context (short-term memory)
        sentiment_label, sentiment_score = PersianNLP.analyze_sentiment(user_input)
        self.conversation_context.append({
            "ts": now,
            "input": user_input,
            "response": response[:200],
            "sentiment": sentiment_label,
            "keywords": PersianNLP.extract_keywords(user_input)[:10],
        })
        self._save_context()

        self.config["total_interactions"] = self.config.get("total_interactions", 0) + 1
        self._save_config()

        # Auto-learn: track repeated queries
        qhash = hashlib.md5(user_input.lower().strip().encode()).hexdigest()[:8]
        self._query_tracker[qhash] = self._query_tracker.get(qhash, 0) + 1

    # ── CRUD ──

    def store(self, content: str, topic: str, memory_type: str = "fact",
              keywords: Optional[List[str]] = None,
              associations: Optional[List[str]] = None) -> Memory:
        """Store a new memory with full NLP processing."""
        now = datetime.now(timezone.utc).isoformat()
        mid = hashlib.sha256(f"{content}:{topic}:{now}".encode()).hexdigest()[:12]

        if keywords is None:
            keywords = PersianNLP.extract_keywords(content + " " + topic)

        sentiment_label, _ = PersianNLP.analyze_sentiment(content)
        language = PersianNLP.detect_language(content)

        mem = Memory(
            id=mid,
            content=content,
            memory_type=memory_type,
            topic=topic,
            keywords=keywords,
            associations=associations or [],
            created_at=now,
            last_accessed=now,
            sentiment=sentiment_label,
            language=language,
        )
        self.memories[mid] = mem
        self._save_memories()

        # Update TF-IDF index incrementally
        self._update_tfidf_for_memory(mid)

        self.config["total_teachings"] = self.config.get("total_teachings", 0) + 1
        self._save_config()

        return mem

    def _update_tfidf_for_memory(self, mid: str) -> Any:
        """Incrementally update TF-IDF index for a single new memory.
        
        Instead of rebuilding ALL IDF from scratch (O(n) per store),
        we only update the DF counts for the new document's terms
        and recalculate IDF for those affected terms.
        """
        if mid not in self.memories:
            return
        mem = self.memories[mid]
        tokens = PersianNLP.tokenize(mem.content + " " + mem.topic)
        total = len(tokens)
        if total == 0:
            return

        # Update TF cache for this document
        counts = Counter(tokens)
        tf = {term: count / total for term, count in counts.items()}
        self._tf_cache[mid] = tf

        # v29.0: Prevent unbounded TF cache growth
        if len(self._tf_cache) > self._tf_cache_max:
            # Evict oldest 20% entries
            to_evict = list(self._tf_cache.keys())[:len(self._tf_cache) // 5]
            for k in to_evict:
                del self._tf_cache[k]

        # Incrementally update doc count and avg doc length
        old_doc_count = self._doc_count
        self._doc_count = len(self.memories)

        # Update avg doc length incrementally
        if old_doc_count > 0:
            old_total_len = self._avg_doc_len * old_doc_count
            self._avg_doc_len = (old_total_len + total) / self._doc_count
        else:
            self._avg_doc_len = float(total)

        # Initialize _df_counts if not present (first time or after rebuild)
        if not hasattr(self, '_df_counts'):
            self._df_counts: Dict[str, int] = defaultdict(int)
            # Build DF from scratch once
            for m in self.memories.values():
                doc_terms = set(PersianNLP.tokenize(m.content + " " + m.topic))
                for t in doc_terms:
                    self._df_counts[t] += 1
        else:
            # Only increment DF for the new document's unique terms
            new_terms = set(tokens)
            for t in new_terms:
                self._df_counts[t] = self._df_counts.get(t, 0) + 1

        # Recalculate IDF only for affected terms
        new_terms = set(tokens)
        for term in new_terms:
            freq = self._df_counts.get(term, 0)
            self._idf[term] = math.log(
                (self._doc_count - freq + 0.5) / (freq + 0.5) + 1
            )

    def recall_bm25(self, query: str, top_k: int = 10) -> List[Tuple[float, Memory]]:
        """
        BM25 retrieval — much smarter than simple keyword matching.
        Okapi BM25 with TF-IDF scoring.
        """
        query_tokens = PersianNLP.tokenize(query)
        query_stems = [PersianNLP.stem(t) for t in query_tokens]
        all_query_terms = set(query_tokens + query_stems)

        scored: List[Tuple[float, Memory]] = []

        for mid, mem in self.memories.items():
            doc_tokens = PersianNLP.tokenize(mem.content + " " + mem.topic)
            doc_len = len(doc_tokens)
            if doc_len == 0:
                continue

            tf = self._tf_cache.get(mid, {})
            score = 0.0

            for term in all_query_terms:
                if term not in tf:
                    # Try stemmed version
                    stemmed = PersianNLP.stem(term)
                    if stemmed not in tf:
                        continue
                    term = stemmed

                term_tf = tf.get(term, 0.0) * doc_len  # un-normalize
                idf = self._idf.get(term, 0.0)

                # BM25 formula
                numerator = term_tf * (BM25_K1 + 1)
                denominator = term_tf + BM25_K1 * (1 - BM25_B + BM25_B * (doc_len / max(1, self._avg_doc_len)))
                score += idf * (numerator / max(0.001, denominator))

            if score > 0:
                # Apply memory strength and recency bonuses
                strength_bonus = math.log(1 + mem.strength) * 2
                access_bonus = math.log(1 + mem.access_count) * 0.5

                # Ebbinghaus forgetting curve penalty
                try:
                    last_access = datetime.fromisoformat(mem.last_accessed)
                    hours_since = (datetime.now(timezone.utc) - last_access).total_seconds() / 3600
                    retention = math.exp(-hours_since * FORGETTING_RATE)
                except Exception:
                    retention = 0.5

                final_score = score * (1 + strength_bonus + access_bonus) * (0.5 + 0.5 * retention)
                scored.append((final_score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def recall(self, query: str, top_k: int = 10) -> List[Memory]:
        """
        Hybrid recall: BM25 + keyword overlap + fuzzy match.
        Returns best memories ranked by combined score.
        """
        if not self.memories:
            return []

        # 1. BM25 scores
        bm25_results = self.recall_bm25(query, top_k=top_k * 2)
        bm25_scores: Dict[str, float] = {mem.id: score for score, mem in bm25_results}

        # 2. Fuzzy similarity scores
        fuzzy_scores: Dict[str, float] = {}
        query_lower = query.lower()
        for mid, mem in self.memories.items():
            sim = PersianNLP.similarity(query_lower, mem.content.lower())
            topic_sim = PersianNLP.similarity(query_lower, mem.topic.lower())
            fuzzy_scores[mid] = max(sim, topic_sim)

        # 3. Normalize scores to [0,1] range before combining
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        max_bm25 = max(max_bm25, 1e-6)  # avoid division by zero

        combined: List[Tuple[float, Memory]] = []
        all_mids = set(bm25_scores.keys()) | set(fuzzy_scores.keys())

        for mid in all_mids:
            if mid not in self.memories:
                continue
            mem = self.memories[mid]

            # Normalize BM25 to [0,1] range; fuzzy (Jaccard) is already [0,1]
            bm25_norm = bm25_scores.get(mid, 0.0) / max_bm25
            fuzzy = fuzzy_scores.get(mid, 0.0)

            # Weighted combination: BM25 primary (70%), fuzzy secondary (30%)
            combined_score = bm25_norm * 0.7 + fuzzy * 0.3

            if combined_score > 0.05:
                combined.append((combined_score, mem))

        combined.sort(key=lambda x: x[0], reverse=True)

        # Update access counts
        results = []
        now = datetime.now(timezone.utc).isoformat()
        for _, mem in combined[:top_k]:
            mem.access_count += 1
            mem.last_accessed = now
            results.append(mem)

        if results:
            self._save_memories()

        return results

    def forget(self, topic: str) -> int:
        """Forget all memories about a topic."""
        to_remove = [
            mid for mid, m in self.memories.items()
            if m.topic.lower() == topic.lower()
            or topic.lower() in m.content.lower()
        ]
        for mid in to_remove:
            del self.memories[mid]
            self._tf_cache.pop(mid, None)

        self.graph_edges = [
            e for e in self.graph_edges
            if topic.lower() not in e.from_node.lower()
            and topic.lower() not in e.to_node.lower()
        ]

        self._save_memories()
        self._save_graph()
        self._rebuild_tfidf_index()
        return len(to_remove)

    def reinforce(self, memory_id: str, amount: float = 0.5) -> Any:
        """Strengthen a memory (positive reinforcement)."""
        if memory_id in self.memories:
            self.memories[memory_id].strength += amount
            self._save_memories()

    def weaken(self, memory_id: str, amount: float = 0.3) -> Any:
        """Weaken a memory (negative reinforcement / correction)."""
        if memory_id in self.memories:
            self.memories[memory_id].strength = max(0.1, self.memories[memory_id].strength - amount)
            self._save_memories()

    def add_association(self, mem_id_1: str, mem_id_2: str) -> None:
        """Link two memories together."""
        if mem_id_1 in self.memories and mem_id_2 in self.memories:
            if mem_id_2 not in self.memories[mem_id_1].associations:
                self.memories[mem_id_1].associations.append(mem_id_2)
            if mem_id_1 not in self.memories[mem_id_2].associations:
                self.memories[mem_id_2].associations.append(mem_id_1)
            self._save_memories()

    def add_graph_edge(self, from_node: str, to_node: str,
                       relation: str, weight: float = 1.0,
                       bidirectional: bool = False) -> None:
        """Add a relationship to the knowledge graph."""
        # Check for duplicates
        for e in self.graph_edges:
            if (e.from_node.lower() == from_node.lower()
                    and e.to_node.lower() == to_node.lower()
                    and e.relation == relation):
                e.weight = max(e.weight, weight)
                self._save_graph()
                return

        self.graph_edges.append(KnowledgeEdge(
            from_node=from_node,
            to_node=to_node,
            relation=relation,
            weight=weight,
            bidirectional=bidirectional,
        ))
        self._save_graph()

    def get_related(self, concept: str, max_hops: int = 1) -> List[Tuple[str, str, float, int]]:
        """
        Get all concepts related to a given concept from the graph.
        Supports multi-hop traversal.
        Returns: [(concept, relation, weight, hop_distance), ...]
        """
        results = []
        visited = {concept.lower()}
        frontier = [(concept.lower(), 0)]

        while frontier:
            current, depth = frontier.pop(0)
            if depth >= max_hops:
                continue

            for edge in self.graph_edges:
                # Forward direction
                if current in edge.from_node.lower():
                    target = edge.to_node
                    if target.lower() not in visited:
                        visited.add(target.lower())
                        # Weight decays with hops
                        adjusted_weight = edge.weight * (0.7 ** depth)
                        results.append((target, edge.relation, adjusted_weight, depth + 1))
                        frontier.append((target.lower(), depth + 1))

                # Backward direction (or bidirectional)
                if current in edge.to_node.lower() and (edge.bidirectional or edge.relation in ("related_to", "part_of")):
                    target = edge.from_node
                    if target.lower() not in visited:
                        visited.add(target.lower())
                        adjusted_weight = edge.weight * (0.7 ** depth)
                        results.append((target, f"inv_{edge.relation}", adjusted_weight, depth + 1))
                        frontier.append((target.lower(), depth + 1))

        return sorted(results, key=lambda x: x[2], reverse=True)

    def find_path(self, concept_a: str, concept_b: str, max_depth: int = 4) -> Optional[List[str]]:
        """
        Find a path between two concepts in the knowledge graph.
        BFS pathfinding.
        """
        a_lower = concept_a.lower()
        b_lower = concept_b.lower()

        queue = [(a_lower, [concept_a])]
        visited = {a_lower}

        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue

            for edge in self.graph_edges:
                next_node = None
                if current in edge.from_node.lower():
                    next_node = edge.to_node
                elif current in edge.to_node.lower():
                    next_node = edge.from_node

                if next_node and next_node.lower() not in visited:
                    new_path = path + [f"--[{edge.relation}]-->", next_node]
                    if b_lower in next_node.lower():
                        return new_path
                    visited.add(next_node.lower())
                    queue.append((next_node.lower(), new_path))

        return None

    # ── Inference Rules ──

    def add_rule(self, condition_topic: str, condition_keywords: List[str],
                 conclusion: str, confidence: float = 0.8) -> InferenceRule:
        """Add a new inference rule."""
        rid = hashlib.sha256(
            f"{condition_topic}:{','.join(condition_keywords)}".encode()
        ).hexdigest()[:10]

        rule = InferenceRule(
            id=rid,
            condition_topic=condition_topic,
            condition_keywords=condition_keywords,
            conclusion=conclusion,
            confidence=confidence,
        )
        self.rules[rid] = rule
        self._save_rules()
        return rule

    def match_rules(self, query: str) -> List[Tuple[InferenceRule, float]]:
        """Match query against inference rules."""
        query_keywords = set(PersianNLP.extract_keywords(query))
        query_lower = query.lower()

        matched: List[Tuple[InferenceRule, float]] = []

        for rule in self.rules.values():
            score = 0.0

            # Topic match
            if rule.condition_topic.lower() in query_lower:
                score += 40

            # Keyword overlap
            rule_keywords = set(k.lower() for k in rule.condition_keywords)
            overlap = len(query_keywords & rule_keywords)
            if rule_keywords:
                score += (overlap / len(rule_keywords)) * 60

            if score >= 30:
                matched.append((rule, score * rule.confidence))

        matched.sort(key=lambda x: x[1], reverse=True)
        return matched

    # ── Contradiction Detection ──

    def find_contradictions(self, new_content: str, topic: str) -> List[Memory]:
        """Find memories that might contradict new information."""
        contradictions = []
        related_memories = self.recall(f"{topic} {new_content}", top_k=10)

        sentiment_new, _ = PersianNLP.analyze_sentiment(new_content)

        for mem in related_memories:
            if mem.topic.lower() == topic.lower():
                # Check if sentiments are opposite
                if (sentiment_new == "positive" and mem.sentiment == "negative") or \
                   (sentiment_new == "negative" and mem.sentiment == "positive"):
                    contradictions.append(mem)
                    continue

                # Check for negation patterns
                new_has_neg = any(p in new_content for p in ["نیست", "نه", "نمی", "بدون"])
                old_has_neg = any(p in mem.content for p in ["نیست", "نه", "نمی", "بدون"])
                if new_has_neg != old_has_neg:
                    # One is positive, one is negative about same topic
                    sim = PersianNLP.similarity(new_content, mem.content)
                    if sim > 0.4:
                        contradictions.append(mem)

        return contradictions

    # ── Correction System ──

    def record_correction(self, wrong_response: str, correct_response: str, context: str = "") -> Any:
        """Record a correction from admin for learning."""
        self.corrections.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "wrong": wrong_response[:500],
            "correct": correct_response[:500],
            "context": context[:200],
        })
        self._save_corrections()

        # Store correction as a high-strength memory
        self.store(
            content=f"اصلاح: وقتی سوال «{context[:100]}» پرسیده شد، جواب درست: {correct_response[:300]}",
            topic="correction",
            memory_type="correction",
        )
        # Reinforce the correction
        # Find and weaken the memory that produced the wrong answer
        wrong_memories = self.recall(wrong_response, top_k=3)
        for mem in wrong_memories:
            self.weaken(mem.id, 0.5)

    def reset(self) -> Any:
        """Factory reset — clear everything."""
        self.memories.clear()
        self.graph_edges.clear()
        self.rules.clear()
        self.conversation_context.clear()
        self.corrections.clear()
        self._tf_cache.clear()
        self._idf.clear()
        self._query_tracker.clear()

        self.config = {
            "name": "Victor",
            "born_at": datetime.now(timezone.utc).isoformat(),
            "total_interactions": 0,
            "total_teachings": 0,
            "personality_traits": [],
            "language_preference": "fa",
            "version": "7.0",
            "previous_births": self.config.get("previous_births", 0) + 1,
        }
        self._save_memories()
        self._save_graph()
        self._save_config()
        self._save_rules()
        self._save_context()
        self._save_corrections()

    def get_stats(self) -> Dict[str, Any]:
        """Get brain statistics."""
        type_counts = Counter(m.memory_type for m in self.memories.values())
        topic_counts = Counter(m.topic for m in self.memories.values())
        sentiment_counts = Counter(m.sentiment for m in self.memories.values())
        avg_strength = (
            sum(m.strength for m in self.memories.values()) / max(1, len(self.memories))
        )

        return {
            "total_memories": len(self.memories),
            "by_type": dict(type_counts),
            "by_topic": dict(topic_counts.most_common(10)),
            "by_sentiment": dict(sentiment_counts),
            "graph_edges": len(self.graph_edges),
            "inference_rules": len(self.rules),
            "corrections": len(self.corrections),
            "total_interactions": self.config.get("total_interactions", 0),
            "total_teachings": self.config.get("total_teachings", 0),
            "born_at": self.config.get("born_at", "unknown"),
            "avg_strength": avg_strength,
            "vocabulary_size": len(self._idf),
            "context_depth": len(self.conversation_context),
            "strongest_memories": [
                (m.topic, m.content[:80], m.strength)
                for m in sorted(
                    self.memories.values(),
                    key=lambda x: x.strength,
                    reverse=True,
                )[:5]
            ],
        }


