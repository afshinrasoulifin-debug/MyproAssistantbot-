
from __future__ import annotations
"""Victor v7.0 TITAN — Reasoning Engine (multi-hop + inference + analogy)"""

from typing import Dict, List, Optional, Tuple

from .memory import MemoryStore
from .nlp import PersianNLP
from .constants import MAX_GRAPH_HOPS

# ═══════════════════════════════════════════════════════════════════
# 3. REASONING ENGINE v5 — Multi-hop + Inference + Analogy
# ═══════════════════════════════════════════════════════════════════

class ReasoningEngine:
    """
    v5: Advanced algorithmic reasoning over the knowledge graph and memories.
    Supports: direct recall, multi-hop reasoning, inference rules,
    analogical reasoning, and context-aware disambiguation.
    """

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def reason(self, query: str, context: List[Dict] = None) -> Tuple[str, float]:
        """
        Main reasoning pipeline:
        0. Penetration Awareness (Strategic Layer)
        1. Direct recall (highest confidence)
        2. Inference rules
        3. Multi-hop graph reasoning
        4. Analogical reasoning
        5. Context-based disambiguation

        Returns: (answer, confidence_score)
        """
        # 0. Penetration Awareness
        if any(kw in query.lower() for kw in ["نفوذ", "بای‌پس", "دسترسی", "دیواره آتش", "پروکسی"]):
            strat_answer, strat_conf = self._penetration_reasoning(query)
            if strat_conf > 80:
                return strat_answer, strat_conf
        # 1. Direct recall
        answer, confidence = self._direct_recall(query)
        if confidence > 70:
            return answer, confidence

        # 2. Inference rules
        rule_answer, rule_conf = self._apply_rules(query)
        if rule_conf > confidence:
            answer, confidence = rule_answer, rule_conf

        # 3. Multi-hop graph reasoning
        graph_answer, graph_conf = self._graph_reasoning(query)
        if graph_conf > confidence:
            answer, confidence = graph_answer, graph_conf

        # 4. Context-based enhancement
        if context and answer:
            enhanced = self._enhance_with_context(answer, context)
            if enhanced != answer:
                answer = enhanced
                confidence = min(confidence + 5, 95)

        return answer, confidence

    def _direct_recall(self, query: str) -> Tuple[str, float]:
        """Direct memory lookup with BM25 scoring."""
        memories = self.memory.recall(query, top_k=8)
        if not memories:
            return "", 0.0

        parts = []
        used_topics = set()
        total_strength = 0

        for mem in memories:
            if mem.topic not in used_topics:
                parts.append(f"• {mem.content}")
                used_topics.add(mem.topic)
                total_strength += mem.strength

                # Follow associations
                for assoc_id in mem.associations[:2]:
                    if assoc_id in self.memory.memories:
                        assoc_mem = self.memory.memories[assoc_id]
                        if assoc_mem.topic not in used_topics:
                            parts.append(f"  ↳ مرتبط: {assoc_mem.content}")
                            used_topics.add(assoc_mem.topic)

        # Reinforce accessed memories
        for mem in memories[:3]:
            self.memory.reinforce(mem.id, 0.1)

        if parts:
            avg_strength = total_strength / max(1, len(memories))
            confidence = min(40 + avg_strength * 10 + len(memories) * 5, 90)
            return "\n".join(parts), confidence

        return "", 0.0

    def _apply_rules(self, query: str) -> Tuple[str, float]:
        """Apply inference rules to the query."""
        matched_rules = self.memory.match_rules(query)
        if not matched_rules:
            return "", 0.0

        parts = []
        max_conf = 0.0

        for rule, score in matched_rules[:3]:
            parts.append(f"📏 {rule.conclusion}")
            rule.use_count += 1
            max_conf = max(max_conf, score)

        if parts:
            self.memory._save_rules()
            return "\n".join(parts), min(max_conf, 85)
        return "", 0.0

    def _graph_reasoning(self, query: str) -> Tuple[str, float]:
        """
        Multi-hop reasoning on the knowledge graph.
        Traverses relationships to find indirect answers.
        """
        keywords = PersianNLP.extract_keywords(query)
        if not keywords:
            return "", 0.0

        parts = []
        total_weight = 0.0

        for kw in keywords[:5]:
            # Get related concepts (up to MAX_GRAPH_HOPS hops)
            related = self.memory.get_related(kw, max_hops=MAX_GRAPH_HOPS)

            for concept, relation, weight, hops in related[:5]:
                # Find memories about the related concept
                concept_memories = self.memory.recall(concept, top_k=2)
                for cm in concept_memories:
                    rel_display = relation.replace("inv_", "← ").replace("_", " ")
                    hop_indicator = "→" * hops
                    parts.append(f"  {hop_indicator} [{kw} {rel_display} {concept}]: {cm.content[:150]}")
                    total_weight += weight

        if parts:
            # Deduplicate
            unique_parts = list(dict.fromkeys(parts))[:8]
            confidence = min(30 + total_weight * 10, 75)
            header = "🔗 استدلال از روی گراف دانش:\n"
            return header + "\n".join(unique_parts), confidence
        return "", 0.0

    def _enhance_with_context(self, answer: str, context: List[Dict]) -> str:
        """
        Use recent conversation context to disambiguate and enhance answer.
        """
        if not context:
            return answer

        recent_topics = set()
        for c in context[-5:]:
            recent_topics.update(c.get("keywords", []))

        # If answer mentions multiple topics, prioritize the one in context
        # This is a simple heuristic — context narrows the answer
        if recent_topics:
            context_hint = " | ".join(list(recent_topics)[:5])
            return f"{answer}\n\n💭 _(با توجه به مکالمه اخیر: {context_hint})_"

        return answer

    def find_analogy(self, concept_a: str, concept_b: str, concept_c: str) -> Optional[str]:
        """
        Analogical reasoning: A is to B as C is to ?
        Uses knowledge graph relationships.
        """
        # Find the relationship between A and B
        for edge in self.memory.graph_edges:
            if (concept_a.lower() in edge.from_node.lower()
                    and concept_b.lower() in edge.to_node.lower()):
                relation = edge.relation

                # Find what has the same relationship with C
                for e2 in self.memory.graph_edges:
                    if (concept_c.lower() in e2.from_node.lower()
                            and e2.relation == relation):
                        return e2.to_node

            # Try reverse too
            if (concept_b.lower() in edge.from_node.lower()
                    and concept_a.lower() in edge.to_node.lower()):
                relation = edge.relation
                for e2 in self.memory.graph_edges:
                    if (e2.relation == relation
                            and concept_c.lower() in e2.to_node.lower()):
                        return e2.from_node

        return None

    def _penetration_reasoning(self, query: str) -> Tuple[str, float]:
        """Strategic reasoning for penetration and stealth operations."""
        # Task: Quantum Strategic Intelligence
        header = "🛡️ تحلیل استراتژیک نفوذ (DEEP-TITANIUM):\n"
        if "بای‌پس" in query or "نفوذ" in query:
            return header + "• فعال‌سازی پشته شبکه QUANTUM-REAL\n• استفاده از آنتروپی رفتاری برای دور زدن WAF\n• چرخش هویت در لایه L2 (TLS Impersonation)", 95.0
        return "", 0.0

    def can_answer(self, query: str) -> bool:
        """Check if we have enough knowledge to answer."""
        memories = self.memory.recall(query, top_k=3)
        if memories:
            return True
        # Also check rules
        rules = self.memory.match_rules(query)
        return bool(rules)


