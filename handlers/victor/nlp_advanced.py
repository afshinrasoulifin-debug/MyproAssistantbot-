
from __future__ import annotations
"""Victor v7.0 TITAN — Advanced NLP Pipeline (Phase 6)

Six NLP engines for deep Persian text understanding:
- DependencyParser: rule-based SOV parsing
- ClauseSplitter: complex → simple sentences
- TextRankSummarizer: extractive summarization (TextRank)
- EntailmentChecker: textual entailment
- AdvancedNER: named entity recognition (person, loc, org, date, product)
- NGramModel: n-gram language model for fluency scoring + next-word prediction
"""

import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from .nlp import PersianNLP

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. DEPENDENCY PARSER — Rule-based Persian SOV parsing
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DepToken:
    """A token with dependency info."""
    text: str
    pos: str      # Part of speech: NOUN, VERB, ADJ, ADV, PREP, CONJ, DET, PRON, NUM, PUNCT
    dep: str      # Dependency: subj, obj, pred, mod, prep, conj, det, root
    head: int     # Index of head token (-1 for root)
    index: int


class DependencyParser:
    """
    Rule-based dependency parser for Persian (SOV word order).
    Not a statistical parser — uses morphological rules and position heuristics.
    Good enough for: subject/object extraction, clause identification, relation extraction.
    """

    # Persian verb endings (present/past/imperative)
    VERB_ENDINGS = {
        "م", "ی", "د", "یم", "ید", "ند",  # present
        "ام", "ای", "ست", "ایم", "اید", "اند",  # past
        "می‌کنم", "می‌کنی", "می‌کند",
    }

    VERB_PREFIXES = {"می", "ن", "نمی", "بر", "در", "فرا", "فرو", "باز", "وا", "پیش"}

    VERB_STEMS = {
        "است", "بود", "شد", "شود", "شوند", "هست", "نیست", "باشد", "باشند",
        "کرد", "کند", "کنند", "کردند", "گفت", "گوید", "رفت", "رود",
        "آمد", "آید", "داد", "دهد", "دارد", "دارند", "داشت",
        "خواهد", "خواهند", "شده", "کرده", "گرفت", "گیرد",
        "نوشت", "نویسد", "خواند", "خوانند", "ساخت", "سازد",
    }

    PREPOSITIONS = {
        "از", "به", "با", "در", "بر", "برای", "تا", "بین",
        "میان", "نزد", "روی", "زیر", "بالای", "پایین",
        "بدون", "درباره", "درمورد", "مقابل", "کنار",
        "بعد", "قبل", "پشت", "جلوی", "داخل", "خارج",
    }

    CONJUNCTIONS = {"و", "یا", "اما", "ولی", "لیکن", "پس", "زیرا", "چون", "که", "تا", "اگر"}

    DETERMINERS = {"این", "آن", "هر", "همه", "بعضی", "چند", "یک", "هیچ", "کدام"}

    PRONOUNS = {
        "من", "تو", "او", "ما", "شما", "آنها", "ایشان",
        "خود", "خودم", "خودت", "خودش", "آن", "این",
    }

    ADJECTIVE_SUFFIXES = {"تر", "ترین", "انه", "گونه", "وار", "مند"}

    def parse(self, text: str) -> List[DepToken]:
        """Parse a sentence into dependency tokens."""
        tokens_text = PersianNLP.tokenize(text)
        if not tokens_text:
            return []

        tokens = []
        for i, t in enumerate(tokens_text):
            pos = self._pos_tag(t)
            tokens.append(DepToken(text=t, pos=pos, dep="", head=-1, index=i))

        # Find root verb (usually last verb in SOV)
        root_idx = -1
        for i in range(len(tokens) - 1, -1, -1):
            if tokens[i].pos == "VERB":
                root_idx = i
                break

        if root_idx == -1:
            # No verb found — use last non-punct token as root
            for i in range(len(tokens) - 1, -1, -1):
                if tokens[i].pos != "PUNCT":
                    root_idx = i
                    break

        if root_idx >= 0:
            tokens[root_idx].dep = "root"
            tokens[root_idx].head = -1
        else:
            if tokens:
                tokens[0].dep = "root"
            return tokens

        # Assign dependencies
        self._assign_deps(tokens, root_idx)
        return tokens

    def _pos_tag(self, token: str) -> str:
        """Simple rule-based POS tagging."""
        if not token:
            return "PUNCT"
        if token in self.PREPOSITIONS:
            return "PREP"
        if token in self.CONJUNCTIONS:
            return "CONJ"
        if token in self.DETERMINERS:
            return "DET"
        if token in self.PRONOUNS:
            return "PRON"
        if token in self.VERB_STEMS:
            return "VERB"
        if any(token.endswith(s) for s in self.VERB_ENDINGS if len(token) > len(s) + 1):
            stem = token
            for prefix in self.VERB_PREFIXES:
                if stem.startswith(prefix):
                    return "VERB"
            # Check common verb patterns
            if any(token.startswith(p) for p in ("می", "نمی")):
                return "VERB"
        if re.match(r'^[\d۰-۹]+$', token):
            return "NUM"
        if token in (".", "!", "؟", "?", "،", "؛", ":", "«", "»"):
            return "PUNCT"
        if any(token.endswith(s) for s in self.ADJECTIVE_SUFFIXES):
            return "ADJ"
        # Default: NOUN (Persian is noun-heavy)
        return "NOUN"

    def _assign_deps(self, tokens: List[DepToken], root_idx: int) -> Any:
        """Assign dependency relations using SOV heuristics."""
        # In Persian SOV: Subject ... Object ... Verb
        # Subject: first NOUN/PRON before root
        # Object: NOUN/PRON closest to root (before root)

        subj_found = False
        obj_found = False

        # Before root: subjects and objects
        for i in range(root_idx):
            t = tokens[i]
            if t.dep:
                continue

            if t.pos == "PREP":
                t.dep = "prep"
                t.head = root_idx
                # Next token is the prepositional object
                if i + 1 < root_idx and not tokens[i + 1].dep:
                    tokens[i + 1].dep = "pobj"
                    tokens[i + 1].head = i
                continue

            if t.pos == "DET":
                # Attach to next noun
                for j in range(i + 1, len(tokens)):
                    if tokens[j].pos in ("NOUN", "PRON", "ADJ"):
                        t.dep = "det"
                        t.head = j
                        break
                if not t.dep:
                    t.dep = "det"
                    t.head = root_idx
                continue

            if t.pos == "CONJ":
                t.dep = "conj"
                t.head = root_idx
                continue

            if t.pos == "ADJ":
                # Attach to preceding noun
                for j in range(i - 1, -1, -1):
                    if tokens[j].pos in ("NOUN", "PRON"):
                        t.dep = "mod"
                        t.head = j
                        break
                if not t.dep:
                    t.dep = "mod"
                    t.head = root_idx
                continue

            if t.pos in ("NOUN", "PRON"):
                if not subj_found:
                    t.dep = "subj"
                    t.head = root_idx
                    subj_found = True
                elif not obj_found:
                    t.dep = "obj"
                    t.head = root_idx
                    obj_found = True
                else:
                    t.dep = "mod"
                    t.head = root_idx
                continue

            if t.pos == "NUM":
                # Attach to next/prev noun
                for j in range(i + 1, len(tokens)):
                    if tokens[j].pos == "NOUN":
                        t.dep = "num"
                        t.head = j
                        break
                if not t.dep:
                    t.dep = "num"
                    t.head = root_idx
                continue

            if t.pos == "VERB" and i != root_idx:
                t.dep = "aux"
                t.head = root_idx
                continue

            t.dep = "dep"
            t.head = root_idx

        # After root
        for i in range(root_idx + 1, len(tokens)):
            t = tokens[i]
            if t.dep:
                continue
            if t.pos == "PUNCT":
                t.dep = "punct"
                t.head = root_idx
            elif t.pos == "CONJ":
                t.dep = "conj"
                t.head = root_idx
            elif t.pos == "VERB":
                t.dep = "aux"
                t.head = root_idx
            else:
                t.dep = "comp"
                t.head = root_idx

    def extract_svo(self, text: str) -> Dict[str, List[str]]:
        """Extract Subject-Verb-Object triples from text."""
        tokens = self.parse(text)
        result = {"subjects": [], "verbs": [], "objects": [], "modifiers": []}

        for t in tokens:
            if t.dep == "subj":
                result["subjects"].append(t.text)
            elif t.dep == "root" and t.pos == "VERB":
                result["verbs"].append(t.text)
            elif t.dep in ("obj", "pobj"):
                result["objects"].append(t.text)
            elif t.dep == "mod":
                result["modifiers"].append(t.text)

        return result

    def format_tree(self, tokens: List[DepToken]) -> str:
        """Format parse tree as readable text."""
        lines = []
        for t in tokens:
            head_text = tokens[t.head].text if 0 <= t.head < len(tokens) else "ROOT"
            lines.append(f"  {t.text:15s} [{t.pos:5s}] ──{t.dep:6s}──▶ {head_text}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 2. CLAUSE SPLITTER — Complex → Simple sentences
# ═══════════════════════════════════════════════════════════════════

class ClauseSplitter:
    """
    Splits complex Persian sentences into simple clauses.
    Handles: subordinate clauses (که), conditional (اگر), causal (چون), etc.
    """

    CLAUSE_MARKERS = [
        (r'\s+که\s+', 'relative'),
        (r'\s+اگر\s+', 'conditional'),
        (r'\s+چون\s+', 'causal'),
        (r'\s+زیرا\s+', 'causal'),
        (r'\s+اما\s+', 'adversative'),
        (r'\s+ولی\s+', 'adversative'),
        (r'\s+تا\s+', 'purpose'),
        (r'\s+وقتی\s+', 'temporal'),
        (r'\s+هنگامی\s+که\s+', 'temporal'),
        (r'\s+بنابراین\s+', 'consequential'),
        (r'\s+پس\s+', 'consequential'),
        (r'\s+یعنی\s+', 'explanatory'),
        (r'\s+مثلاً\s+', 'exemplary'),
        (r'[؛;]\s*', 'semicolon'),
    ]

    def split(self, text: str) -> List[Tuple[str, str]]:
        """
        Split text into clauses.
        Returns: [(clause_text, clause_type)]
        """
        clauses = []
        remaining = text.strip()

        while remaining:
            earliest_pos = len(remaining)
            earliest_marker = None
            earliest_type = "main"

            for pattern, clause_type in self.CLAUSE_MARKERS:
                m = re.search(pattern, remaining)
                if m and m.start() < earliest_pos and m.start() > 0:
                    earliest_pos = m.start()
                    earliest_marker = m
                    earliest_type = clause_type

            if earliest_marker and earliest_pos > 0:
                # Everything before the marker is one clause
                before = remaining[:earliest_pos].strip()
                if before:
                    clauses.append((before, "main" if not clauses else earliest_type))

                remaining = remaining[earliest_marker.end():].strip()
            else:
                if remaining.strip():
                    clauses.append((remaining.strip(), "main" if not clauses else "continuation"))
                break

        return clauses if clauses else [(text, "main")]

    def simplify(self, text: str) -> List[str]:
        """Return only the clause texts, simplified."""
        return [clause for clause, _ in self.split(text)]


# ═══════════════════════════════════════════════════════════════════
# 3. TEXTRANK SUMMARIZER — Extractive summarization
# ═══════════════════════════════════════════════════════════════════

class TextRankSummarizer:
    """
    TextRank-based extractive summarization.
    Ranks sentences by importance using a graph of sentence similarities.
    """

    def __init__(self, damping: float = 0.85, iterations: int = 30,
                 convergence: float = 0.0001) -> None:
        self.damping = damping
        self.iterations = iterations
        self.convergence = convergence

    def summarize(self, text: str, num_sentences: int = 3,
                  ratio: float = None) -> str:
        """
        Summarize text by extracting top sentences.
        Either specify num_sentences or ratio (0.0-1.0).
        """
        sentences = self._split_sentences(text)
        if len(sentences) <= num_sentences:
            return text

        if ratio:
            num_sentences = max(1, int(len(sentences) * ratio))

        # Build similarity matrix
        sim_matrix = self._build_similarity_matrix(sentences)

        # Run TextRank
        scores = self._textrank(sim_matrix, len(sentences))

        # Get top sentences (maintain original order)
        ranked = sorted(range(len(sentences)), key=lambda i: -scores[i])
        top_indices = sorted(ranked[:num_sentences])

        return " ".join(sentences[i] for i in top_indices)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Persian sentence boundaries
        parts = re.split(r'[.!؟?]\s*|\n+', text)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]

    def _sentence_tokens(self, sentence: str) -> Set[str]:
        """Get meaningful tokens from a sentence."""
        tokens = PersianNLP.tokenize(sentence)
        return {t for t in tokens if t not in PersianNLP.STOPWORDS and len(t) > 1}

    def _build_similarity_matrix(self, sentences: List[str]) -> List[List[float]]:
        """Build sentence similarity matrix using token overlap."""
        n = len(sentences)
        token_sets = [self._sentence_tokens(s) for s in sentences]
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                if not token_sets[i] or not token_sets[j]:
                    continue
                overlap = len(token_sets[i] & token_sets[j])
                norm = math.log(len(token_sets[i]) + 1) + math.log(len(token_sets[j]) + 1)
                if norm > 0:
                    sim = overlap / norm
                    matrix[i][j] = sim
                    matrix[j][i] = sim

        return matrix

    def _textrank(self, matrix: List[List[float]], n: int) -> List[float]:
        """Run TextRank algorithm."""
        scores = [1.0 / n] * n

        for _ in range(self.iterations):
            new_scores = [0.0] * n
            max_delta = 0.0

            for i in range(n):
                rank_sum = 0.0
                for j in range(n):
                    if i == j or matrix[j][i] == 0:
                        continue
                    out_sum = sum(matrix[j])
                    if out_sum > 0:
                        rank_sum += matrix[j][i] / out_sum * scores[j]

                new_scores[i] = (1 - self.damping) / n + self.damping * rank_sum
                max_delta = max(max_delta, abs(new_scores[i] - scores[i]))

            scores = new_scores
            if max_delta < self.convergence:
                break

        return scores

    def get_keywords(self, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Extract keywords using TextRank on words (not sentences)."""
        tokens = PersianNLP.tokenize(text)
        tokens = [t for t in tokens if t not in PersianNLP.STOPWORDS and len(t) > 1]
        if not tokens:
            return []

        # Build word co-occurrence graph (window=4)
        word_graph = defaultdict(lambda: defaultdict(float))
        window = 4
        for i, token in enumerate(tokens):
            for j in range(i + 1, min(i + window, len(tokens))):
                word_graph[token][tokens[j]] += 1.0
                word_graph[tokens[j]][token] += 1.0

        # Run PageRank on words
        words = list(word_graph.keys())
        if not words:
            return []

        word_idx = {w: i for i, w in enumerate(words)}
        n = len(words)
        scores = [1.0 / n] * n

        for _ in range(self.iterations):
            new_scores = [0.0] * n
            for i, word in enumerate(words):
                rank_sum = 0.0
                for neighbor, weight in word_graph[word].items():
                    j = word_idx.get(neighbor)
                    if j is not None:
                        out_sum = sum(word_graph[neighbor].values())
                        if out_sum > 0:
                            rank_sum += weight / out_sum * scores[j]
                new_scores[i] = (1 - self.damping) / n + self.damping * rank_sum
            scores = new_scores

        ranked = sorted(zip(words, scores), key=lambda x: -x[1])
        return ranked[:top_k]


# ═══════════════════════════════════════════════════════════════════
# 4. ENTAILMENT CHECKER — Does A follow from B?
# ═══════════════════════════════════════════════════════════════════

class EntailmentChecker:
    """
    Textual entailment: given premise P and hypothesis H,
    does P entail H? (entailment / contradiction / neutral)

    Uses:
    - Token overlap analysis
    - Negation detection
    - Synonym/antonym matching
    - Structural comparison
    """

    ANTONYM_PAIRS = {
        ("خوب", "بد"), ("بزرگ", "کوچک"), ("سفید", "سیاه"),
        ("گرم", "سرد"), ("بالا", "پایین"), ("راست", "چپ"),
        ("درست", "غلط"), ("زنده", "مرده"), ("قوی", "ضعیف"),
        ("سریع", "کند"), ("زیاد", "کم"), ("قدیم", "جدید"),
        ("آسان", "سخت"), ("نزدیک", "دور"), ("شروع", "پایان"),
        ("ممکن", "غیرممکن"), ("قانونی", "غیرقانونی"),
        ("مثبت", "منفی"), ("فعال", "غیرفعال"),
        ("موفق", "ناموفق"), ("سالم", "بیمار"),
    }

    NEGATION_WORDS = {"نه", "نیست", "نبود", "ندارد", "نمی", "نکرد", "هرگز", "هیچ", "بدون"}

    def check(self, premise: str, hypothesis: str) -> Tuple[str, float]:
        """
        Check entailment.
        Returns: ("entailment" | "contradiction" | "neutral", confidence)
        """
        p_tokens = set(PersianNLP.tokenize(premise))
        h_tokens = set(PersianNLP.tokenize(hypothesis))

        p_content = p_tokens - PersianNLP.STOPWORDS
        h_content = h_tokens - PersianNLP.STOPWORDS

        if not h_content:
            return "neutral", 0.3

        # 1. Token overlap
        overlap = len(p_content & h_content) / max(len(h_content), 1)

        # 2. Check negation asymmetry
        p_neg = bool(p_tokens & self.NEGATION_WORDS)
        h_neg = bool(h_tokens & self.NEGATION_WORDS)

        # 3. Check antonyms
        has_antonym = False
        for a, b in self.ANTONYM_PAIRS:
            if (a in p_tokens and b in h_tokens) or (b in p_tokens and a in h_tokens):
                has_antonym = True
                break

        # Decision logic
        if p_neg != h_neg and overlap > 0.3:
            return "contradiction", min(0.5 + overlap * 0.4, 0.9)

        if has_antonym and overlap > 0.2:
            return "contradiction", min(0.4 + overlap * 0.3, 0.85)

        if overlap > 0.6:
            return "entailment", min(overlap, 0.95)

        if overlap > 0.3:
            return "entailment", overlap * 0.8

        return "neutral", max(0.3, 1 - overlap)


# ═══════════════════════════════════════════════════════════════════
# 5. ADVANCED NER — Named Entity Recognition
# ═══════════════════════════════════════════════════════════════════

class AdvancedNER:
    """
    Named entity recognition for Persian text.
    Entities: PERSON, LOCATION, ORGANIZATION, DATE, TIME, MONEY, PRODUCT, EVENT
    Uses: pattern matching + context heuristics + gazetteers
    """

    # Person name patterns
    HONORIFICS = {
        "آقای", "خانم", "دکتر", "مهندس", "استاد", "پروفسور",
        "حاج", "حاجی", "سید", "میرزا", "آیت‌الله", "حجت‌الاسلام",
        "سرهنگ", "سرتیپ", "سروان", "ستوان",
    }

    # Location indicators
    LOCATION_INDICATORS = {
        "شهر", "استان", "کشور", "روستا", "دهستان",
        "خیابان", "میدان", "بلوار", "کوچه", "بزرگراه",
        "دریا", "رود", "کوه", "جنگل", "دشت", "جزیره",
        "شمال", "جنوب", "شرق", "غرب", "مرکز",
    }

    # Organization indicators
    ORG_INDICATORS = {
        "شرکت", "سازمان", "وزارت", "بانک", "دانشگاه",
        "بیمارستان", "موسسه", "بنیاد", "انجمن", "اتحادیه",
        "کمیته", "هیئت", "فدراسیون", "آکادمی", "مجلس",
    }

    # Date patterns
    DATE_PATTERNS = [
        r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{2,4})',
        r'(\d{1,2})\s+(فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)\s+(\d{2,4})',
        r'(۱[۳-۴][۰-۹]{2})',
        r'(\d{4})\s*میلادی',
    ]

    # Money patterns
    MONEY_PATTERNS = [
        r'(\d[\d,.]*)\s*(تومان|تومن|ریال|دلار|یورو|پوند)',
        r'(\d[\d,.]*)\s*(هزار|میلیون|میلیارد)\s*(تومان|تومن|ریال|دلار)?',
    ]

    # Time patterns
    TIME_PATTERNS = [
        r'ساعت\s+(\d{1,2})[:\s](\d{2})',
        r'(\d{1,2})\s*:\s*(\d{2})',
    ]

    def extract(self, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Extract named entities.
        Returns: [(entity_text, entity_type, start_pos, end_pos)]
        """
        entities = []

        # Extract dates
        for pattern in self.DATE_PATTERNS:
            for m in re.finditer(pattern, text):
                entities.append((m.group(0), "DATE", m.start(), m.end()))

        # Extract money
        for pattern in self.MONEY_PATTERNS:
            for m in re.finditer(pattern, text):
                entities.append((m.group(0), "MONEY", m.start(), m.end()))

        # Extract times
        for pattern in self.TIME_PATTERNS:
            for m in re.finditer(pattern, text):
                entities.append((m.group(0), "TIME", m.start(), m.end()))

        # Extract emails and URLs (from base NLP)
        base_entities = PersianNLP.extract_entities(text)
        for email in base_entities.get("emails", []):
            pos = text.find(email)
            if pos >= 0:
                entities.append((email, "EMAIL", pos, pos + len(email)))
        for phone in base_entities.get("phones", []):
            pos = text.find(phone)
            if pos >= 0:
                entities.append((phone, "PHONE", pos, pos + len(phone)))

        # Extract persons (after honorifics)
        for hon in self.HONORIFICS:
            pattern = rf'{hon}\s+(\S+(?:\s+\S+)?)'
            for m in re.finditer(pattern, text):
                name = m.group(1).strip()
                if len(name) > 1 and name not in PersianNLP.STOPWORDS:
                    entities.append((f"{hon} {name}", "PERSON", m.start(), m.end()))

        # Extract locations (after indicators)
        for indicator in self.LOCATION_INDICATORS:
            pattern = rf'({indicator})\s+(\S+(?:\s+\S+)?)'
            for m in re.finditer(pattern, text):
                loc = m.group(0).strip()
                entities.append((loc, "LOCATION", m.start(), m.end()))

        # Extract organizations (after indicators)
        for indicator in self.ORG_INDICATORS:
            pattern = rf'({indicator})\s+(\S+(?:\s+\S+){0,3})'
            for m in re.finditer(pattern, text):
                org = m.group(0).strip()
                entities.append((org, "ORGANIZATION", m.start(), m.end()))

        # Deduplicate (keep longest span for overlapping entities)
        entities.sort(key=lambda e: (e[2], -(e[3] - e[2])))
        filtered = []
        last_end = -1
        for ent in entities:
            if ent[2] >= last_end:
                filtered.append(ent)
                last_end = ent[3]

        return filtered

    def format_entities(self, entities: List[Tuple[str, str, int, int]]) -> str:
        """Format entities as readable text."""
        if not entities:
            return "موجودیتی یافت نشد."
        by_type = defaultdict(list)
        for text, etype, _, _ in entities:
            by_type[etype].append(text)

        TYPE_LABELS = {
            "PERSON": "👤 اشخاص", "LOCATION": "📍 مکان‌ها",
            "ORGANIZATION": "🏢 سازمان‌ها", "DATE": "📅 تاریخ‌ها",
            "TIME": "⏰ زمان‌ها", "MONEY": "💰 مبالغ",
            "EMAIL": "📧 ایمیل‌ها", "PHONE": "📱 تلفن‌ها",
        }
        lines = []
        for etype, items in by_type.items():
            label = TYPE_LABELS.get(etype, etype)
            lines.append(f"{label}: {', '.join(items)}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 6. N-GRAM LANGUAGE MODEL — Fluency scoring + prediction
# ═══════════════════════════════════════════════════════════════════

class NGramModel:
    """
    N-gram language model for Persian.
    - Train on accumulated text
    - Score text fluency (perplexity)
    - Predict next word
    - Generate completions
    Uses Kneser-Ney-like smoothing for unseen n-grams.
    """

    def __init__(self, n: int = 3) -> None:
        self.n = n
        self.ngram_counts: Dict[int, Counter] = {i: Counter() for i in range(1, n + 1)}
        self.total_tokens = 0
        self.vocab: Set[str] = set()

    def train(self, text: str) -> Any:
        """Train on text (incremental)."""
        tokens = PersianNLP.tokenize(text)
        tokens = ["<s>"] + tokens + ["</s>"]
        self.total_tokens += len(tokens) - 2

        for token in tokens:
            if token not in ("<s>", "</s>"):
                self.vocab.add(token)

        for order in range(1, self.n + 1):
            for i in range(len(tokens) - order + 1):
                ngram = tuple(tokens[i:i + order])
                self.ngram_counts[order][ngram] += 1

    def train_batch(self, texts: List[str]) -> Any:
        """Train on multiple texts."""
        for text in texts:
            self.train(text)

    def score(self, text: str) -> float:
        """
        Score text fluency (lower perplexity = more fluent).
        Returns perplexity score.
        """
        tokens = ["<s>"] + PersianNLP.tokenize(text) + ["</s>"]
        if len(tokens) <= 2:
            return float('inf')

        log_prob_sum = 0.0
        count = 0

        for i in range(1, len(tokens)):
            # Try highest order n-gram first, back off
            prob = self._get_probability(tokens, i)
            if prob > 0:
                log_prob_sum += math.log2(prob)
            else:
                log_prob_sum += math.log2(1e-10)  # smoothing floor
            count += 1

        if count == 0:
            return float('inf')

        # Perplexity
        avg_log_prob = log_prob_sum / count
        return 2 ** (-avg_log_prob)

    def _get_probability(self, tokens: List[str], position: int) -> float:
        """Get probability of token at position using backoff."""
        for order in range(min(self.n, position + 1), 0, -1):
            start = position - order + 1
            if start < 0:
                continue
            context = tuple(tokens[start:position])
            ngram = tuple(tokens[start:position + 1])

            ngram_count = self.ngram_counts[order].get(ngram, 0)
            if order == 1:
                # Unigram: count / total
                if self.total_tokens > 0:
                    return (ngram_count + 1) / (self.total_tokens + len(self.vocab))
            else:
                context_count = self.ngram_counts[order - 1].get(context, 0)
                if context_count > 0:
                    # Laplace smoothing
                    return (ngram_count + 1) / (context_count + len(self.vocab))

        return 1.0 / max(len(self.vocab), 1)

    def predict_next(self, text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict next word given context."""
        tokens = PersianNLP.tokenize(text)
        if not tokens:
            return []

        candidates = Counter()
        context_len = min(self.n - 1, len(tokens))
        context = tuple(tokens[-context_len:])

        # Find all n-grams starting with this context
        order = context_len + 1
        if order in self.ngram_counts:
            for ngram, count in self.ngram_counts[order].items():
                if ngram[:-1] == context:
                    word = ngram[-1]
                    if word != "</s>":
                        candidates[word] += count

        # Backoff to shorter contexts
        if not candidates and context_len > 0:
            shorter = tuple(tokens[-(context_len - 1):]) if context_len > 1 else ()
            order = len(shorter) + 1
            if order in self.ngram_counts:
                for ngram, count in self.ngram_counts[order].items():
                    if ngram[:-1] == shorter:
                        word = ngram[-1]
                        if word != "</s>":
                            candidates[word] += count

        if not candidates:
            return []

        total = sum(candidates.values())
        return [(word, count / total) for word, count in candidates.most_common(top_k)]

    def complete(self, text: str, max_words: int = 10) -> str:
        """Generate text completion."""
        result = text
        for _ in range(max_words):
            predictions = self.predict_next(result, top_k=1)
            if not predictions:
                break
            next_word = predictions[0][0]
            if next_word == "</s>":
                break
            result += " " + next_word
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get model statistics."""
        return {
            "vocab_size": len(self.vocab),
            "total_tokens": self.total_tokens,
            "ngram_counts": {f"{k}-gram": len(v) for k, v in self.ngram_counts.items()},
        }


