
from __future__ import annotations
"""Victor v7.0 TITAN — Deep Reasoning Engine v2 (Phase 5)

Six reasoning engines that work over the knowledge graph and memories:
- AnalogicalReasoner: A:B :: C:? via structural mapping
- CausalChainEngine: forward/backward causal chain propagation
- TemporalReasoner: temporal ordering and sequence reasoning
- AbductiveReasoner: best-explanation inference
- ConflictResolver: detect and resolve contradictory memories
- OntologyEngine: hierarchical IS-A / PART-OF reasoning
"""

import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

from .nlp import PersianNLP
from .memory import MemoryStore

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. ANALOGICAL REASONER — Structural mapping (not just graph lookup)
# ═══════════════════════════════════════════════════════════════════

class AnalogicalReasoner:
    """
    Structural analogy: finds mappings between domains.
    Given (A → rel → B), finds D such that (C → rel → D).
    Also supports multi-relation analogy: if A has relation-set R to B,
    find D where C has relation-set R to D.
    """

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def find_analogy(self, concept_a: str, concept_b: str,
                     concept_c: str) -> List[Tuple[str, str, float]]:
        """
        A is to B as C is to ?
        Returns list of (answer, explanation, confidence) sorted by confidence.
        """
        results = []

        # Strategy 1: Direct relation mapping
        ab_relations = self._get_relations(concept_a, concept_b)
        if ab_relations:
            for rel, weight in ab_relations:
                candidates = self._find_by_relation(concept_c, rel)
                for cand, w in candidates:
                    conf = min((weight + w) / 2 * 100, 95)
                    explanation = (
                        f"{concept_a} [{rel}] {concept_b} → "
                        f"{concept_c} [{rel}] {cand}"
                    )
                    results.append((cand, explanation, conf))

        # Strategy 2: Property-based analogy
        a_props = self._get_properties(concept_a)
        b_props = self._get_properties(concept_b)
        c_props = self._get_properties(concept_c)

        # Find the "transformation" from A to B
        added = b_props - a_props
        removed = a_props - b_props
        if added or removed:
            # Apply same transformation to C
            d_props = (c_props | added) - removed
            # Find concepts that match d_props
            prop_candidates = self._find_by_properties(d_props)
            for cand, overlap in prop_candidates:
                conf = min(overlap * 20, 80)
                explanation = (
                    f"ویژگی‌های مشترک: {', '.join(list(d_props)[:5])}"
                )
                results.append((cand, explanation, conf))

        # Strategy 3: Contextual similarity (memory-based)
        a_mems = {m.id: m for m in self.memory.recall(concept_a, top_k=5)}
        b_mems = {m.id: m for m in self.memory.recall(concept_b, top_k=5)}
        c_mems = {m.id: m for m in self.memory.recall(concept_c, top_k=5)}

        a_topics = {m.topic for m in a_mems.values()}
        b_topics = {m.topic for m in b_mems.values()}
        c_topics = {m.topic for m in c_mems.values()}

        # What topics B has that A doesn't
        diff_topics = b_topics - a_topics
        # Find memories in those topics related to C
        for topic in diff_topics:
            topic_mems = self.memory.recall(f"{concept_c} {topic}", top_k=3)
            for tm in topic_mems:
                results.append((
                    tm.content[:100],
                    f"قیاس موضوعی: {topic}",
                    min(tm.strength * 15, 65)
                ))

        # Deduplicate and sort
        seen = set()
        unique = []
        for answer, expl, conf in sorted(results, key=lambda x: -x[2]):
            key = answer.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append((answer, expl, conf))
        return unique[:5]

    def _get_relations(self, a: str, b: str) -> List[Tuple[str, float]]:
        """Get all relations from a to b."""
        relations = []
        for edge in self.memory.graph_edges:
            a_low, b_low = a.lower(), b.lower()
            if a_low in edge.from_node.lower() and b_low in edge.to_node.lower():
                relations.append((edge.relation, edge.weight))
            elif edge.bidirectional:
                if b_low in edge.from_node.lower() and a_low in edge.to_node.lower():
                    relations.append((f"inv_{edge.relation}", edge.weight))
        return relations

    def _find_by_relation(self, concept: str, relation: str) -> List[Tuple[str, float]]:
        """Find all X where concept→relation→X."""
        results = []
        c_low = concept.lower()
        inv = relation.startswith("inv_")
        rel = relation[4:] if inv else relation

        for edge in self.memory.graph_edges:
            if edge.relation != rel:
                continue
            if inv:
                if c_low in edge.to_node.lower():
                    results.append((edge.from_node, edge.weight))
            else:
                if c_low in edge.from_node.lower():
                    results.append((edge.to_node, edge.weight))
        return results

    def _get_properties(self, concept: str) -> Set[str]:
        """Extract properties of a concept from memories and graph."""
        props = set()
        mems = self.memory.recall(concept, top_k=5)
        for m in mems:
            props.update(m.keywords)
            props.add(m.topic)

        neighbors = self.memory.get_graph_neighbors(concept)
        for node, rel, w in neighbors:
            props.add(f"{rel}:{node}")
        return props

    def _find_by_properties(self, target_props: Set[str]) -> List[Tuple[str, int]]:
        """Find concepts with matching properties."""
        if not target_props:
            return []
        candidates = defaultdict(int)
        for mem in self.memory.memories.values():
            mem_props = set(mem.keywords) | {mem.topic}
            overlap = len(mem_props & target_props)
            if overlap > 0:
                candidates[mem.topic] = max(candidates[mem.topic], overlap)
        return sorted(candidates.items(), key=lambda x: -x[1])[:5]


