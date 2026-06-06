
from __future__ import annotations
"""Victor v7.0 TITAN — Knowledge Auto-Linker (auto graph growth)"""

from typing import Dict, List

from .models import KnowledgeEdge
from .memory import MemoryStore
from .nlp import PersianNLP

# ═══════════════════════════════════════════════════════════════════
# 11. KNOWLEDGE AUTO-LINKER — v7 Auto Graph Growth
# ═══════════════════════════════════════════════════════════════════

class KnowledgeAutoLinker:
    """
    v7: Automatically discovers and adds knowledge graph edges
    from text content. Grows the graph without explicit /relate commands.
    """

    def __init__(self, memory_store: "MemoryStore") -> None:
        self.memory = memory_store
        self._discovered_count = 0

    def auto_link(self, text: str, topic: str = "") -> List[KnowledgeEdge]:
        """Extract relations from text and add to knowledge graph."""
        new_edges = []

        # 1. Extract explicit relations from text
        triples = PersianNLP.extract_relations_from_text(text)
        for subj, rel, obj in triples:
            edge = KnowledgeEdge(
                from_node=subj, to_node=obj, relation=rel,
                weight=0.7, bidirectional=False,
            )
            # Avoid duplicates
            if not self._edge_exists(subj, obj, rel):
                self.memory.graph_edges.append(edge)
                new_edges.append(edge)

        # 2. Link to existing topics via keyword overlap
        if topic:
            keywords = PersianNLP.extract_keywords(text)
            for mem in self.memory.memories.values():
                if mem.topic.lower() != topic.lower() and mem.id:
                    shared_kw = set(keywords) & set(mem.keywords)
                    if len(shared_kw) >= 2:
                        if not self._edge_exists(topic, mem.topic, "related_to"):
                            edge = KnowledgeEdge(
                                from_node=topic, to_node=mem.topic,
                                relation="related_to",
                                weight=len(shared_kw) * 0.15,
                                bidirectional=True,
                            )
                            self.memory.graph_edges.append(edge)
                            new_edges.append(edge)

        self._discovered_count += len(new_edges)
        if new_edges:
            self.memory._save_graph()
        return new_edges

    def _edge_exists(self, from_node: str, to_node: str, relation: str) -> bool:
        """Check if an edge already exists."""
        fn = from_node.lower()
        tn = to_node.lower()
        for edge in self.memory.graph_edges:
            if (edge.from_node.lower() == fn and edge.to_node.lower() == tn
                    and edge.relation == relation):
                return True
            if edge.bidirectional and edge.from_node.lower() == tn and edge.to_node.lower() == fn:
                return True
        return False

    def stats(self) -> Dict[str, int]:
        return {
            "auto_discovered_edges": self._discovered_count,
            "total_graph_edges": len(self.memory.graph_edges),
        }


