
from __future__ import annotations
"""Victor v7.0 TITAN — Topic Clusterer (hierarchical + bridges)"""

import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import Memory
from .memory import MemoryStore
from .nlp import PersianNLP

# ═══════════════════════════════════════════════════════════════════
# 8. TOPIC CLUSTERER — v7 Auto-organize Knowledge
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TopicCluster:
    """A cluster of related memories with hierarchy support."""
    cluster_id: str
    label: str               # Auto-generated label
    memory_ids: List[str]
    centroid_keywords: List[str]
    size: int = 0
    coherence: float = 0.0   # How tightly related the memories are
    parent_id: Optional[str] = None   # Hierarchical clustering
    sub_clusters: List[str] = None    # Child cluster IDs
    summary: str = ""                 # Auto-generated summary

class TopicClusterer:
    """
    v7 TITAN: Deep topic clustering with:
    - Hierarchical clusters (parent → child)
    - Cross-cluster bridges (shared keywords between clusters)
    - Auto-summary for each cluster
    - Cluster-based intelligent retrieval
    - Cluster evolution tracking
    """

    def __init__(self, memory_store: "MemoryStore") -> None:
        self.memory = memory_store
        self._clusters: List[TopicCluster] = []
        self._last_clustered: float = 0.0
        self._bridges: List[Dict[str, Any]] = []  # Cross-cluster connections
        self._evolution: List[Dict[str, Any]] = []  # Track cluster changes over time

    def cluster(self, min_cluster_size: int = 2, similarity_threshold: float = 0.3) -> List[TopicCluster]:
        """Run deep clustering on all memories with hierarchical support."""
        memories = list(self.memory.memories.values())
        if len(memories) < min_cluster_size:
            self._clusters = []
            return []

        # Build keyword vectors per memory (v7: include topic, associations, entity context)
        keyword_sets: Dict[str, Set[str]] = {}
        topic_map: Dict[str, str] = {}  # memory_id → topic
        for mem in memories:
            kw = set(PersianNLP.extract_keywords(mem.content + " " + mem.topic))
            # v7: Also add associations and keywords as features
            kw |= set(mem.keywords[:10])
            kw |= set(mem.associations[:5])
            keyword_sets[mem.id] = kw
            topic_map[mem.id] = mem.topic

        # Phase 1: Fine-grained agglomerative clustering
        clusters: List[Set[str]] = [{mid} for mid in keyword_sets]

        def cluster_similarity(c1: Set[str], c2: Set[str]) -> float:
            kw1 = set()
            kw2 = set()
            for mid in c1:
                kw1 |= keyword_sets.get(mid, set())
            for mid in c2:
                kw2 |= keyword_sets.get(mid, set())
            if not kw1 or not kw2:
                return 0.0
            jaccard = len(kw1 & kw2) / len(kw1 | kw2)
            # v7: Boost if same topic
            topics1 = {topic_map.get(m, "") for m in c1} - {""}
            topics2 = {topic_map.get(m, "") for m in c2} - {""}
            topic_overlap = len(topics1 & topics2) / max(1, len(topics1 | topics2))
            return jaccard * 0.6 + topic_overlap * 0.4

        # Iterative merging
        changed = True
        max_iterations = 100
        iteration = 0
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            best_sim = 0.0
            best_pair = (-1, -1)

            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    sim = cluster_similarity(clusters[i], clusters[j])
                    if sim > best_sim:
                        best_sim = sim
                        best_pair = (i, j)

            if best_sim >= similarity_threshold and best_pair[0] >= 0:
                i, j = best_pair
                clusters[i] = clusters[i] | clusters[j]
                clusters.pop(j)
                changed = True

        # Phase 2: Build TopicCluster objects with deep metadata
        self._clusters = []
        for idx, member_ids in enumerate(clusters):
            if len(member_ids) < min_cluster_size:
                continue

            # Compute centroid keywords (weighted by frequency)
            all_kw: Counter = Counter()
            for mid in member_ids:
                for kw in keyword_sets.get(mid, []):
                    all_kw[kw] += 1
            centroid = [kw for kw, _ in all_kw.most_common(8)]

            # Auto-label: most common topic
            topic_counts: Counter = Counter()
            for mid in member_ids:
                if mid in self.memory.memories:
                    topic_counts[self.memory.memories[mid].topic] += 1
            label = topic_counts.most_common(1)[0][0] if topic_counts else f"cluster_{idx}"

            # v7: Auto-summary from strongest memories
            sorted_mems = sorted(
                [self.memory.memories[m] for m in member_ids if m in self.memory.memories],
                key=lambda m: m.strength, reverse=True
            )
            summary_parts = []
            for m in sorted_mems[:3]:
                snippet = m.content[:100].strip()
                if snippet:
                    summary_parts.append(snippet)
            summary = " | ".join(summary_parts)

            # v7: Compute real coherence (average pairwise similarity)
            total_sim = 0.0
            pair_count = 0
            member_list = list(member_ids)
            for i in range(min(len(member_list), 15)):
                for j in range(i + 1, min(len(member_list), 15)):
                    kw_i = keyword_sets.get(member_list[i], set())
                    kw_j = keyword_sets.get(member_list[j], set())
                    if kw_i and kw_j:
                        total_sim += len(kw_i & kw_j) / len(kw_i | kw_j)
                        pair_count += 1
            coherence = total_sim / max(1, pair_count)

            tc = TopicCluster(
                cluster_id=f"c_{idx}",
                label=label,
                memory_ids=list(member_ids),
                centroid_keywords=centroid,
                size=len(member_ids),
                coherence=coherence,
                sub_clusters=[],
                summary=summary,
            )
            self._clusters.append(tc)

        # Phase 3: Discover cross-cluster bridges
        self._discover_bridges()

        # Phase 4: Track evolution
        self._track_evolution()

        self._last_clustered = time.time()
        return self._clusters

    def _discover_bridges(self) -> Any:
        """Find connections between clusters (shared concepts)."""
        self._bridges = []
        for i in range(len(self._clusters)):
            kw_i = set(self._clusters[i].centroid_keywords)
            for j in range(i + 1, len(self._clusters)):
                kw_j = set(self._clusters[j].centroid_keywords)
                shared = kw_i & kw_j
                if shared:
                    self._bridges.append({
                        "from": self._clusters[i].cluster_id,
                        "from_label": self._clusters[i].label,
                        "to": self._clusters[j].cluster_id,
                        "to_label": self._clusters[j].label,
                        "shared_keywords": list(shared),
                        "strength": len(shared) / max(1, len(kw_i | kw_j)),
                    })

    def _track_evolution(self) -> Any:
        """Track how clusters change over time."""
        snapshot = {
            "ts": time.time(),
            "count": len(self._clusters),
            "sizes": [c.size for c in self._clusters],
            "labels": [c.label for c in self._clusters],
        }
        self._evolution.append(snapshot)
        # Keep last 50 snapshots
        self._evolution = self._evolution[-50:]

    def get_clusters(self, refresh: bool = False) -> List[TopicCluster]:
        """Get cached clusters or re-cluster if stale."""
        if refresh or not self._clusters or (time.time() - self._last_clustered > 3600):
            return self.cluster()
        return self._clusters

    def find_cluster_for_query(self, query: str) -> Optional[TopicCluster]:
        """Find the best matching cluster for a query."""
        query_kw = set(PersianNLP.extract_keywords(query))
        if not query_kw:
            return None
        best_cluster = None
        best_score = 0.0

        for cluster in self.get_clusters():
            centroid_kw = set(cluster.centroid_keywords)
            if not centroid_kw:
                continue
            overlap = len(query_kw & centroid_kw) / max(1, len(centroid_kw))
            if overlap > best_score:
                best_score = overlap
                best_cluster = cluster

        return best_cluster if best_score > 0.15 else None

    def get_related_clusters(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Get clusters related to a given cluster via bridges."""
        related = []
        for bridge in self._bridges:
            if bridge["from"] == cluster_id:
                related.append(bridge)
            elif bridge["to"] == cluster_id:
                # Reverse direction
                related.append({
                    **bridge,
                    "from": bridge["to"],
                    "from_label": bridge["to_label"],
                    "to": bridge["from"],
                    "to_label": bridge["from_label"],
                })
        return sorted(related, key=lambda x: x["strength"], reverse=True)

    def deep_retrieve(self, query: str, max_results: int = 10) -> List[Memory]:
        """
        v7 TITAN: Deep cluster-aware retrieval.
        1. Find best cluster
        2. Get memories from cluster
        3. Follow bridges to related clusters
        4. Merge and rank results
        """
        results: List[Tuple[Memory, float]] = []
        query_kw = set(PersianNLP.extract_keywords(query))

        cluster = self.find_cluster_for_query(query)
        if not cluster:
            return []

        # Get memories from primary cluster
        for mid in cluster.memory_ids:
            if mid in self.memory.memories:
                mem = self.memory.memories[mid]
                mem_kw = set(mem.keywords)
                relevance = len(query_kw & mem_kw) / max(1, len(query_kw)) * mem.strength
                results.append((mem, relevance))

        # Follow bridges to related clusters
        related = self.get_related_clusters(cluster.cluster_id)
        for bridge in related[:2]:  # Max 2 bridge-hops
            for c in self._clusters:
                if c.cluster_id == bridge["to"]:
                    for mid in c.memory_ids[:5]:  # Limit from related clusters
                        if mid in self.memory.memories:
                            mem = self.memory.memories[mid]
                            mem_kw = set(mem.keywords)
                            # Discount score for bridge-hopped results
                            relevance = len(query_kw & mem_kw) / max(1, len(query_kw)) * mem.strength * 0.6
                            results.append((mem, relevance))

        # Sort by relevance, deduplicate
        results.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        final = []
        for mem, score in results:
            if mem.id not in seen:
                seen.add(mem.id)
                final.append(mem)
            if len(final) >= max_results:
                break

        return final

    def format_clusters(self) -> str:
        """Format clusters for display — deep view with bridges."""
        clusters = self.get_clusters(refresh=True)
        if not clusters:
            return "🗂️ هنوز خوشه‌ای کشف نشده. بیشتر یاد بده!"

        total_memories = sum(c.size for c in clusters)
        lines = [
            f"🗂️ *خوشه‌های دانش عمیق ({len(clusters)} خوشه | {total_memories} خاطره):*\n"
        ]

        for c in sorted(clusters, key=lambda x: x.size, reverse=True):
            kw_str = "، ".join(c.centroid_keywords[:5])
            coherence_bar = "🟢" * int(c.coherence * 5) + "⚪" * (5 - int(c.coherence * 5))
            lines.append(
                f"  📦 *{c.label}* ({c.size} خاطره)\n"
                f"     کلیدواژه‌ها: {kw_str}\n"
                f"     انسجام: {coherence_bar}"
            )
            if c.summary:
                lines.append(f"     خلاصه: {c.summary[:120]}...")

            # Show bridges
            related = self.get_related_clusters(c.cluster_id)
            if related:
                bridge_str = ", ".join(
                    f"{b['to_label']}({'،'.join(b['shared_keywords'][:2])})"
                    for b in related[:3]
                )
                lines.append(f"     🔗 پل‌ها: {bridge_str}")
            lines.append("")

        # Evolution info
        if len(self._evolution) > 1:
            prev = self._evolution[-2]
            curr = self._evolution[-1]
            delta = curr["count"] - prev["count"]
            if delta > 0:
                lines.append(f"📈 رشد: +{delta} خوشه جدید نسبت به آخرین بررسی")
            elif delta < 0:
                lines.append(f"📉 ادغام: {abs(delta)} خوشه ادغام شدند")
            else:
                lines.append("📊 تعداد خوشه‌ها پایدار")

        return "\n".join(lines)

    def format_cluster_detail(self, label: str) -> str:
        """Show detailed view of a specific cluster."""
        clusters = self.get_clusters()
        target = None
        for c in clusters:
            if c.label.lower() == label.lower() or c.cluster_id == label:
                target = c
                break

        if not target:
            return f"❌ خوشه «{label}» پیدا نشد."

        lines = [
            f"📦 *جزئیات خوشه: {target.label}*\n",
            f"🆔 شناسه: `{target.cluster_id}`",
            f"📏 تعداد خاطرات: {target.size}",
            f"🎯 انسجام: {target.coherence:.2f}",
            f"🔑 کلیدواژه‌ها: {', '.join(target.centroid_keywords)}",
        ]

        if target.summary:
            lines.append(f"\n📝 *خلاصه:*\n{target.summary}")

        # Show memories
        lines.append(f"\n📚 *خاطرات ({min(10, target.size)} نمایش):*")
        mems = [
            self.memory.memories[mid]
            for mid in target.memory_ids
            if mid in self.memory.memories
        ]
        mems.sort(key=lambda m: m.strength, reverse=True)
        for i, mem in enumerate(mems[:10], 1):
            strength_bar = "█" * int(mem.strength) + "░" * (10 - int(mem.strength))
            lines.append(
                f"  {i}. [{strength_bar}] *{mem.topic}*\n"
                f"     {mem.content[:120]}..."
            )

        # Show bridges
        related = self.get_related_clusters(target.cluster_id)
        if related:
            lines.append("\n🔗 *پل‌ها به خوشه‌های دیگر:*")
            for bridge in related:
                shared = ", ".join(bridge["shared_keywords"])
                lines.append(f"  → {bridge['to_label']} (مشترک: {shared})")

        return "\n".join(lines)


