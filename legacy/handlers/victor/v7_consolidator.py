
from __future__ import annotations
"""Victor v7.0 TITAN — Memory Consolidator (merge, decay, strengthen)"""

import math
import time
from datetime import datetime
from typing import Any, Dict, List

from .memory import MemoryStore
from .nlp import PersianNLP

# ═══════════════════════════════════════════════════════════════════
# 10. MEMORY CONSOLIDATOR — v7 Brain Maintenance
# ═══════════════════════════════════════════════════════════════════

class MemoryConsolidator:
    """
    v7: Maintains brain health by merging duplicates, strengthening
    important memories, and decaying unused ones.
    """

    def __init__(self, memory_store: "MemoryStore") -> None:
        self.memory = memory_store
        self._last_consolidation: float = 0.0
        self._merge_log: List[Dict[str, Any]] = []

    def consolidate(self) -> Dict[str, int]:
        """Run full consolidation cycle. Returns stats."""
        stats = {
            "merged": 0,
            "decayed": 0,
            "strengthened": 0,
            "removed": 0,
        }

        # 1. Merge similar memories
        stats["merged"] = self._merge_duplicates()

        # 2. Decay old, unused memories
        stats["decayed"] = self._apply_decay()

        # 3. Strengthen frequently accessed memories
        stats["strengthened"] = self._strengthen_popular()

        # 4. Remove very weak memories
        stats["removed"] = self._prune_weak()

        self._last_consolidation = time.time()
        self.memory._rebuild_tfidf_index()
        self.memory._save_memories()

        return stats

    def _merge_duplicates(self, similarity_threshold: float = 0.85) -> int:
        """Merge memories that are very similar."""
        merged_count = 0
        memories = list(self.memory.memories.values())
        to_remove = set()

        for i in range(len(memories)):
            if memories[i].id in to_remove:
                continue
            for j in range(i + 1, len(memories)):
                if memories[j].id in to_remove:
                    continue
                # Same topic and high similarity
                if memories[i].topic.lower() == memories[j].topic.lower():
                    sim = PersianNLP.similarity(memories[i].content, memories[j].content)
                    if sim >= similarity_threshold:
                        # Keep the stronger one, merge content
                        keeper = memories[i] if memories[i].strength >= memories[j].strength else memories[j]
                        loser = memories[j] if keeper == memories[i] else memories[i]

                        # Merge: combine unique keywords, boost strength
                        keeper.keywords = list(set(keeper.keywords + loser.keywords))[:30]
                        keeper.strength = min(10.0, keeper.strength + loser.strength * 0.3)
                        keeper.access_count += loser.access_count
                        keeper.associations = list(set(keeper.associations + loser.associations))[:20]

                        # If loser has unique content, append it
                        if len(loser.content) > len(keeper.content):
                            keeper.content = loser.content

                        to_remove.add(loser.id)
                        merged_count += 1

                        self._merge_log.append({
                            "ts": time.time(),
                            "kept": keeper.id,
                            "removed": loser.id,
                            "similarity": sim,
                        })

        for mid in to_remove:
            self.memory.memories.pop(mid, None)

        return merged_count

    def _apply_decay(self) -> int:
        """Apply Ebbinghaus forgetting curve to old, unused memories."""
        decayed = 0
        now = time.time()

        for mem in self.memory.memories.values():
            if mem.last_accessed:
                try:
                    last_ts = datetime.fromisoformat(mem.last_accessed).timestamp()
                except (ValueError, TypeError):
                    last_ts = now
            else:
                last_ts = now

            hours_since = (now - last_ts) / 3600
            if hours_since > 24:  # Only decay after 24 hours of no access
                decay = FORGETTING_RATE * math.log(1 + hours_since / 24)
                old_strength = mem.strength
                mem.strength = max(0.1, mem.strength - decay)
                if mem.strength < old_strength:
                    decayed += 1

        return decayed

    def _strengthen_popular(self) -> int:
        """Strengthen memories that are accessed frequently."""
        strengthened = 0
        for mem in self.memory.memories.values():
            if mem.access_count > 5:
                bonus = math.log(1 + mem.access_count) * 0.1
                old = mem.strength
                mem.strength = min(10.0, mem.strength + bonus)
                if mem.strength > old:
                    strengthened += 1
        return strengthened

    def _prune_weak(self, min_strength: float = 0.15) -> int:
        """Remove memories that are too weak to be useful."""
        to_remove = [
            mid for mid, mem in self.memory.memories.items()
            if mem.strength < min_strength and mem.memory_type not in ("correction", "pattern")
        ]
        for mid in to_remove:
            self.memory.memories.pop(mid, None)
        return len(to_remove)

    def format_report(self) -> str:
        """Format consolidation report."""
        stats = self.consolidate()
        return (
            f"🔧 *نتیجه یکپارچه‌سازی حافظه:*\n\n"
            f"  🔗 ادغام شده: {stats['merged']} خاطره\n"
            f"  📉 تضعیف شده: {stats['decayed']} خاطره\n"
            f"  💪 تقویت شده: {stats['strengthened']} خاطره\n"
            f"  🗑️ حذف شده: {stats['removed']} خاطره\n\n"
            f"  📊 کل خاطرات بعد از یکپارچه‌سازی: {len(self.memory.memories)}"
        )