# ═══════════════════════════════════════════════════════════════════
# 2. CAUSAL CHAIN ENGINE — Forward/Backward causal propagation
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CausalLink:
    cause: str
    effect: str
    confidence: float = 0.8
    evidence: List[str] = field(default_factory=list)
    timestamp: str = ""


class CausalChainEngine:
    """
    Builds and traverses causal chains:
    - Forward: if X happens, what follows?
    - Backward: what could have caused X?
    - Chain: A → B → C → ...
    - Strength: accumulated confidence along the chain
    """

    CAUSAL_PATTERNS = [
        (r"(.+?)\s+(?:باعث|موجب|سبب|علت)\s+(.+?)\s+(?:می‌?شود|شد|شده)", "causes"),
        (r"(.+?)\s+(?:منجر|ختم)\s+به\s+(.+?)\s+(?:می‌?شود|شد|شده)", "leads_to"),
        (r"اگر\s+(.+?)\s+(?:آنگاه|پس|بنابراین)\s+(.+)", "if_then"),
        (r"(?:به\s+دلیل|به\s+خاطر|به\s+علت)\s+(.+?)[،,]\s*(.+)", "because"),
        (r"(.+?)\s+(?:نتیجه|حاصل|ثمره)\s+(.+)", "result_of"),
        (r"(.+?)\s+(?:تأثیر|اثر)\s+(?:بر|روی)\s+(.+)", "affects"),
        (r"(.+?)\s+(?:پیش‌?نیاز|لازمه)\s+(.+)", "prerequisite"),
        (r"(.+?)\s+(?:مانع|جلوگیر)\s+(.+)", "prevents"),
    ]

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self.causal_links: List[CausalLink] = []
        self._build_from_graph()

    def _build_from_graph(self) -> Any:
        """Extract causal relations from the knowledge graph."""
        causal_rels = {"causes", "leads_to", "if_then", "produces",
                       "prevents", "requires", "affects", "prerequisite"}
        for edge in self.memory.graph_edges:
            if edge.relation in causal_rels:
                self.causal_links.append(CausalLink(
                    cause=edge.from_node,
                    effect=edge.to_node,
                    confidence=edge.weight,
                ))

    def extract_causal(self, text: str) -> List[CausalLink]:
        """Extract causal relations from text using patterns."""
        found = []
        for pattern, rel_type in self.CAUSAL_PATTERNS:
            for m in re.finditer(pattern, text):
                link = CausalLink(
                    cause=m.group(1).strip(),
                    effect=m.group(2).strip() if m.lastindex >= 2 else "",
                    confidence=0.7,
                    evidence=[text[:200]],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                if link.effect:
                    found.append(link)
                    self.causal_links.append(link)
        return found

    def forward_chain(self, cause: str, max_depth: int = 5) -> List[Tuple[str, float, List[str]]]:
        """
        Forward chaining: given cause, what effects follow?
        Returns: [(effect, accumulated_confidence, [chain_path])]
        """
        results = []
        visited = set()
        queue = deque([(cause, 1.0, [cause])])

        while queue:
            current, conf, path = queue.popleft()
            if current in visited or len(path) > max_depth + 1:
                continue
            visited.add(current)

            for link in self.causal_links:
                if self._fuzzy_eq(link.cause, current):
                    new_conf = conf * link.confidence
                    new_path = path + [link.effect]
                    if new_conf > 0.1:  # threshold
                        results.append((link.effect, new_conf, new_path))
                        queue.append((link.effect, new_conf, new_path))

        return sorted(results, key=lambda x: -x[1])

    def backward_chain(self, effect: str, max_depth: int = 5) -> List[Tuple[str, float, List[str]]]:
        """
        Backward chaining: what could have caused this effect?
        Returns: [(possible_cause, confidence, [chain_path])]
        """
        results = []
        visited = set()
        queue = deque([(effect, 1.0, [effect])])

        while queue:
            current, conf, path = queue.popleft()
            if current in visited or len(path) > max_depth + 1:
                continue
            visited.add(current)

            for link in self.causal_links:
                if self._fuzzy_eq(link.effect, current):
                    new_conf = conf * link.confidence
                    new_path = [link.cause] + path
                    if new_conf > 0.1:
                        results.append((link.cause, new_conf, new_path))
                        queue.append((link.cause, new_conf, new_path))

        return sorted(results, key=lambda x: -x[1])

    def find_chain(self, start: str, end: str, max_depth: int = 6) -> Optional[Tuple[List[str], float]]:
        """Find causal chain from start to end."""
        visited = set()
        queue = deque([(start, 1.0, [start])])

        while queue:
            current, conf, path = queue.popleft()
            if self._fuzzy_eq(current, end):
                return path, conf
            if current in visited or len(path) > max_depth:
                continue
            visited.add(current)

            for link in self.causal_links:
                if self._fuzzy_eq(link.cause, current):
                    queue.append((link.effect, conf * link.confidence, path + [link.effect]))

        return None

    def _fuzzy_eq(self, a: str, b: str) -> bool:
        """Fuzzy string match for concept matching."""
        a_low, b_low = a.lower().strip(), b.lower().strip()
        if a_low == b_low:
            return True
        return SequenceMatcher(None, a_low, b_low).ratio() > 0.8

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_causal_links": len(self.causal_links),
            "unique_causes": len({l.cause for l in self.causal_links}),
            "unique_effects": len({l.effect for l in self.causal_links}),
        }


