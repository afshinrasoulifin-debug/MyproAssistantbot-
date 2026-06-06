
"""
memory_store_pkg/memory_store.py — MemoryStore
Arki Engine v29.0.0
"""
from __future__ import annotations
from ._base import *  # noqa
from arki_project.exceptions import StorageError

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
    ):
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
            except StorageError as exc:
                logger.warning(f"Failed to import memory: {exc}")

        for pd in data.get("profiles", []):
            try:
                p = UserProfile.from_dict(pd)
                self._user_profiles[p.user_id] = p
            except StorageError as exc:
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



