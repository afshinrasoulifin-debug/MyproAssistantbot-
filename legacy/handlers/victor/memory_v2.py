
from __future__ import annotations
"""Victor v7.0 TITAN — Professional Memory System (Phase 9)

Advanced memory management beyond simple key-value storage:
- EpisodicMemory: events with time, place, participants
- SemanticCompressor: merge/compress similar memories
- KnowledgeVersioning: track changes to knowledge over time
- CrossTopicInference: discover connections across topics
- ImportanceScorer: multi-factor importance ranking
"""

import json
import logging
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .nlp import PersianNLP
from .constants import BRAIN_DIR

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. EPISODIC MEMORY — Events with context
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Episode:
    """An episodic memory — a specific event or experience."""
    id: str
    content: str
    timestamp: str
    participants: List[str] = field(default_factory=list)
    location: str = ""
    topic: str = ""
    emotions: Dict[str, float] = field(default_factory=dict)
    related_episodes: List[str] = field(default_factory=list)
    importance: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "content": self.content,
            "timestamp": self.timestamp, "participants": self.participants,
            "location": self.location, "topic": self.topic,
            "emotions": self.emotions, "related_episodes": self.related_episodes,
            "importance": self.importance,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Episode":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class EpisodicMemory:
    """
    Stores and retrieves episodic memories (events/experiences).
    Unlike semantic memory (facts), these are time-bound and context-rich.
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.episodes: Dict[str, Episode] = {}
        self._counter = 0
        self._load()

    def record(self, content: str, participants: List[str] = None,
               location: str = "", topic: str = "",
               emotions: Dict[str, float] = None) -> Episode:
        """Record a new episode."""
        self._counter += 1
        ep_id = f"ep_{int(time.time())}_{self._counter}"

        episode = Episode(
            id=ep_id,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            participants=participants or [],
            location=location,
            topic=topic,
            emotions=emotions or {},
        )

        # Auto-score importance
        episode.importance = self._score_importance(episode)

        # Find related episodes
        episode.related_episodes = self._find_related(episode)

        self.episodes[ep_id] = episode
        self._save()
        return episode

    def recall_by_time(self, start: str = None, end: str = None,
                       limit: int = 20) -> List[Episode]:
        """Recall episodes within a time range."""
        episodes = sorted(self.episodes.values(),
                         key=lambda e: e.timestamp, reverse=True)

        if start:
            episodes = [e for e in episodes if e.timestamp >= start]
        if end:
            episodes = [e for e in episodes if e.timestamp <= end]

        return episodes[:limit]

    def recall_by_participant(self, participant: str, limit: int = 20) -> List[Episode]:
        """Recall episodes involving a specific participant."""
        return sorted(
            [e for e in self.episodes.values()
             if any(participant.lower() in p.lower() for p in e.participants)],
            key=lambda e: e.timestamp, reverse=True
        )[:limit]

    def recall_by_topic(self, topic: str, limit: int = 20) -> List[Episode]:
        """Recall episodes about a topic."""
        results = []
        for ep in self.episodes.values():
            if topic.lower() in ep.topic.lower() or topic.lower() in ep.content.lower():
                results.append(ep)
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def search(self, query: str, top_k: int = 10) -> List[Tuple[Episode, float]]:
        """Search episodes by content similarity."""
        query_kw = set(PersianNLP.extract_keywords(query))
        if not query_kw:
            return []

        results = []
        for ep in self.episodes.values():
            ep_kw = set(PersianNLP.extract_keywords(ep.content))
            overlap = len(query_kw & ep_kw)
            if overlap > 0:
                score = overlap / max(len(query_kw), 1) * ep.importance
                results.append((ep, score))

        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def _score_importance(self, episode: Episode) -> float:
        """Score importance of an episode."""
        score = 0.5

        # More participants = more important
        score += min(len(episode.participants) * 0.1, 0.3)

        # Strong emotions = more memorable
        if episode.emotions:
            max_emotion = max(episode.emotions.values())
            score += max_emotion * 0.2

        # Longer content = more detail = potentially more important
        word_count = len(PersianNLP.tokenize(episode.content))
        score += min(word_count * 0.005, 0.15)

        return min(score, 1.0)

    def _find_related(self, episode: Episode, top_k: int = 3) -> List[str]:
        """Find related episodes."""
        ep_kw = set(PersianNLP.extract_keywords(episode.content))
        if not ep_kw:
            return []

        scored = []
        for other in self.episodes.values():
            if other.id == episode.id:
                continue
            other_kw = set(PersianNLP.extract_keywords(other.content))
            overlap = len(ep_kw & other_kw)
            if overlap > 0:
                scored.append((other.id, overlap))
        scored.sort(key=lambda x: -x[1])
        return [eid for eid, _ in scored[:top_k]]

    def format_episode(self, episode: Episode) -> str:
        """Format episode for display."""
        lines = [f"📖 *{episode.content[:100]}*"]
        if episode.timestamp:
            try:
                dt = datetime.fromisoformat(episode.timestamp)
                lines.append(f"  🕐 {dt.strftime('%Y-%m-%d %H:%M')}")
            except (ValueError, TypeError):
                pass
        if episode.participants:
            lines.append(f"  👥 {', '.join(episode.participants)}")
        if episode.location:
            lines.append(f"  📍 {episode.location}")
        if episode.emotions:
            top_em = max(episode.emotions, key=episode.emotions.get)
            lines.append(f"  💭 {top_em}: {episode.emotions[top_em]:.1f}")
        return "\n".join(lines)

    def _save(self) -> Any:
        path = self.brain_dir / "episodes.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {eid: ep.to_dict() for eid, ep in self.episodes.items()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "episodes.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for eid, ep_data in data.items():
                self.episodes[eid] = Episode.from_dict(ep_data)
            self._counter = len(self.episodes)
        except Exception as e:
            logger.warning("Failed to load episodes: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 2. SEMANTIC COMPRESSOR — Merge similar memories
# ═══════════════════════════════════════════════════════════════════

class SemanticCompressor:
    """
    Compresses memory by merging similar/redundant memories.
    - Finds near-duplicate memories
    - Merges them into a single stronger memory
    - Preserves unique information from each source
    """

    def __init__(self, memory_store: Any) -> None:
        self.memory = memory_store

    def find_duplicates(self, similarity_threshold: float = 0.75) -> List[Tuple[str, str, float]]:
        """Find pairs of near-duplicate memories."""
        duplicates = []
        mems = list(self.memory.memories.values())

        for i, mem_a in enumerate(mems):
            for mem_b in mems[i + 1:]:
                if mem_a.topic != mem_b.topic:
                    continue

                sim = self._content_similarity(mem_a.content, mem_b.content)
                if sim >= similarity_threshold:
                    duplicates.append((mem_a.id, mem_b.id, sim))

        return sorted(duplicates, key=lambda x: -x[2])

    def compress(self, dry_run: bool = True) -> List[Dict[str, Any]]:
        """
        Merge near-duplicate memories.
        If dry_run=True, returns what would be merged without actually doing it.
        """
        duplicates = self.find_duplicates()
        merges = []
        merged_ids = set()

        for id_a, id_b, sim in duplicates:
            if id_a in merged_ids or id_b in merged_ids:
                continue

            mem_a = self.memory.memories.get(id_a)
            mem_b = self.memory.memories.get(id_b)
            if not mem_a or not mem_b:
                continue

            # Keep the stronger/older one as base
            if mem_a.strength >= mem_b.strength:
                keeper, removed = mem_a, mem_b
            else:
                keeper, removed = mem_b, mem_a

            # Merge content (keep unique parts from removed)
            merged_content = self._merge_content(keeper.content, removed.content)

            merge_info = {
                "keeper": keeper.id,
                "removed": removed.id,
                "similarity": sim,
                "original_content": keeper.content[:100],
                "merged_content": merged_content[:100],
            }

            if not dry_run:
                # Apply merge
                keeper.content = merged_content
                keeper.strength = max(keeper.strength, removed.strength) + 0.1
                keeper.keywords = list(set(keeper.keywords + removed.keywords))
                keeper.associations = list(set(keeper.associations + removed.associations))
                del self.memory.memories[removed.id]
                merged_ids.add(removed.id)

            merges.append(merge_info)

        if not dry_run:
            self.memory._save_memories()

        return merges

    def _content_similarity(self, a: str, b: str) -> float:
        """Compute content similarity using token overlap and sequence matching."""
        tokens_a = set(PersianNLP.extract_keywords(a))
        tokens_b = set(PersianNLP.extract_keywords(b))
        if not tokens_a or not tokens_b:
            return 0.0

        jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
        seq_ratio = SequenceMatcher(None, a, b).ratio()
        return jaccard * 0.6 + seq_ratio * 0.4

    def _merge_content(self, base: str, other: str) -> str:
        """Merge two memory contents, keeping unique info from both."""
        base_tokens = set(PersianNLP.tokenize(base))
        other_tokens = set(PersianNLP.tokenize(other))

        unique_other = other_tokens - base_tokens - PersianNLP.STOPWORDS
        if unique_other and len(unique_other) > 2:
            # Find the sentences in 'other' that contain unique tokens
            other_parts = re.split(r'[.!؟?،]\s*', other)
            additions = []
            for part in other_parts:
                part_tokens = set(PersianNLP.tokenize(part))
                if part_tokens & unique_other:
                    additions.append(part.strip())
            if additions:
                return base + " | " + " ".join(additions[:2])
        return base


# ═══════════════════════════════════════════════════════════════════
# 3. KNOWLEDGE VERSIONING — Track changes over time
# ═══════════════════════════════════════════════════════════════════

@dataclass
class KnowledgeVersion:
    topic: str
    content: str
    version: int
    timestamp: str
    source: str
    change_type: str  # "created", "updated", "corrected", "merged"
    previous_content: str = ""


class KnowledgeVersioning:
    """
    Tracks how knowledge evolves over time:
    - Every update creates a version
    - Can compare versions
    - Can revert to previous state
    - Tracks who/when changed what
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.versions: Dict[str, List[KnowledgeVersion]] = defaultdict(list)
        self._load()

    def record_version(self, topic: str, content: str, source: str = "admin",
                       change_type: str = "updated", previous: str = "") -> Any:
        """Record a new version of knowledge."""
        topic_versions = self.versions[topic]
        version_num = len(topic_versions) + 1

        kv = KnowledgeVersion(
            topic=topic,
            content=content,
            version=version_num,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            change_type=change_type,
            previous_content=previous,
        )
        topic_versions.append(kv)

        if len(topic_versions) % 5 == 0:
            self._save()

    def get_history(self, topic: str) -> List[KnowledgeVersion]:
        """Get version history for a topic."""
        return self.versions.get(topic, [])

    def get_latest(self, topic: str) -> Optional[KnowledgeVersion]:
        """Get latest version of a topic."""
        history = self.versions.get(topic, [])
        return history[-1] if history else None

    def diff(self, topic: str, version_a: int, version_b: int) -> Dict[str, Any]:
        """Compare two versions of a topic."""
        history = self.versions.get(topic, [])
        va = next((v for v in history if v.version == version_a), None)
        vb = next((v for v in history if v.version == version_b), None)

        if not va or not vb:
            return {"error": "نسخه پیدا نشد"}

        a_tokens = set(PersianNLP.tokenize(va.content))
        b_tokens = set(PersianNLP.tokenize(vb.content))

        return {
            "topic": topic,
            "version_a": version_a,
            "version_b": version_b,
            "added": list(b_tokens - a_tokens),
            "removed": list(a_tokens - b_tokens),
            "common": len(a_tokens & b_tokens),
            "similarity": SequenceMatcher(None, va.content, vb.content).ratio(),
        }

    def format_history(self, topic: str) -> str:
        """Format version history as readable text."""
        history = self.versions.get(topic, [])
        if not history:
            return f"📜 تاریخچه‌ای برای «{topic}» ثبت نشده."

        lines = [f"📜 *تاریخچه دانش: {topic}* ({len(history)} نسخه)\n"]
        for v in reversed(history[-10:]):
            try:
                dt = datetime.fromisoformat(v.timestamp).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                dt = v.timestamp
            type_emoji = {
                "created": "🆕", "updated": "✏️",
                "corrected": "🔧", "merged": "🔀",
            }.get(v.change_type, "📝")
            lines.append(f"  {type_emoji} v{v.version} [{dt}] ({v.source})")
            lines.append(f"     {v.content[:80]}")
        return "\n".join(lines)

    def _save(self) -> Any:
        path = self.brain_dir / "knowledge_versions.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for topic, versions in self.versions.items():
            data[topic] = [
                {
                    "topic": v.topic, "content": v.content,
                    "version": v.version, "timestamp": v.timestamp,
                    "source": v.source, "change_type": v.change_type,
                    "previous_content": v.previous_content,
                }
                for v in versions[-50:]  # Keep last 50 versions per topic
            ]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "knowledge_versions.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for topic, versions in data.items():
                self.versions[topic] = [
                    KnowledgeVersion(**v) for v in versions
                ]
        except Exception as e:
            logger.warning("Failed to load knowledge versions: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 4. CROSS-TOPIC INFERENCE — Discover hidden connections
# ═══════════════════════════════════════════════════════════════════

class CrossTopicInference:
    """
    Discovers connections between seemingly unrelated topics:
    - Shared keywords across topics
    - Bridging concepts
    - Analogical connections
    - Co-occurrence patterns
    """

    def __init__(self, memory_store: Any) -> None:
        self.memory = memory_store

    def find_bridges(self, topic_a: str, topic_b: str) -> List[Tuple[str, float]]:
        """
        Find bridging concepts between two topics.
        A concept is a bridge if it's related to both topics.
        """
        a_keywords = set()
        b_keywords = set()

        for mem in self.memory.memories.values():
            if mem.topic == topic_a:
                a_keywords.update(mem.keywords)
            elif mem.topic == topic_b:
                b_keywords.update(mem.keywords)

        bridges = a_keywords & b_keywords
        if not bridges:
            # Try graph neighbors
            a_neighbors = set()
            b_neighbors = set()
            for edge in self.memory.graph_edges:
                if topic_a.lower() in edge.from_node.lower():
                    a_neighbors.add(edge.to_node)
                if topic_b.lower() in edge.from_node.lower():
                    b_neighbors.add(edge.to_node)
            bridges = a_neighbors & b_neighbors

        # Score bridges by relevance
        scored = []
        for bridge in bridges:
            # Count how many memories in each topic mention this bridge
            a_count = sum(1 for m in self.memory.memories.values()
                         if m.topic == topic_a and bridge in m.keywords)
            b_count = sum(1 for m in self.memory.memories.values()
                         if m.topic == topic_b and bridge in m.keywords)
            score = min(a_count, b_count) / max(a_count + b_count, 1)
            scored.append((bridge, score))

        return sorted(scored, key=lambda x: -x[1])

    def discover_connections(self, min_shared: int = 2) -> List[Dict[str, Any]]:
        """
        Discover all topic pairs with hidden connections.
        """
        # Build topic → keywords map
        topic_keywords: Dict[str, Counter] = defaultdict(Counter)
        for mem in self.memory.memories.values():
            for kw in mem.keywords:
                topic_keywords[mem.topic][kw] += 1

        topics = list(topic_keywords.keys())
        connections = []

        for i, topic_a in enumerate(topics):
            for topic_b in topics[i + 1:]:
                shared = set(topic_keywords[topic_a].keys()) & set(topic_keywords[topic_b].keys())
                # Filter to meaningful shared keywords
                meaningful = {kw for kw in shared
                             if kw not in PersianNLP.STOPWORDS and len(kw) > 1}
                if len(meaningful) >= min_shared:
                    connections.append({
                        "topic_a": topic_a,
                        "topic_b": topic_b,
                        "shared_concepts": list(meaningful)[:10],
                        "strength": len(meaningful),
                    })

        return sorted(connections, key=lambda x: -x["strength"])

    def infer_new_knowledge(self, topic: str) -> List[str]:
        """
        Infer new knowledge about a topic based on cross-topic connections.
        """
        inferences = []
        connections = self.discover_connections()

        for conn in connections:
            if topic not in (conn["topic_a"], conn["topic_b"]):
                continue

            other_topic = conn["topic_b"] if conn["topic_a"] == topic else conn["topic_a"]
            shared = conn["shared_concepts"]

            # Get knowledge from other topic that mentions shared concepts
            for mem in self.memory.memories.values():
                if mem.topic == other_topic:
                    mem_kw = set(mem.keywords)
                    if mem_kw & set(shared):
                        inferences.append(
                            f"از {other_topic}: {mem.content[:150]}"
                        )

        return inferences[:10]


# ═══════════════════════════════════════════════════════════════════
# 5. IMPORTANCE SCORER — Multi-factor importance ranking
# ═══════════════════════════════════════════════════════════════════

class ImportanceScorer:
    """
    Scores memory importance using multiple factors:
    - Recency (newer = potentially more important)
    - Access frequency (more accessed = more useful)
    - Strength (reinforced knowledge)
    - Uniqueness (rare knowledge is more valuable)
    - Connectivity (well-connected in graph = hub knowledge)
    - Source authority (admin > user > auto)
    """

    SOURCE_WEIGHTS = {
        "admin": 1.0, "owner": 0.9, "moderator": 0.7,
        "user": 0.5, "auto": 0.3, "inferred": 0.2,
    }

    def __init__(self, memory_store: Any) -> None:
        self.memory = memory_store

    def score(self, memory_id: str) -> Dict[str, float]:
        """
        Compute multi-factor importance score.
        Returns breakdown of factors.
        """
        mem = self.memory.memories.get(memory_id)
        if not mem:
            return {"total": 0}

        factors = {}

        # 1. Recency (exponential decay over days)
        try:
            created = datetime.fromisoformat(mem.created_at)
            age_days = (datetime.now(timezone.utc) - created).total_seconds() / 86400
            factors["recency"] = math.exp(-0.01 * age_days)
        except (ValueError, TypeError):
            factors["recency"] = 0.5

        # 2. Access frequency (normalized)
        max_access = max((m.access_count for m in self.memory.memories.values()), default=1)
        factors["access"] = mem.access_count / max(max_access, 1)

        # 3. Strength
        factors["strength"] = min(mem.strength / 5.0, 1.0)

        # 4. Uniqueness (inverse of how many memories share same topic)
        topic_count = sum(1 for m in self.memory.memories.values() if m.topic == mem.topic)
        factors["uniqueness"] = 1.0 / math.sqrt(max(topic_count, 1))

        # 5. Connectivity (graph connections)
        connections = len(mem.associations)
        for edge in self.memory.graph_edges:
            if mem.topic.lower() in edge.from_node.lower() or mem.topic.lower() in edge.to_node.lower():
                connections += 1
        factors["connectivity"] = min(connections / 10.0, 1.0)

        # 6. Source authority
        factors["authority"] = self.SOURCE_WEIGHTS.get(mem.source, 0.3)

        # Weighted total
        weights = {
            "recency": 0.15, "access": 0.20, "strength": 0.25,
            "uniqueness": 0.10, "connectivity": 0.15, "authority": 0.15,
        }
        total = sum(factors[k] * weights[k] for k in weights)
        factors["total"] = total

        return factors

    def rank_all(self, top_k: int = None) -> List[Tuple[str, float]]:
        """Rank all memories by importance."""
        ranked = []
        for mid in self.memory.memories:
            total = self.score(mid)["total"]
            ranked.append((mid, total))
        ranked.sort(key=lambda x: -x[1])
        return ranked[:top_k] if top_k else ranked

    def suggest_forget(self, threshold: float = 0.1,
                       max_forget: int = 10) -> List[Tuple[str, float, str]]:
        """Suggest memories that could be forgotten (low importance)."""
        ranked = self.rank_all()
        suggestions = []
        for mid, score in reversed(ranked):
            if score < threshold:
                mem = self.memory.memories.get(mid)
                if mem:
                    suggestions.append((mid, score, mem.content[:100]))
                if len(suggestions) >= max_forget:
                    break
        return suggestions

    def suggest_reinforce(self, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """Suggest important memories that should be reinforced."""
        ranked = self.rank_all()
        suggestions = []
        for mid, score in ranked:
            mem = self.memory.memories.get(mid)
            if mem and mem.access_count < 3 and score > 0.5:
                suggestions.append((mid, score, mem.content[:100]))
            if len(suggestions) >= top_k:
                break
        return suggestions


