
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""Victor v7.0 TITAN — Advanced Capabilities (Phase 10)

Production-ready capabilities that add real value:
- NaiveBayesClassifier: text classification trained on user's data
- MarkovGenerator: simple but real text generation (Markov chains)
- FAQBuilder: auto-build FAQ from conversation history
- ConversationFlowManager: manage multi-step conversation flows
- KnowledgeExporter: export/import knowledge in multiple formats
"""

import csv
import io
import json
import logging
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .nlp import PersianNLP
from .constants import BRAIN_DIR

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. NAIVE BAYES CLASSIFIER — Text classification
# ═══════════════════════════════════════════════════════════════════

class NaiveBayesClassifier:
    """
    Multinomial Naive Bayes text classifier.
    - Trains on (text, label) pairs
    - Classifies new text into learned categories
    - Supports incremental training
    - Laplace smoothing for unseen words
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.class_counts: Counter = Counter()
        self.word_counts: Dict[str, Counter] = defaultdict(Counter)
        self.vocab: Set[str] = set()
        self.total_docs = 0
        self._load()

    def train(self, text: str, label: str) -> Any:
        """Train on a single (text, label) pair."""
        tokens = self._tokenize(text)
        self.class_counts[label] += 1
        self.total_docs += 1
        for token in tokens:
            self.word_counts[label][token] += 1
            self.vocab.add(token)

    def train_batch(self, examples: List[Tuple[str, str]]) -> Any:
        """Train on multiple examples."""
        for text, label in examples:
            self.train(text, label)
        self._save()

    def classify(self, text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Classify text. Returns: [(label, probability)]
        """
        if not self.class_counts:
            return []

        tokens = self._tokenize(text)
        scores = {}
        vocab_size = len(self.vocab)

        for label, doc_count in self.class_counts.items():
            # Prior: P(class)
            log_prob = math.log(doc_count / self.total_docs)

            # Likelihood: P(word|class) with Laplace smoothing
            total_words_in_class = sum(self.word_counts[label].values())
            for token in tokens:
                word_count = self.word_counts[label].get(token, 0)
                log_prob += math.log((word_count + 1) / (total_words_in_class + vocab_size))

            scores[label] = log_prob

        # Convert log probs to probabilities (softmax-like)
        if not scores:
            return []

        max_score = max(scores.values())
        exp_scores = {label: math.exp(s - max_score) for label, s in scores.items()}
        total = sum(exp_scores.values())
        probs = {label: exp_s / total for label, exp_s in exp_scores.items()}

        return sorted(probs.items(), key=lambda x: -x[1])[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": self.total_docs,
            "classes": dict(self.class_counts),
            "vocab_size": len(self.vocab),
        }

    def _tokenize(self, text: str) -> List[str]:
        tokens = PersianNLP.tokenize(text)
        return [PersianNLP.stem(t) for t in tokens
                if t not in PersianNLP.STOPWORDS and len(t) > 1]

    def _save(self) -> Any:
        path = self.brain_dir / "classifier.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "class_counts": dict(self.class_counts),
            "word_counts": {label: dict(counts)
                           for label, counts in self.word_counts.items()},
            "vocab": list(self.vocab),
            "total_docs": self.total_docs,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "classifier.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.class_counts = Counter(data.get("class_counts", {}))
            self.word_counts = defaultdict(Counter, {
                label: Counter(counts)
                for label, counts in data.get("word_counts", {}).items()
            })
            self.vocab = set(data.get("vocab", []))
            self.total_docs = data.get("total_docs", 0)
        except HandlerError as e:
            logger.warning("Failed to load classifier: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 2. MARKOV GENERATOR — Simple but real text generation
# ═══════════════════════════════════════════════════════════════════

class MarkovGenerator:
    """
    Markov chain text generator.
    - Trains on text Victor has seen
    - Generates contextually relevant completions
    - Order-2 Markov chains (bigram → next word)
    - NOT a language model replacement — a tool for:
      - Generating response templates
      - Expanding short answers
      - Creating example sentences
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.transitions: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
        self.starters: List[Tuple[str, str]] = []
        self.total_trained = 0
        self._load()

    def train(self, text: str) -> Any:
        """Train on text."""
        sentences = re.split(r'[.!؟?]\s*|\n+', text)
        for sentence in sentences:
            tokens = PersianNLP.tokenize(sentence)
            if len(tokens) < 3:
                continue

            self.starters.append((tokens[0], tokens[1]))
            for i in range(len(tokens) - 2):
                key = (tokens[i], tokens[i + 1])
                self.transitions[key][tokens[i + 2]] += 1

            self.total_trained += len(tokens)

    def generate(self, seed: str = None, max_words: int = 30,
                 temperature: float = 1.0) -> str:
        """
        Generate text. If seed provided, start from seed words.
        Temperature: 0.5=conservative, 1.0=normal, 1.5=creative
        """
        if not self.transitions:
            return ""

        # Find starting pair
        if seed:
            tokens = PersianNLP.tokenize(seed)
            if len(tokens) >= 2:
                current = (tokens[-2], tokens[-1])
            elif len(tokens) == 1:
                # Find a starter with this word
                matches = [(a, b) for a, b in self.starters if a == tokens[0]]
                current = matches[0] if matches else random.choice(self.starters) if self.starters else None
            else:
                current = random.choice(self.starters) if self.starters else None
        else:
            current = random.choice(self.starters) if self.starters else None

        if not current:
            return seed or ""

        result = list(current)

        for _ in range(max_words):
            options = self.transitions.get(current)
            if not options:
                break

            # Temperature-weighted selection
            words = list(options.keys())
            weights = [options[w] ** (1.0 / temperature) for w in words]
            total = sum(weights)
            if total == 0:
                break

            probs = [w / total for w in weights]
            next_word = random.choices(words, weights=probs, k=1)[0]
            result.append(next_word)
            current = (current[1], next_word)

        return " ".join(result)

    def generate_about(self, topic: str, max_words: int = 25) -> str:
        """Generate text about a specific topic."""
        # Find transitions that contain the topic keyword
        topic_starters = []
        for (w1, w2), nexts in self.transitions.items():
            if topic in w1 or topic in w2:
                topic_starters.append((w1, w2))

        if topic_starters:
            start = random.choice(topic_starters)
            result = list(start)
            current = start
            for _ in range(max_words):
                options = self.transitions.get(current)
                if not options:
                    break
                next_word = options.most_common(1)[0][0]
                result.append(next_word)
                current = (current[1], next_word)
            return " ".join(result)

        return self.generate(seed=topic, max_words=max_words)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "unique_transitions": len(self.transitions),
            "total_starters": len(self.starters),
            "total_trained_tokens": self.total_trained,
        }

    def _save(self) -> Any:
        path = self.brain_dir / "markov.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "transitions": {
                f"{k[0]}|{k[1]}": dict(v)
                for k, v in self.transitions.items()
            },
            "starters": self.starters[-1000:],
            "total_trained": self.total_trained,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "markov.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key_str, nexts in data.get("transitions", {}).items():
                parts = key_str.split("|", 1)
                if len(parts) == 2:
                    self.transitions[(parts[0], parts[1])] = Counter(nexts)
            self.starters = [tuple(s) for s in data.get("starters", []) if len(s) == 2]
            self.total_trained = data.get("total_trained", 0)
        except HandlerError as e:
            logger.warning("Failed to load Markov model: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 3. FAQ BUILDER — Auto-build FAQ from conversations
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FAQEntry:
    question: str
    answer: str
    category: str = ""
    frequency: int = 1
    last_asked: str = ""
    helpful_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "question": self.question, "answer": self.answer,
            "category": self.category, "frequency": self.frequency,
            "last_asked": self.last_asked, "helpful_count": self.helpful_count,
        }