# ═══════════════════════════════════════════════════════════════════
# 3. TEMPORAL REASONER — Time-aware reasoning
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TemporalEvent:
    content: str
    timestamp: Optional[float] = None  # Unix timestamp
    time_expr: str = ""   # Original Persian time expression
    topic: str = ""
    memory_id: str = ""


class TemporalReasoner:
    """
    Reasons about time:
    - Extract temporal expressions from Persian text
    - Order events chronologically
    - Answer "before/after/during/when" questions
    - Detect temporal contradictions
    """

    # Persian temporal patterns
    TEMPORAL_PATTERNS = [
        (r"(?:قبل\s+از|پیش\s+از)\s+(.+)", "before"),
        (r"(?:بعد\s+از|پس\s+از)\s+(.+)", "after"),
        (r"(?:همزمان\s+با|در\s+حین|موقع)\s+(.+)", "during"),
        (r"(?:دیروز|روز\s+گذشته)", "yesterday"),
        (r"(?:امروز|الان|اکنون)", "today"),
        (r"(?:فردا|روز\s+بعد)", "tomorrow"),
        (r"(\d+)\s+(?:روز|هفته|ماه|سال)\s+(?:پیش|قبل)", "past_relative"),
        (r"(\d+)\s+(?:روز|هفته|ماه|سال)\s+(?:بعد|آینده|دیگر)", "future_relative"),
        (r"(?:اول|ابتدا|نخست)", "first"),
        (r"(?:سپس|بعد|آنگاه|سپس)", "then"),
        (r"(?:در\s+نهایت|نهایتاً|بالاخره)", "finally"),
        (r"(?:همیشه|دائماً)", "always"),
        (r"(?:هرگز|هیچ\s*وقت)", "never"),
    ]

    SEQUENCE_WORDS = {
        "اول": 1, "ابتدا": 1, "نخست": 1, "اولین": 1,
        "دوم": 2, "دومین": 2, "سپس": 2, "بعد": 2,
        "سوم": 3, "سومین": 3,
        "چهارم": 4, "پنجم": 5, "ششم": 6,
        "نهایت": 99, "آخر": 99, "بالاخره": 99, "نهایتاً": 99,
    }

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self.timeline: List[TemporalEvent] = []
        self._build_timeline()

    def _build_timeline(self) -> Any:
        """Build timeline from existing memories."""
        for mem in self.memory.memories.values():
            if mem.created_at:
                try:
                    ts = datetime.fromisoformat(mem.created_at).timestamp()
                except (ValueError, TypeError):
                    ts = None
                self.timeline.append(TemporalEvent(
                    content=mem.content,
                    timestamp=ts,
                    topic=mem.topic,
                    memory_id=mem.id,
                ))
        self.timeline.sort(key=lambda e: e.timestamp or 0)

    def extract_temporal(self, text: str) -> List[Tuple[str, str]]:
        """Extract temporal expressions from text."""
        found = []
        for pattern, label in self.TEMPORAL_PATTERNS:
            for m in re.finditer(pattern, text):
                found.append((m.group(0), label))
        return found

    def order_events(self, events: List[str]) -> List[Tuple[str, int]]:
        """
        Given a list of event descriptions, try to order them chronologically.
        Uses sequence words and temporal expressions.
        """
        ordered = []
        for i, event in enumerate(events):
            priority = i  # Default: input order
            tokens = PersianNLP.tokenize(event)
            for token in tokens:
                if token in self.SEQUENCE_WORDS:
                    priority = self.SEQUENCE_WORDS[token]
                    break
            # Check temporal patterns
            for pattern, label in self.TEMPORAL_PATTERNS:
                if re.search(pattern, event):
                    if label in ("before", "first", "past_relative"):
                        priority = max(0, priority - 10)
                    elif label in ("after", "then", "future_relative"):
                        priority += 10
                    elif label == "finally":
                        priority = 100
                    break
            ordered.append((event, priority))
        return sorted(ordered, key=lambda x: x[1])

    def query_timeline(self, query: str, limit: int = 10) -> List[TemporalEvent]:
        """Query timeline for relevant events."""
        keywords = set(PersianNLP.extract_keywords(query))
        if not keywords:
            return self.timeline[-limit:]

        scored = []
        for event in self.timeline:
            event_keywords = set(PersianNLP.extract_keywords(event.content))
            overlap = len(keywords & event_keywords)
            if overlap > 0:
                scored.append((event, overlap))
        scored.sort(key=lambda x: -x[1])
        return [e for e, _ in scored[:limit]]

    def detect_temporal_contradiction(self, event_a: str, event_b: str) -> Optional[str]:
        """Check if two events have temporal contradictions."""
        a_temps = self.extract_temporal(event_a)
        b_temps = self.extract_temporal(event_b)

        for a_expr, a_label in a_temps:
            for b_expr, b_label in b_temps:
                if a_label == "before" and b_label == "after":
                    if SequenceMatcher(None, a_expr, b_expr).ratio() > 0.6:
                        return f"تناقض زمانی: «{event_a[:50]}» قبل و بعد همزمان"
                if a_label == "always" and b_label == "never":
                    return f"تناقض زمانی: همیشه vs هرگز"
        return None

    def format_timeline(self, events: List[TemporalEvent]) -> str:
        """Format timeline as readable text."""
        if not events:
            return "📅 رویدادی ثبت نشده."
        lines = ["📅 *خط زمانی:*\n"]
        for i, event in enumerate(events, 1):
            ts_str = ""
            if event.timestamp:
                try:
                    dt = datetime.fromtimestamp(event.timestamp)
                    ts_str = f" [{dt.strftime('%Y-%m-%d %H:%M')}]"
                except (OSError, ValueError):
                    pass
            lines.append(f"  {i}. {event.content[:120]}{ts_str}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 4. ABDUCTIVE REASONER — Best explanation for observations
# ═══════════════════════════════════════════════════════════════════

class AbductiveReasoner:
    """
    Abductive reasoning: given an observation, find the best explanation.
    Uses:
    - Backward causal chaining
    - Memory similarity
    - Graph relationship traversal
    - Scoring by coverage, simplicity, and prior confidence
    """

    def __init__(self, memory: MemoryStore, causal: CausalChainEngine) -> None:
        self.memory = memory
        self.causal = causal

    def explain(self, observation: str, max_explanations: int = 5) -> List[Tuple[str, float, str]]:
        """
        Given observation, return best explanations.
        Returns: [(explanation, confidence, reasoning_path)]
        """
        explanations = []

        # Strategy 1: Backward causal chaining
        causes = self.causal.backward_chain(observation, max_depth=3)
        for cause, conf, path in causes[:5]:
            chain_str = " → ".join(path)
            explanations.append((
                f"علت احتمالی: {cause}",
                conf * 80,
                f"زنجیره علّی: {chain_str}"
            ))

        # Strategy 2: Memory-based explanation
        obs_keywords = set(PersianNLP.extract_keywords(observation))
        related_memories = self.memory.recall(observation, top_k=10)

        for mem in related_memories:
            mem_keywords = set(mem.keywords)
            overlap = len(obs_keywords & mem_keywords)
            if overlap > 0 and mem.memory_type in ("fact", "rule", "pattern"):
                coverage = overlap / max(len(obs_keywords), 1)
                conf = coverage * mem.strength * 40
                explanations.append((
                    f"بر اساس دانش: {mem.content[:150]}",
                    min(conf, 85),
                    f"منبع: {mem.topic} (اطمینان: {mem.strength:.1f})"
                ))

        # Strategy 3: Graph-based explanation
        for kw in list(obs_keywords)[:3]:
            neighbors = self.memory.get_graph_neighbors(kw)
            for node, rel, weight in neighbors:
                if rel in ("causes", "leads_to", "produces"):
                    explanations.append((
                        f"گراف دانش: {node} [{rel}] {kw}",
                        weight * 50,
                        f"رابطه گراف: {node} → {kw}"
                    ))

        # Sort by confidence and deduplicate
        explanations.sort(key=lambda x: -x[1])
        seen = set()
        unique = []
        for expl, conf, path in explanations:
            key = expl[:50]
            if key not in seen:
                seen.add(key)
                unique.append((expl, conf, path))
        return unique[:max_explanations]


# ═══════════════════════════════════════════════════════════════════
# 5. CONFLICT RESOLVER — Handle contradictory memories
# ═══════════════════════════════════════════════════════════════════

class ConflictResolver:
    """
    Detects and resolves contradictions between memories.
    Resolution strategies:
    1. Recency: newer info wins (unless older is much stronger)
    2. Authority: admin-taught > user-taught > auto-learned
    3. Confidence: higher-strength memory wins
    4. Consensus: if multiple memories agree, they win
    5. Flag: if no clear winner, flag for human review
    """

    SOURCE_AUTHORITY = {
        "admin": 10,
        "owner": 8,
        "moderator": 6,
        "user": 4,
        "auto": 2,
        "inferred": 1,
    }

    NEGATION_PAIRS = [
        ("است", "نیست"), ("هست", "نیست"), ("دارد", "ندارد"),
        ("می‌تواند", "نمی‌تواند"), ("بود", "نبود"),
        ("شد", "نشد"), ("کرد", "نکرد"),
        ("درست", "غلط"), ("صحیح", "اشتباه"),
        ("بله", "خیر"), ("آره", "نه"),
        ("همیشه", "هرگز"), ("زیاد", "کم"),
        ("خوب", "بد"), ("مثبت", "منفی"),
        ("ممکن", "غیرممکن"), ("قانونی", "غیرقانونی"),
    ]

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self.flagged: List[Tuple[str, str, str]] = []  # (mem_id_a, mem_id_b, reason)

    def detect_conflicts(self, topic: str = None) -> List[Tuple[str, str, str, float]]:
        """
        Detect contradictions in memories.
        Returns: [(mem_id_a, mem_id_b, conflict_type, severity)]
        """
        conflicts = []
        memories = list(self.memory.memories.values())
        if topic:
            memories = [m for m in memories if m.topic == topic]

        for i, mem_a in enumerate(memories):
            for mem_b in memories[i + 1:]:
                # Only compare same-topic memories
                if mem_a.topic != mem_b.topic:
                    continue

                conflict_type, severity = self._check_contradiction(mem_a, mem_b)
                if conflict_type:
                    conflicts.append((mem_a.id, mem_b.id, conflict_type, severity))

        return sorted(conflicts, key=lambda x: -x[3])

    def _check_contradiction(self, a: Any, b: Any) -> Tuple[Optional[str], float]:
        """Check if two memories contradict each other."""
        a_tokens = set(PersianNLP.tokenize(a.content))
        b_tokens = set(PersianNLP.tokenize(b.content))

        # Check direct negation
        for pos, neg in self.NEGATION_PAIRS:
            if pos in a_tokens and neg in b_tokens:
                # Check if they're talking about the same thing
                overlap = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
                if overlap > 0.3:
                    return "negation", 0.7 + overlap * 0.3
            if neg in a_tokens and pos in b_tokens:
                overlap = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
                if overlap > 0.3:
                    return "negation", 0.7 + overlap * 0.3

        # Check numeric contradiction (same topic, different numbers)
        a_nums = re.findall(r'\d+', a.content)
        b_nums = re.findall(r'\d+', b.content)
        if a_nums and b_nums and a_nums != b_nums:
            # If high token overlap, likely a numeric contradiction
            overlap = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
            if overlap > 0.5:
                return "numeric_conflict", 0.6

        # Check sentiment contradiction
        if a.sentiment != b.sentiment and a.sentiment != "neutral" and b.sentiment != "neutral":
            overlap = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
            if overlap > 0.4:
                return "sentiment_conflict", 0.4

        return None, 0.0

    def resolve(self, mem_id_a: str, mem_id_b: str) -> Tuple[str, str]:
        """
        Resolve conflict between two memories.
        Returns: (winner_id, resolution_reason)
        """
        a = self.memory.memories.get(mem_id_a)
        b = self.memory.memories.get(mem_id_b)
        if not a or not b:
            return mem_id_a, "خاطره پیدا نشد"

        score_a = 0.0
        score_b = 0.0
        reasons = []

        # 1. Authority
        auth_a = self.SOURCE_AUTHORITY.get(a.source, 3)
        auth_b = self.SOURCE_AUTHORITY.get(b.source, 3)
        if auth_a > auth_b:
            score_a += 20
            reasons.append(f"منبع معتبرتر: {a.source}")
        elif auth_b > auth_a:
            score_b += 20
            reasons.append(f"منبع معتبرتر: {b.source}")

        # 2. Strength (reinforcement)
        score_a += a.strength * 10
        score_b += b.strength * 10
        if a.strength > b.strength * 1.5:
            reasons.append(f"استحکام بیشتر: {a.strength:.1f} vs {b.strength:.1f}")
        elif b.strength > a.strength * 1.5:
            reasons.append(f"استحکام بیشتر: {b.strength:.1f} vs {a.strength:.1f}")

        # 3. Recency
        try:
            time_a = datetime.fromisoformat(a.created_at).timestamp() if a.created_at else 0
            time_b = datetime.fromisoformat(b.created_at).timestamp() if b.created_at else 0
            if time_a > time_b:
                score_a += 10
                reasons.append("جدیدتر")
            elif time_b > time_a:
                score_b += 10
                reasons.append("جدیدتر")
        except (ValueError, TypeError):
            pass

        # 4. Access count (more accessed = more trusted)
        score_a += min(a.access_count * 2, 15)
        score_b += min(b.access_count * 2, 15)

        if score_a >= score_b:
            return mem_id_a, " + ".join(reasons) if reasons else "امتیاز کلی بالاتر"
        return mem_id_b, " + ".join(reasons) if reasons else "امتیاز کلی بالاتر"

    def auto_resolve_all(self, topic: str = None) -> List[Dict[str, Any]]:
        """Auto-resolve all detected conflicts."""
        conflicts = self.detect_conflicts(topic)
        resolutions = []
        for mem_a, mem_b, conflict_type, severity in conflicts:
            winner, reason = self.resolve(mem_a, mem_b)
            loser = mem_b if winner == mem_a else mem_a
            resolutions.append({
                "winner": winner,
                "loser": loser,
                "type": conflict_type,
                "severity": severity,
                "reason": reason,
            })
            # Weaken the loser
            if loser in self.memory.memories:
                self.memory.memories[loser].strength *= 0.5
        return resolutions


# ═══════════════════════════════════════════════════════════════════
# 6. ONTOLOGY ENGINE — Hierarchical IS-A / PART-OF reasoning
# ═══════════════════════════════════════════════════════════════════

class OntologyEngine:
    """
    Hierarchical knowledge organization:
    - IS-A hierarchy (cat is_a animal)
    - PART-OF hierarchy (wheel part_of car)
    - Property inheritance (if animal has property X, cat inherits X)
    - Subsumption queries (is X a kind of Y?)
    """

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self.hierarchy: Dict[str, Set[str]] = defaultdict(set)  # child → parents
        self.parts: Dict[str, Set[str]] = defaultdict(set)      # whole → parts
        self.properties: Dict[str, Set[str]] = defaultdict(set)  # concept → properties
        self._build_from_graph()

    def _build_from_graph(self) -> Any:
        """Build ontology from knowledge graph."""
        for edge in self.memory.graph_edges:
            rel = edge.relation.lower()
            if rel in ("is_a", "type_of", "kind_of", "instance_of"):
                self.hierarchy[edge.from_node.lower()].add(edge.to_node.lower())
            elif rel in ("part_of", "component_of", "element_of"):
                self.parts[edge.to_node.lower()].add(edge.from_node.lower())
            elif rel in ("has", "has_property", "characterized_by"):
                self.properties[edge.from_node.lower()].add(edge.to_node.lower())

    def add_is_a(self, child: str, parent: str) -> None:
        """Add IS-A relation."""
        self.hierarchy[child.lower()].add(parent.lower())
        self.memory.add_graph_edge(child, parent, "is_a")

    def add_part_of(self, part: str, whole: str) -> None:
        """Add PART-OF relation."""
        self.parts[whole.lower()].add(part.lower())
        self.memory.add_graph_edge(part, whole, "part_of")

    def add_property(self, concept: str, prop: str) -> None:
        """Add property to a concept."""
        self.properties[concept.lower()].add(prop.lower())
        self.memory.add_graph_edge(concept, prop, "has_property")

    def get_ancestors(self, concept: str, max_depth: int = 10) -> List[Tuple[str, int]]:
        """Get all ancestors (parents, grandparents, ...) with depth."""
        ancestors = []
        visited = set()
        queue = deque([(concept.lower(), 0)])

        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            if depth > 0:
                ancestors.append((current, depth))

            for parent in self.hierarchy.get(current, set()):
                queue.append((parent, depth + 1))

        return ancestors

    def get_descendants(self, concept: str, max_depth: int = 10) -> List[Tuple[str, int]]:
        """Get all children, grandchildren, etc."""
        descendants = []
        visited = set()
        queue = deque([(concept.lower(), 0)])

        # Build reverse hierarchy
        children_of = defaultdict(set)
        for child, parents in self.hierarchy.items():
            for parent in parents:
                children_of[parent].add(child)

        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            if depth > 0:
                descendants.append((current, depth))

            for child in children_of.get(current, set()):
                queue.append((child, depth + 1))

        return descendants

    def is_a(self, concept: str, category: str) -> Tuple[bool, int]:
        """Check if concept IS-A category. Returns (True/False, depth)."""
        ancestors = self.get_ancestors(concept)
        for anc, depth in ancestors:
            if anc == category.lower():
                return True, depth
        return False, -1

    def get_inherited_properties(self, concept: str) -> Dict[str, int]:
        """
        Get all properties of a concept, including inherited ones.
        Returns: {property: depth_inherited_from}
        """
        all_props = {}

        # Direct properties
        for prop in self.properties.get(concept.lower(), set()):
            all_props[prop] = 0

        # Inherited from ancestors
        ancestors = self.get_ancestors(concept)
        for anc, depth in ancestors:
            for prop in self.properties.get(anc, set()):
                if prop not in all_props:
                    all_props[prop] = depth

        return all_props

    def get_parts(self, concept: str, recursive: bool = True) -> List[Tuple[str, int]]:
        """Get all parts of a concept."""
        parts = []
        visited = set()
        queue = deque([(concept.lower(), 0)])

        while queue:
            current, depth = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if depth > 0:
                parts.append((current, depth))

            if recursive or depth == 0:
                for part in self.parts.get(current, set()):
                    queue.append((part, depth + 1))

        return parts

    def find_common_ancestor(self, concept_a: str, concept_b: str) -> Optional[Tuple[str, int, int]]:
        """Find lowest common ancestor of two concepts."""
        ancestors_a = {c: d for c, d in self.get_ancestors(concept_a)}
        ancestors_a[concept_a.lower()] = 0

        ancestors_b = {c: d for c, d in self.get_ancestors(concept_b)}
        ancestors_b[concept_b.lower()] = 0

        common = set(ancestors_a.keys()) & set(ancestors_b.keys())
        if not common:
            return None

        # Find the one with smallest total depth
        best = min(common, key=lambda c: ancestors_a[c] + ancestors_b[c])
        return best, ancestors_a[best], ancestors_b[best]

    def format_tree(self, concept: str, max_depth: int = 4) -> str:
        """Format concept tree as readable text."""
        lines = [f"🌳 *{concept}*"]

        # Ancestors
        ancestors = self.get_ancestors(concept, max_depth)
        if ancestors:
            lines.append("  ⬆️ دسته‌بندی:")
            for anc, depth in ancestors:
                indent = "    " * depth
                lines.append(f"  {indent}↑ {anc}")

        # Properties
        props = self.get_inherited_properties(concept)
        if props:
            lines.append("  📋 ویژگی‌ها:")
            for prop, depth in sorted(props.items(), key=lambda x: x[1]):
                inherited = " (ارثی)" if depth > 0 else ""
                lines.append(f"    • {prop}{inherited}")

        # Descendants
        descendants = self.get_descendants(concept, max_depth)
        if descendants:
            lines.append("  ⬇️ زیرمجموعه‌ها:")
            for desc, depth in descendants:
                indent = "    " * depth
                lines.append(f"  {indent}↓ {desc}")

        # Parts
        parts = self.get_parts(concept)
        if parts:
            lines.append("  🧩 اجزا:")
            for part, depth in parts:
                indent = "    " * depth
                lines.append(f"  {indent}◦ {part}")

        return "\n".join(lines)