class FAQBuilder:
    """
    Auto-builds FAQ from conversation patterns:
    - Clusters similar questions
    - Identifies best answers
    - Organizes by category
    - Exports as structured document
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.faqs: List[FAQEntry] = []
        self._load()

    def add_qa(self, question: str, answer: str, category: str = "") -> None:
        """Add a Q&A pair. Merges with existing if similar."""
        # Check if similar FAQ exists
        for faq in self.faqs:
            if self._similar(question, faq.question) > 0.7:
                faq.frequency += 1
                faq.last_asked = datetime.now(timezone.utc).isoformat()
                # Keep better answer (longer usually = more complete)
                if len(answer) > len(faq.answer):
                    faq.answer = answer
                self._save()
                return

        # New FAQ
        self.faqs.append(FAQEntry(
            question=question,
            answer=answer,
            category=category or self._auto_categorize(question),
            last_asked=datetime.now(timezone.utc).isoformat(),
        ))
        self._save()

    def search(self, query: str, top_k: int = 3) -> List[FAQEntry]:
        """Search FAQs."""
        scored = []
        for faq in self.faqs:
            sim = self._similar(query, faq.question)
            if sim > 0.3:
                scored.append((faq, sim))
        scored.sort(key=lambda x: -x[1])
        return [faq for faq, _ in scored[:top_k]]

    def export_markdown(self) -> str:
        """Export FAQ as Markdown."""
        if not self.faqs:
            return "# سوالات متداول\n\nهنوز سوالی ثبت نشده."

        by_category = defaultdict(list)
        for faq in sorted(self.faqs, key=lambda f: -f.frequency):
            by_category[faq.category or "عمومی"].append(faq)

        lines = ["# ❓ سوالات متداول ویکتور\n"]
        for category, faqs in by_category.items():
            lines.append(f"\n## 📂 {category}\n")
            for faq in faqs:
                lines.append(f"### ❔ {faq.question}")
                lines.append(f"{faq.answer}\n")
                lines.append(f"_({faq.frequency} بار پرسیده شده)_\n")

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export FAQ as JSON."""
        return json.dumps(
            [faq.to_dict() for faq in self.faqs],
            ensure_ascii=False, indent=2
        )

    def _similar(self, a: str, b: str) -> float:
        kw_a = set(PersianNLP.extract_keywords(a))
        kw_b = set(PersianNLP.extract_keywords(b))
        if not kw_a or not kw_b:
            return 0.0
        return len(kw_a & kw_b) / len(kw_a | kw_b)

    def _auto_categorize(self, question: str) -> str:
        """Auto-categorize a question."""
        q_lower = question.lower()
        if any(w in q_lower for w in ["چطور", "چگونه", "نحوه", "روش"]):
            return "آموزشی"
        if any(w in q_lower for w in ["چرا", "دلیل", "علت"]):
            return "توضیحی"
        if any(w in q_lower for w in ["کی", "زمان", "وقتی"]):
            return "زمانی"
        if any(w in q_lower for w in ["کجا", "مکان", "آدرس"]):
            return "مکانی"
        if any(w in q_lower for w in ["چقدر", "قیمت", "هزینه"]):
            return "مالی"
        return "عمومی"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_faqs": len(self.faqs),
            "categories": dict(Counter(f.category for f in self.faqs)),
            "most_asked": [(f.question[:50], f.frequency)
                          for f in sorted(self.faqs, key=lambda x: -x.frequency)[:5]],
        }

    def _save(self) -> Any:
        path = self.brain_dir / "faqs.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [faq.to_dict() for faq in self.faqs]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "faqs.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.faqs = [FAQEntry(**item) for item in data]
        except HandlerError as e:
            logger.warning("Failed to load FAQs: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 4. CONVERSATION FLOW MANAGER — Multi-step flows
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FlowStep:
    id: str
    prompt: str  # What to ask the user
    validation: str = ""  # Regex pattern to validate response
    next_step: str = ""  # ID of next step (or "" for end)
    on_invalid: str = "لطفاً دوباره تلاش کنید."


@dataclass
class FlowState:
    flow_id: str
    current_step: str
    user_id: int
    collected_data: Dict[str, str] = field(default_factory=dict)
    started_at: str = ""


class ConversationFlowManager:
    """
    Manages multi-step conversation flows:
    - Define flows with steps
    - Track user progress through flows
    - Validate responses
    - Collect structured data
    """

    def __init__(self) -> None:
        self.flows: Dict[str, List[FlowStep]] = {}
        self.active_flows: Dict[int, FlowState] = {}  # user_id → state

    def register_flow(self, flow_id: str, steps: List[FlowStep]) -> None:
        """Register a conversation flow."""
        self.flows[flow_id] = steps

    def start_flow(self, flow_id: str, user_id: int) -> Optional[str]:
        """Start a flow for a user. Returns first prompt."""
        steps = self.flows.get(flow_id)
        if not steps:
            return None

        state = FlowState(
            flow_id=flow_id,
            current_step=steps[0].id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.active_flows[user_id] = state
        return steps[0].prompt

    def process_response(self, user_id: int, response: str) -> Tuple[Optional[str], bool]:
        """
        Process user response in active flow.
        Returns: (next_prompt_or_None, is_flow_complete)
        """
        state = self.active_flows.get(user_id)
        if not state:
            return None, False

        steps = self.flows.get(state.flow_id, [])
        current = next((s for s in steps if s.id == state.current_step), None)
        if not current:
            return None, True

        # Validate response
        if current.validation and not re.match(current.validation, response):
            return current.on_invalid, False

        # Store data
        state.collected_data[current.id] = response

        # Move to next step
        if current.next_step:
            next_step = next((s for s in steps if s.id == current.next_step), None)
            if next_step:
                state.current_step = next_step.id
                return next_step.prompt, False

        # Flow complete
        del self.active_flows[user_id]
        return None, True

    def is_in_flow(self, user_id: int) -> bool:
        return user_id in self.active_flows

    def cancel_flow(self, user_id: int) -> Any:
        self.active_flows.pop(user_id, None)

    def get_collected_data(self, user_id: int) -> Dict[str, str]:
        state = self.active_flows.get(user_id)
        return state.collected_data if state else {}


# ═══════════════════════════════════════════════════════════════════
# 5. KNOWLEDGE EXPORTER — Export/Import knowledge
# ═══════════════════════════════════════════════════════════════════

class KnowledgeExporter:
    """
    Export and import Victor's knowledge in multiple formats:
    - JSON (complete, machine-readable)
    - Markdown (human-readable report)
    - CSV (spreadsheet-compatible)
    """

    def __init__(self, memory_store: Any) -> None:
        self.memory = memory_store

    def export_json(self, path: str = None) -> str:
        """Export all knowledge as JSON."""
        data = {
            "meta": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_memories": len(self.memory.memories),
                "total_edges": len(self.memory.graph_edges),
                "total_rules": len(self.memory.rules),
            },
            "memories": {
                mid: {
                    "content": m.content,
                    "type": m.memory_type,
                    "topic": m.topic,
                    "keywords": m.keywords,
                    "strength": m.strength,
                    "source": m.source,
                    "sentiment": m.sentiment,
                    "created_at": m.created_at,
                }
                for mid, m in self.memory.memories.items()
            },
            "graph": [
                {
                    "from": e.from_node,
                    "to": e.to_node,
                    "relation": e.relation,
                    "weight": e.weight,
                }
                for e in self.memory.graph_edges
            ],
            "rules": {
                rid: {
                    "condition_topic": r.condition_topic,
                    "condition_keywords": r.condition_keywords,
                    "conclusion": r.conclusion,
                    "confidence": r.confidence,
                }
                for rid, r in self.memory.rules.items()
            },
        }

        text = json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def export_markdown(self, path: str = None) -> str:
        """Export as readable Markdown report."""
        lines = [
            "# 🧠 دانش ویکتور",
            f"\n_صادر شده: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
            f"\n**آمار:** {len(self.memory.memories)} خاطره | "
            f"{len(self.memory.graph_edges)} رابطه | "
            f"{len(self.memory.rules)} قانون\n",
        ]

        # Group by topic
        by_topic = defaultdict(list)
        for mem in self.memory.memories.values():
            by_topic[mem.topic].append(mem)

        for topic in sorted(by_topic.keys()):
            mems = sorted(by_topic[topic], key=lambda m: -m.strength)
            lines.append(f"\n## 📂 {topic} ({len(mems)} خاطره)\n")
            for m in mems:
                strength_bar = "█" * min(int(m.strength), 10)
                lines.append(f"- **[{m.memory_type}]** {m.content}")
                lines.append(f"  - قدرت: {strength_bar} ({m.strength:.1f})")
                if m.keywords:
                    lines.append(f"  - کلیدواژه: {', '.join(m.keywords[:5])}")

        # Graph summary
        if self.memory.graph_edges:
            lines.append(f"\n## 🔗 گراف دانش ({len(self.memory.graph_edges)} رابطه)\n")
            by_relation = defaultdict(list)
            for e in self.memory.graph_edges:
                by_relation[e.relation].append(e)
            for rel, edges in sorted(by_relation.items()):
                lines.append(f"\n### {rel} ({len(edges)} رابطه)")
                for e in edges[:20]:
                    lines.append(f"- {e.from_node} → {e.to_node} (w={e.weight:.2f})")

        text = "\n".join(lines)
        if path:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def export_csv(self, path: str = None) -> str:
        """Export memories as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "content", "type", "topic", "keywords",
                         "strength", "source", "sentiment", "created_at"])

        for mid, m in self.memory.memories.items():
            writer.writerow([
                mid, m.content, m.memory_type, m.topic,
                "|".join(m.keywords), f"{m.strength:.2f}",
                m.source, m.sentiment, m.created_at,
            ])

        text = output.getvalue()
        if path:
            Path(path).write_text(text, encoding="utf-8-sig")  # BOM for Excel
        return text

    def import_json(self, json_text: str) -> Dict[str, int]:
        """Import knowledge from JSON. Returns counts."""
        data = json.loads(json_text)
        imported = {"memories": 0, "edges": 0, "rules": 0}

        for mid, mdata in data.get("memories", {}).items():
            if mid not in self.memory.memories:
                self.memory.store(
                    content=mdata["content"],
                    topic=mdata.get("topic", "imported"),
                    memory_type=mdata.get("type", "fact"),
                    keywords=mdata.get("keywords", []),
                    source=mdata.get("source", "import"),
                )
                imported["memories"] += 1

        for edge_data in data.get("graph", []):
            self.memory.add_graph_edge(
                edge_data["from"], edge_data["to"],
                edge_data.get("relation", "related_to"),
            )
            imported["edges"] += 1

        self.memory._save_all_sync()
        return imported


