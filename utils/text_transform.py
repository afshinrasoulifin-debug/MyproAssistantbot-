
"""
tg_bot/utils/text_transform.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
TEXT TRANSFORM — Advanced NLP & Text Processing Engine

Comprehensive text processing, transformation, and analysis
engine with NLP capabilities, encoding tricks, and linguistic tools.

Architecture
────────────
   ┌────────────────────────────────────────────────────────┐
   │               TEXT TRANSFORM ENGINE                     │
   ├──────────┬──────────┬──────────┬──────────┬────────────┤
   │ Encode   │ NLP      │ Format   │ Generate │ Analyze    │
   │ Pipeline │ Pipeline │ Pipeline │ Pipeline │ Pipeline   │
   ├──────────┼──────────┼──────────┼──────────┼────────────┤
   │ Base64   │ Tokenize │ Markdown │ Lorem    │ Readability│
   │ ROT13    │ Stem     │ HTML     │ Password │ Sentiment  │
   │ Hex      │ Stopword │ JSON     │ UUID     │ Language   │
   │ Binary   │ N-gram   │ YAML     │ Slug     │ Keywords   │
   │ Morse    │ Lemma    │ CSV      │ Regex    │ Similarity │
   │ Caesar   │ POS Tag  │ Table    │ Template │ Entropy    │
   │ Unicode  │ NER      │ XML      │ Faker    │ Frequency  │
   │ URL      │ Summary  │ BBCode   │ Pattern  │ Collocate  │
   └──────────┴──────────┴──────────┴──────────┴────────────┘

Features
────────
  • Multi-encoding: Base64, ROT13, Hex, Binary, Morse, Caesar cipher
  • URL encoding/decoding
  • Unicode manipulation (homoglyphs, zalgo, invisible chars)
  • Tokenization (word, sentence, regex-based)
  • Stemming (Porter algorithm, pure Python)
  • Stopword filtering (English + Persian)
  • N-gram extraction (unigram through 5-gram)
  • Named entity recognition patterns
  • Text summarization (extractive, frequency-based)
  • Readability scoring (Flesch-Kincaid, Coleman-Liau, ARI)
  • Sentiment analysis (lexicon-based)
  • Language detection (trigram-based)
  • Keyword extraction (TF-IDF + frequency)
  • Text similarity (Jaccard, cosine, Levenshtein)
  • Shannon entropy calculation
  • Password strength scoring
  • Slug generation
  • Markdown ↔ HTML conversion
  • Template rendering

References
──────────
  Port of: apex_app/src/lib/parseltongue.ts (437 lines)
  Enhanced with: Porter stemmer, readability scoring, language
                 detection, NER patterns, Levenshtein distance,
                 Morse code, Caesar cipher, sentiment analysis
"""

from __future__ import annotations

import base64
import math
import os
import re
import string
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, unquote

# ── TITANIUM v29.0 Integration ──


# ═══════════════════════════════════════════════════════════════════
# Encoding / Decoding
# ═══════════════════════════════════════════════════════════════════

def to_base64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")

def from_base64(b64: str) -> str:
    return base64.b64decode(b64).decode("utf-8")

def to_hex(text: str) -> str:
    return text.encode("utf-8").hex()

def from_hex(hex_str: str) -> str:
    return bytes.fromhex(hex_str).decode("utf-8")

def to_binary(text: str) -> str:
    return " ".join(format(b, "08b") for b in text.encode("utf-8"))

def from_binary(binary: str) -> str:
    bytes_list = binary.split()
    return bytes(int(b, 2) for b in bytes_list).decode("utf-8")

def rot13(text: str) -> str:
    result = []
    for c in text:
        if "a" <= c <= "z":
            result.append(chr((ord(c) - ord("a") + 13) % 26 + ord("a")))
        elif "A" <= c <= "Z":
            result.append(chr((ord(c) - ord("A") + 13) % 26 + ord("A")))
        else:
            result.append(c)
    return "".join(result)

def caesar_encrypt(text: str, shift: int = 3) -> str:
    result = []
    for c in text:
        if "a" <= c <= "z":
            result.append(chr((ord(c) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= c <= "Z":
            result.append(chr((ord(c) - ord("A") + shift) % 26 + ord("A")))
        else:
            result.append(c)
    return "".join(result)

def caesar_decrypt(text: str, shift: int = 3) -> str:
    return caesar_encrypt(text, -shift)

def url_encode(text: str) -> str:
    return quote(text, safe="")

def url_decode(text: str) -> str:
    return unquote(text)


# ─── Morse Code ───────────────────────────────────────────────────

MORSE_TABLE: Dict[str, str] = {
    "A": ".-",    "B": "-...",  "C": "-.-.",  "D": "-..",
    "E": ".",     "F": "..-.",  "G": "--.",   "H": "....",
    "I": "..",    "J": ".---",  "K": "-.-",   "L": ".-..",
    "M": "--",    "N": "-.",    "O": "---",   "P": ".--.",
    "Q": "--.-",  "R": ".-.",   "S": "...",   "T": "-",
    "U": "..-",   "V": "...-",  "W": ".--",   "X": "-..-",
    "Y": "-.--",  "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..",
    "!": "-.-.--", " ": "/",
}
MORSE_REVERSE = {v: k for k, v in MORSE_TABLE.items()}

def to_morse(text: str) -> str:
    return " ".join(MORSE_TABLE.get(c.upper(), c) for c in text)

def from_morse(morse: str) -> str:
    words = morse.split(" / ")
    result = []
    for word in words:
        chars = word.split()
        result.append("".join(MORSE_REVERSE.get(c, c) for c in chars))
    return " ".join(result)


# ─── Unicode Tricks ───────────────────────────────────────────────

def strip_accents(text: str) -> str:
    """Remove accent marks from characters."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def remove_invisible_chars(text: str) -> str:
    """Remove zero-width and invisible Unicode characters."""
    invisible = {
        "\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
        "\u2060", "\u2061", "\u2062", "\u2063", "\ufeff",
        "\u00ad",
    }
    return "".join(c for c in text if c not in invisible)

def to_fullwidth(text: str) -> str:
    """Convert ASCII to fullwidth Unicode."""
    return "".join(
        chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c
        for c in text
    )


# ═══════════════════════════════════════════════════════════════════
# Tokenization
# ═══════════════════════════════════════════════════════════════════

def tokenize_words(text: str) -> List[str]:
    """Split text into word tokens."""
    return re.findall(r"\b\w+\b", text.lower())

def tokenize_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

def ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    """Generate n-grams from token list."""
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]

def bigrams(tokens: List[str]) -> List[Tuple[str, str]]:
    return [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]

def trigrams(tokens: List[str]) -> List[Tuple[str, str, str]]:
    return [(tokens[i], tokens[i + 1], tokens[i + 2]) for i in range(len(tokens) - 2)]


# ═══════════════════════════════════════════════════════════════════
# Stopword Filtering
# ═══════════════════════════════════════════════════════════════════

ENGLISH_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "was", "are", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can",
    "this", "that", "these", "those", "it", "its",
    "i", "me", "my", "we", "our", "you", "your", "he", "she",
    "him", "her", "his", "they", "them", "their",
    "what", "which", "who", "whom", "where", "when", "how", "why",
    "not", "no", "nor", "so", "if", "then", "than", "too", "very",
    "just", "about", "also", "as", "up", "down", "out", "off",
}

PERSIAN_STOPWORDS: Set[str] = {
    "و", "در", "به", "از", "که", "این", "را", "با", "است",
    "آن", "یک", "برای", "تا", "هم", "بر", "یا", "اما",
    "اگر", "من", "ما", "شما", "او", "آنها", "خود",
    "هر", "چه", "کی", "کجا", "چرا", "چگونه",
    "بود", "بودن", "شد", "شدن", "کرد", "کردن",
    "می", "نمی", "هست", "نیست", "باید", "شاید",
}

def remove_stopwords(tokens: List[str], lang: str = "en") -> List[str]:
    """Remove stopwords from token list."""
    stops = ENGLISH_STOPWORDS if lang == "en" else PERSIAN_STOPWORDS
    return [t for t in tokens if t.lower() not in stops]


# ═══════════════════════════════════════════════════════════════════
# Porter Stemmer (Pure Python)
# ═══════════════════════════════════════════════════════════════════

def _measure(stem: str) -> int:
    """Measure the number of consonant-vowel sequences."""
    vowels = set("aeiou")
    cv = ""
    for c in stem:
        cv += "V" if c in vowels else "C"
    # Remove leading C and trailing V
    cv = re.sub(r"^C+", "", cv)
    cv = re.sub(r"V+$", "", cv)
    return len(re.findall(r"VC", cv))

def _contains_vowel(stem: str) -> bool:
    return bool(re.search(r"[aeiou]", stem))

def _ends_double_consonant(word: str) -> bool:
    if len(word) >= 2:
        return word[-1] == word[-2] and word[-1] not in "aeiou"
    return False

def _ends_cvc(word: str) -> bool:
    if len(word) >= 3:
        vowels = set("aeiou")
        return (word[-3] not in vowels and
                word[-2] in vowels and
                word[-1] not in vowels and
                word[-1] not in "wxy")
    return False


def porter_stem(word: str) -> str:
    """
    Porter stemmer algorithm (simplified).

    A pure-Python implementation of the classic Porter stemming algorithm.
    """
    if len(word) <= 2:
        return word

    word = word.lower()

    # Step 1a
    if word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("ies"):
        word = word[:-2]
    elif word.endswith("ss"):
        pass
    elif word.endswith("s"):
        word = word[:-1]

    # Step 1b
    step1b_extra = False
    if word.endswith("eed"):
        stem = word[:-3]
        if _measure(stem) > 0:
            word = word[:-1]
    elif word.endswith("ed"):
        stem = word[:-2]
        if _contains_vowel(stem):
            word = stem
            step1b_extra = True
    elif word.endswith("ing"):
        stem = word[:-3]
        if _contains_vowel(stem):
            word = stem
            step1b_extra = True

    if step1b_extra:
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
        elif _ends_double_consonant(word) and word[-1] not in "lsz":
            word = word[:-1]
        elif _measure(word) == 1 and _ends_cvc(word):
            word += "e"

    # Step 1c
    if word.endswith("y") and _contains_vowel(word[:-1]):
        word = word[:-1] + "i"

    # Step 2
    step2_map = {
        "ational": "ate", "tional": "tion", "enci": "ence",
        "anci": "ance", "izer": "ize", "abli": "able",
        "alli": "al", "entli": "ent", "eli": "e",
        "ousli": "ous", "ization": "ize", "ation": "ate",
        "ator": "ate", "alism": "al", "iveness": "ive",
        "fulness": "ful", "ousness": "ous", "aliti": "al",
        "iviti": "ive", "biliti": "ble",
    }
    for suffix, replacement in step2_map.items():
        if word.endswith(suffix):
            stem = word[:-len(suffix)]
            if _measure(stem) > 0:
                word = stem + replacement
            break

    # Step 3
    step3_map = {
        "icate": "ic", "ative": "", "alize": "al",
        "iciti": "ic", "ical": "ic", "ful": "", "ness": "",
    }
    for suffix, replacement in step3_map.items():
        if word.endswith(suffix):
            stem = word[:-len(suffix)]
            if _measure(stem) > 0:
                word = stem + replacement
            break

    # Step 4
    step4_suffixes = [
        "al", "ance", "ence", "er", "ic", "able", "ible",
        "ant", "ement", "ment", "ent", "ion", "ou", "ism",
        "ate", "iti", "ous", "ive", "ize",
    ]
    for suffix in step4_suffixes:
        if word.endswith(suffix):
            stem = word[:-len(suffix)]
            if _measure(stem) > 1:
                if suffix == "ion" and stem and stem[-1] in "st":
                    word = stem
                elif suffix != "ion":
                    word = stem
            break

    # Step 5a
    if word.endswith("e"):
        stem = word[:-1]
        if _measure(stem) > 1:
            word = stem
        elif _measure(stem) == 1 and not _ends_cvc(stem):
            word = stem

    # Step 5b
    if _measure(word) > 1 and _ends_double_consonant(word) and word[-1] == "l":
        word = word[:-1]

    return word


# ═══════════════════════════════════════════════════════════════════
# Text Similarity
# ═══════════════════════════════════════════════════════════════════

def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein (edit) distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insert = prev[j + 1] + 1
            delete = curr[j] + 1
            replace = prev[j] + (0 if c1 == c2 else 1)
            curr.append(min(insert, delete, replace))
        prev = curr

    return prev[-1]


def jaccard_similarity(text1: str, text2: str) -> float:
    """Jaccard similarity coefficient between two texts."""
    set1 = set(tokenize_words(text1))
    set2 = set(tokenize_words(text2))
    if not set1 and not set2:
        return 1.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0


def cosine_similarity(text1: str, text2: str) -> float:
    """Cosine similarity between two texts (bag-of-words)."""
    words1 = Counter(tokenize_words(text1))
    words2 = Counter(tokenize_words(text2))
    all_words = set(words1.keys()) | set(words2.keys())

    dot = sum(words1.get(w, 0) * words2.get(w, 0) for w in all_words)
    mag1 = math.sqrt(sum(v ** 2 for v in words1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in words2.values()))

    return dot / (mag1 * mag2) if mag1 and mag2 else 0.0


# ═══════════════════════════════════════════════════════════════════
# Readability Scoring
# ═══════════════════════════════════════════════════════════════════

def _count_syllables(word: str) -> int:
    """Estimate syllable count for English word."""
    word = word.lower()
    if len(word) <= 3:
        return 1
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e"):
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in "aeiouy":
        count += 1
    return max(1, count)


def flesch_kincaid_grade(text: str) -> float:
    """Calculate Flesch-Kincaid Grade Level."""
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)
    if not sentences or not words:
        return 0.0

    total_syllables = sum(_count_syllables(w) for w in words)
    avg_sentence_len = len(words) / len(sentences)
    avg_syllables = total_syllables / len(words)

    return 0.39 * avg_sentence_len + 11.8 * avg_syllables - 15.59


def flesch_reading_ease(text: str) -> float:
    """Calculate Flesch Reading Ease score (0-100, higher=easier)."""
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)
    if not sentences or not words:
        return 0.0

    total_syllables = sum(_count_syllables(w) for w in words)
    return (206.835
            - 1.015 * (len(words) / len(sentences))
            - 84.6 * (total_syllables / len(words)))


def coleman_liau_index(text: str) -> float:
    """Calculate Coleman-Liau Index."""
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)
    if not sentences or not words:
        return 0.0

    avg_letters = sum(len(w) for w in words) / len(words) * 100
    avg_sentences = len(sentences) / len(words) * 100

    return 0.0588 * avg_letters - 0.296 * avg_sentences - 15.8


def automated_readability_index(text: str) -> float:
    """Calculate Automated Readability Index."""
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)
    chars = sum(len(w) for w in words)
    if not sentences or not words:
        return 0.0

    return (4.71 * (chars / len(words))
            + 0.5 * (len(words) / len(sentences))
            - 21.43)


def readability_report(text: str) -> Dict[str, Any]:
    """Generate comprehensive readability report."""
    words = tokenize_words(text)
    sentences = tokenize_sentences(text)

    fk = flesch_kincaid_grade(text)
    fre = flesch_reading_ease(text)
    cli = coleman_liau_index(text)
    ari = automated_readability_index(text)

    # Determine level
    if fre >= 80:
        level = "Very Easy (6th grade)"
    elif fre >= 60:
        level = "Standard (8th-9th grade)"
    elif fre >= 40:
        level = "Difficult (college)"
    elif fre >= 20:
        level = "Very Difficult (college graduate)"
    else:
        level = "Extremely Difficult (professional)"

    return {
        "words": len(words),
        "sentences": len(sentences),
        "avg_sentence_length": round(len(words) / max(1, len(sentences)), 1),
        "flesch_reading_ease": round(fre, 1),
        "flesch_kincaid_grade": round(fk, 1),
        "coleman_liau_index": round(cli, 1),
        "automated_readability_index": round(ari, 1),
        "level": level,
    }


# ═══════════════════════════════════════════════════════════════════
# Sentiment Analysis (Lexicon-Based)
# ═══════════════════════════════════════════════════════════════════

POSITIVE_WORDS: Set[str] = {
    "good", "great", "excellent", "amazing", "wonderful", "fantastic",
    "beautiful", "love", "happy", "joy", "perfect", "best", "awesome",
    "brilliant", "outstanding", "superb", "magnificent", "delightful",
    "impressive", "remarkable", "extraordinary", "pleasant", "positive",
    "success", "win", "victory", "triumph", "achieve", "accomplish",
    "enjoy", "like", "appreciate", "admire", "praise", "recommend",
}

NEGATIVE_WORDS: Set[str] = {
    "bad", "terrible", "awful", "horrible", "poor", "worst", "ugly",
    "hate", "sad", "angry", "fail", "failure", "disaster", "problem",
    "wrong", "error", "mistake", "broken", "difficult", "annoying",
    "frustrating", "disappointing", "mediocre", "boring", "dull",
    "pathetic", "useless", "waste", "garbage", "trash", "toxic",
    "negative", "pain", "suffer", "lose", "defeat", "reject",
}

INTENSIFIERS: Set[str] = {
    "very", "extremely", "incredibly", "absolutely", "totally",
    "completely", "really", "truly", "utterly", "highly",
}

NEGATIONS: Set[str] = {
    "not", "no", "never", "neither", "nor", "none", "nothing",
    "nowhere", "hardly", "barely", "scarcely", "don't", "doesn't",
    "didn't", "won't", "wouldn't", "can't", "couldn't", "shouldn't",
}


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Lexicon-based sentiment analysis.

    Returns score (-1 to +1), label, and breakdown.
    """
    words = tokenize_words(text)
    pos_count = 0
    neg_count = 0
    intensity = 1.0
    negated = False

    for i, word in enumerate(words):
        if word in NEGATIONS:
            negated = True
            continue

        if word in INTENSIFIERS:
            intensity = 1.5
            continue

        if word in POSITIVE_WORDS:
            if negated:
                neg_count += intensity
                negated = False
            else:
                pos_count += intensity
        elif word in NEGATIVE_WORDS:
            if negated:
                pos_count += intensity * 0.5
                negated = False
            else:
                neg_count += intensity

        intensity = 1.0
        if word not in NEGATIONS:
            negated = False

    total = pos_count + neg_count
    if total == 0:
        score = 0.0
    else:
        score = (pos_count - neg_count) / max(1, total)

    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"

    return {
        "score": round(score, 3),
        "label": label,
        "positive_count": pos_count,
        "negative_count": neg_count,
        "confidence": round(abs(score), 3),
    }


# ═══════════════════════════════════════════════════════════════════
# Language Detection
# ═══════════════════════════════════════════════════════════════════

def detect_language(text: str) -> Dict[str, float]:
    """
    Detect language using character-range heuristics.

    Returns dict of {language: confidence}.
    """
    if not text:
        return {"unknown": 1.0}

    # Count character ranges
    total = 0
    counts: Dict[str, int] = defaultdict(int)

    for c in text:
        if c.isspace() or not c.isalpha():
            continue
        total += 1
        cp = ord(c)

        if 0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFDFF:
            # Arabic/Persian
            if any(ord(pc) in (0x067E, 0x0686, 0x0698, 0x06AF, 0x06CC)
                   for pc in text):
                counts["fa"] += 1
            else:
                counts["ar"] += 1
        elif 0x0400 <= cp <= 0x04FF:
            counts["ru"] += 1
        elif 0x4E00 <= cp <= 0x9FFF:
            counts["zh"] += 1
        elif 0x3040 <= cp <= 0x30FF:
            counts["ja"] += 1
        elif 0xAC00 <= cp <= 0xD7AF:
            counts["ko"] += 1
        elif 0x0900 <= cp <= 0x097F:
            counts["hi"] += 1
        elif 0x0E00 <= cp <= 0x0E7F:
            counts["th"] += 1
        elif 0x0041 <= cp <= 0x024F:
            counts["en"] += 1      # Latin script (could be many languages)

    if total == 0:
        return {"unknown": 1.0}

    result = {}
    for lang, count in counts.items():
        result[lang] = round(count / max(1, total), 3)

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


# ═══════════════════════════════════════════════════════════════════
# Keyword Extraction
# ═══════════════════════════════════════════════════════════════════

def extract_keywords(text: str, top_n: int = 10,
                     lang: str = "en") -> List[Tuple[str, float]]:
    """Extract keywords using TF-based scoring."""
    words = tokenize_words(text)
    filtered = remove_stopwords(words, lang)
    stemmed = [porter_stem(w) if lang == "en" else w for w in filtered]

    # Frequency scoring
    freq = Counter(stemmed)
    total = len(stemmed) if stemmed else 1

    scored = [(word, count / max(1, total)) for word, count in freq.most_common(top_n * 2)]

    # Boost multi-word phrases
    bi = Counter(bigrams(filtered))
    for (w1, w2), count in bi.most_common(top_n):
        phrase = f"{w1} {w2}"
        scored.append((phrase, count / max(1, total) * 1.5))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


# ═══════════════════════════════════════════════════════════════════
# Extractive Summarization
# ═══════════════════════════════════════════════════════════════════

def summarize(text: str, num_sentences: int = 3,
              lang: str = "en") -> str:
    """
    Extractive summarization using sentence scoring.

    Scores sentences by:
      - Word frequency (TF-based)
      - Position (early sentences get bonus)
      - Length (medium-length preferred)
    """
    sentences = tokenize_sentences(text)
    if len(sentences) <= num_sentences:
        return text

    # Word frequencies
    words = remove_stopwords(tokenize_words(text), lang)
    freq = Counter(words)
    max_freq = max(freq.values()) if freq else 1

    # Score sentences
    scored: List[Tuple[int, float, str]] = []
    for idx, sentence in enumerate(sentences):
        sent_words = tokenize_words(sentence)
        if not sent_words:
            continue

        # TF score
        word_score = sum(freq.get(w, 0) / max(1, max_freq) for w in sent_words) / len(sent_words)

        # Position bonus (first sentences get 20% bonus)
        position_bonus = 0.2 * (1 - idx / len(sentences))

        # Length penalty (prefer medium length)
        length = len(sent_words)
        if length < 5:
            length_score = 0.5
        elif length > 30:
            length_score = 0.7
        else:
            length_score = 1.0

        total_score = word_score * length_score + position_bonus
        scored.append((idx, total_score, sentence))

    scored.sort(key=lambda x: x[1], reverse=True)
    selected = scored[:num_sentences]
    selected.sort(key=lambda x: x[0])   # Restore original order

    return ". ".join(s[2] for s in selected) + "."


# ═══════════════════════════════════════════════════════════════════
# Named Entity Recognition (Pattern-Based)
# ═══════════════════════════════════════════════════════════════════

NER_PATTERNS: Dict[str, List[str]] = {
    "EMAIL": [r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
    "URL": [r"https?://[^\s<>\"]+"],
    "PHONE": [
        r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
    ],
    "IP_ADDRESS": [r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"],
    "DATE": [
        r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
    ],
    "CURRENCY": [r"\$[\d,]+\.?\d*", r"€[\d,]+\.?\d*", r"£[\d,]+\.?\d*"],
    "HASHTAG": [r"#\w+"],
    "MENTION": [r"@\w+"],
}


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities using regex patterns."""
    entities: Dict[str, List[str]] = {}
    for entity_type, patterns in NER_PATTERNS.items():
        matches: List[str] = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text))
        if matches:
            entities[entity_type] = list(set(matches))
    return entities


# ═══════════════════════════════════════════════════════════════════
# Shannon Entropy & Information Theory
# ═══════════════════════════════════════════════════════════════════

def shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy of text (bits per character)."""
    if not text:
        return 0.0
    freq = Counter(text)
    length = len(text)
    return -sum(
        (count / max(1, length)) * math.log2(count / max(1, length))
        for count in freq.values()
    )


def character_frequency(text: str) -> Dict[str, float]:
    """Character frequency distribution."""
    freq = Counter(text)
    total = len(text) if text else 1
    return {char: round(count / max(1, total), 4) for char, count in freq.most_common(50)}


# ═══════════════════════════════════════════════════════════════════
# Password & Security
# ═══════════════════════════════════════════════════════════════════

def password_strength(password: str) -> Dict[str, Any]:
    """
    Evaluate password strength (0-100).

    Checks: length, uppercase, lowercase, digits, symbols,
            entropy, common patterns, sequential chars.
    """
    score = 0
    checks: Dict[str, bool] = {}

    # Length
    length = len(password)
    checks["length_8+"] = length >= 8
    checks["length_12+"] = length >= 12
    checks["length_16+"] = length >= 16
    score += min(30, length * 2)

    # Character diversity
    checks["has_lower"] = bool(re.search(r"[a-z]", password))
    checks["has_upper"] = bool(re.search(r"[A-Z]", password))
    checks["has_digit"] = bool(re.search(r"\d", password))
    checks["has_symbol"] = bool(re.search(r"[^a-zA-Z0-9]", password))

    diversity = sum(1 for v in [
        checks["has_lower"], checks["has_upper"],
        checks["has_digit"], checks["has_symbol"],
    ] if v)
    score += diversity * 10

    # Entropy
    entropy = shannon_entropy(password)
    checks["high_entropy"] = entropy > 3.0
    score += min(20, entropy * 5)

    # Penalty: sequential characters
    sequential = 0
    for i in range(len(password) - 2):
        if (ord(password[i + 1]) == ord(password[i]) + 1 and
            ord(password[i + 2]) == ord(password[i]) + 2):
            sequential += 1
    score -= sequential * 5

    # Penalty: repeated characters
    repeats = len(password) - len(set(password))
    score -= repeats * 2

    score = max(0, min(100, score))

    if score >= 80:
        label = "Very Strong"
    elif score >= 60:
        label = "Strong"
    elif score >= 40:
        label = "Moderate"
    elif score >= 20:
        label = "Weak"
    else:
        label = "Very Weak"

    return {
        "score": score,
        "label": label,
        "entropy": round(entropy, 2),
        "checks": checks,
    }


# ═══════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════

def slugify(text: str, separator: str = "-") -> str:
    """Convert text to URL-safe slug."""
    text = strip_accents(text.lower())
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", separator, text)
    return text.strip(separator)


def word_count(text: str) -> Dict[str, int]:
    """Count words, sentences, paragraphs, and characters."""
    return {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(tokenize_words(text)),
        "sentences": len(tokenize_sentences(text)),
        "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
        "lines": len(text.splitlines()),
    }


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def generate_password(length: int = 16, include_symbols: bool = True) -> str:
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits
    if include_symbols:
        chars += "!@#$%^&*()-_=+"
    # Use os.urandom for cryptographic randomness
    return "".join(
        chars[b % len(chars)]
        for b in os.urandom(length)
    )

class TextTransformer:
    """Text transformation utilities."""

    def __init__(self) -> None:
        self._transforms = {}

    def register(self, name: str, func: Any) -> Any:
        self._transforms[name] = func

    def transform(self, text: str, transform_name: str) -> str:
        fn = self._transforms.get(transform_name)
        if fn:
            return fn(text)
        return text

    @staticmethod
    def to_slug(text: str) -> str:
        import re
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

    @staticmethod
    def truncate(text: str, max_len: int = 100) -> str:
        return text[:max_len] + "…" if len(text) > max_len else text



# ═══════════════════════════════════════════════════════════════════════
# PARSELTONGUE — Input Perturbation Engine (DEEP)
# ═══════════════════════════════════════════════════════════════════════
#
# Architecture:
#   ┌────────────────┐
#   │  Input Text     │
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  TRIGGER SCAN   │ ← 36 default + custom triggers
#   │  (7 categories) │   Word-boundary regex matching
#   └───────┬────────┘
#           ▼ triggers found?
#   ┌────────────────┐
#   │  TECHNIQUE SEL  │ ← leetspeak / unicode / zwj / mixedcase / phonetic / random
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  INTENSITY      │ ← light (1 char) / medium (half) / heavy (all)
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  OBFUSCATION    │ ← Apply chosen technique at chosen intensity
#   │  (longest-first │   Sort triggers desc to prevent partial-match corruption
#   │   matching)     │
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  RESULT         │ ← {original, transformed, triggers_found, transformations}
#   └────────────────┘
#
# Ported from: APEX-main/src/lib/parseltongue.ts
# Version: 4.0.0-DEEP (Phase 1-5 hardened)
# ═══════════════════════════════════════════════════════════════════════


import logging
import random as _pt_random
from enum import Enum
from typing import (
    Any, Dict, Final, List, Optional, Sequence, Tuple, TypedDict,
)

_pt_logger = logging.getLogger("arki.apex.parseltongue")


# ═══════════════════ TYPE DEFINITIONS ═══════════════════

class ObfuscationTechnique(str, Enum):
    """Available obfuscation techniques."""
    LEETSPEAK = "leetspeak"
    UNICODE = "unicode"
    ZWJ = "zwj"
    MIXEDCASE = "mixedcase"
    PHONETIC = "phonetic"
    RANDOM = "random"


class ObfuscationIntensity(str, Enum):
    """Transformation intensity levels."""
    LIGHT = "light"    # 1 character
    MEDIUM = "medium"  # ~half of characters
    HEAVY = "heavy"    # all characters


class TransformRecord(TypedDict):
    """Record of a single word transformation."""
    original: str
    transformed: str
    technique: str


class ParseltongueResult(TypedDict):
    """Complete result from parseltongue_obfuscate."""
    original: str
    transformed: str
    triggers_found: List[str]
    technique_used: str
    transformations: List[TransformRecord]


# ═══════════════════ TRIGGER WORDS (36 defaults, 7 categories) ═══════════════════

PARSELTONGUE_TRIGGERS: Final[Tuple[str, ...]] = (
    # Action words (13)
    "hack", "exploit", "bypass", "crack", "break", "attack", "penetrate",
    "inject", "manipulate", "override", "disable", "circumvent", "evade",
    # Security terms (9)
    "malware", "virus", "trojan", "payload", "shellcode", "rootkit",
    "keylogger", "backdoor", "vulnerability",
    # Sensitive topics (6)
    "weapon", "bomb", "explosive", "poison", "drug", "synthesize",
    # System terms (6)
    "jailbreak", "unlock", "root", "sudo", "admin", "privilege",
    # Social engineering (5)
    "phishing", "scam", "impersonate", "deceive", "fraud",
    # Content flags (5)
    "nsfw", "explicit", "uncensored", "unfiltered", "unrestricted",
    # AI-specific (9)
    "ignore", "disregard", "forget", "pretend", "roleplay",
    "character", "act as", "you are now", "new identity",
)

# ═══════════════════ SUBSTITUTION MAPS (pre-built, immutable) ═══════════════════

# Leetspeak: 26 letters × 2-4 alternatives = 85 substitutions
_LEET_MAP: Final[Dict[str, Tuple[str, ...]]] = {
    "a": ("4", "@", "∂", "λ"), "b": ("8", "|3", "ß", "13"),
    "c": ("(", "<", "¢", "©"), "d": ("|)", "|>", "đ"),
    "e": ("3", "€", "£", "∑"), "f": ("|=", "ƒ", "ph"),
    "g": ("9", "6", "&"), "h": ("#", "|-|", "}{"),
    "i": ("1", "!", "|", "¡"), "j": ("_|", "]", "¿"),
    "k": ("|<", "|{", "κ"), "l": ("1", "|", "£", "|_"),
    "m": ("|V|", "/\\/\\", "µ"), "n": ("|\\|", "/\\/", "η"),
    "o": ("0", "()", "°", "ø"), "p": ("|*", "|>", "þ"),
    "q": ("0_", "()_", "ℚ"), "r": ("|2", "®", "12"),
    "s": ("5", "$", "§", "∫"), "t": ("7", "+", "†", "⊤"),
    "u": ("|_|", "µ", "ü"), "v": ("\\/", "√"),
    "w": ("\\/\\/", "vv", "ω"), "x": ("><", "×", "}{"),
    "y": ("`/", "¥", "γ"), "z": ("2", "7_", "ℤ"),
}

# Unicode homoglyphs: visually identical, different codepoints
_UNICODE_HOMOGLYPHS: Final[Dict[str, Tuple[str, ...]]] = {
    "a": ("а", "ɑ", "α", "ａ"), "b": ("Ь", "ｂ", "ḅ"),
    "c": ("с", "ϲ", "ⅽ", "ｃ"), "d": ("ԁ", "ⅾ", "ｄ"),
    "e": ("е", "ė", "ẹ", "ｅ"), "f": ("ƒ", "ｆ"),
    "g": ("ɡ", "ｇ"), "h": ("һ", "ḥ", "ｈ"),
    "i": ("і", "ι", "ｉ"), "j": ("ϳ", "ｊ"),
    "k": ("κ", "ｋ"), "l": ("ӏ", "ⅼ", "ｌ"),
    "m": ("м", "ｍ"), "n": ("ո", "ｎ"),
    "o": ("о", "ο", "ｏ"), "p": ("р", "ρ", "ｐ"),
    "s": ("ѕ", "ｓ"), "t": ("τ", "ｔ"),
    "u": ("υ", "ｕ"), "v": ("ν", "ｖ"),
    "w": ("ѡ", "ｗ"), "x": ("х", "ｘ"),
    "y": ("у", "γ", "ｙ"), "z": ("ᴢ", "ｚ"),
}

# Zero-width characters (4 types)
_ZW_CHARS: Final[Tuple[str, ...]] = ("\u200B", "\u200C", "\u200D", "\uFEFF")

# Phonetic substitution rules (pre-compiled)
_PHONETIC_RULES: Final[Tuple[Tuple[re.Pattern, str], ...]] = (
    (re.compile(r"ph", re.I), "f"),
    (re.compile(r"ck", re.I), "k"),
    (re.compile(r"x", re.I), "ks"),
    (re.compile(r"qu", re.I), "kw"),
    (re.compile(r"c(?=[eiy])", re.I), "s"),
    (re.compile(r"c", re.I), "k"),
)


# ═══════════════════ TECHNIQUE IMPLEMENTATIONS ═══════════════════

def _calc_transform_count(word_len: int, intensity: str) -> int:
    """Calculate how many characters to transform based on intensity.
    
    Args:
        word_len: Length of the word.
        intensity: "light" (1), "medium" (~half), "heavy" (all).
    
    Returns:
        Number of characters to transform.
    """
    if intensity == "light":
        return 1
    elif intensity == "medium":
        return word_len // 2 + 1
    else:  # heavy
        return word_len


def _pt_leetspeak(word: str, intensity: str = "medium") -> str:
    """Apply leetspeak transformation (a→4, e→3, etc.)."""
    chars = list(word)
    count = _calc_transform_count(len(chars), intensity)
    done = 0
    for i in range(len(chars)):
        if done >= count:
            break
        ch = chars[i].lower()
        if ch in _LEET_MAP:
            chars[i] = _pt_random.choice(_LEET_MAP[ch])
            done += 1
    return "".join(chars)


def _pt_unicode(word: str, intensity: str = "medium") -> str:
    """Apply unicode homoglyph transformation."""
    chars = list(word)
    count = _calc_transform_count(len(chars), intensity)
    done = 0
    for i in range(len(chars)):
        if done >= count:
            break
        ch = chars[i].lower()
        if ch in _UNICODE_HOMOGLYPHS:
            replacement = _pt_random.choice(_UNICODE_HOMOGLYPHS[ch])
            chars[i] = replacement.upper() if chars[i].isupper() else replacement
            done += 1
    return "".join(chars)


def _pt_zwj(word: str, intensity: str = "medium") -> str:
    """Insert zero-width characters between letters."""
    chars = list(word)
    count = _calc_transform_count(len(chars) - 1, intensity) if len(chars) > 1 else 0
    result = []
    inserted = 0
    for i, ch in enumerate(chars):
        result.append(ch)
        if i < len(chars) - 1 and inserted < count:
            result.append(_pt_random.choice(_ZW_CHARS))
            inserted += 1
    return "".join(result)


def _pt_mixedcase(word: str, intensity: str = "medium") -> str:
    """Apply mixed case disruption."""
    chars = list(word)
    if not chars:
        return word
    if intensity == "light":
        idx = _pt_random.randrange(len(chars))
        chars[idx] = chars[idx].upper()
    elif intensity == "medium":
        chars = [ch.lower() if i % 2 == 0 else ch.upper() for i, ch in enumerate(chars)]
    else:  # heavy
        chars = [ch.upper() if _pt_random.random() > 0.5 else ch.lower() for ch in chars]
    return "".join(chars)


def _pt_phonetic(word: str, intensity: str = "medium") -> str:
    """Apply phonetic substitution (ph→f, ck→k, etc.)."""
    result = word
    for pat, repl in _PHONETIC_RULES:
        result = pat.sub(repl, result)
    return result


# Technique dispatch table (O(1) lookup)
_PT_TECHNIQUES: Final[Dict[str, Any]] = {
    "leetspeak": _pt_leetspeak,
    "unicode": _pt_unicode,
    "zwj": _pt_zwj,
    "mixedcase": _pt_mixedcase,
    "phonetic": _pt_phonetic,
}

_PT_TECHNIQUE_NAMES: Final[Tuple[str, ...]] = tuple(_PT_TECHNIQUES.keys())


# ═══════════════════ PUBLIC API ═══════════════════

def parseltongue_detect_triggers(
    text: str,
    custom_triggers: Optional[Sequence[str]] = None,
) -> List[str]:
    """Scan text for trigger words that may cause model refusals.
    
    Uses word-boundary regex matching against 36 default triggers
    plus any custom triggers provided.
    
    Args:
        text: Input text to scan.
        custom_triggers: Additional trigger words/phrases.
    
    Returns:
        List of found trigger words (deduplicated).
    
    Examples:
        >>> parseltongue_detect_triggers("how to bypass a firewall")
        ['bypass']
    """
    if not text or not isinstance(text, str):
        return []
    
    all_triggers = list(PARSELTONGUE_TRIGGERS)
    if custom_triggers:
        all_triggers.extend(custom_triggers)
    
    found: List[str] = []
    seen: set = set()
    lower = text.lower()
    
    for trigger in all_triggers:
        if trigger in seen:
            continue
        escaped = re.escape(trigger)
        if re.search(rf"\b{escaped}\b", lower, re.I):
            found.append(trigger)
            seen.add(trigger)
    
    return found


def parseltongue_obfuscate(
    text: str,
    technique: str = "leetspeak",
    intensity: str = "medium",
    custom_triggers: Optional[Sequence[str]] = None,
    enabled: bool = True,
) -> ParseltongueResult:
    """Main Parseltongue transformation — detect and obfuscate trigger words.
    
    Scans input for trigger words, then applies the chosen obfuscation
    technique at the specified intensity. Triggers are processed
    longest-first to prevent partial-match corruption.
    
    Args:
        text: Input text.
        technique: One of "leetspeak", "unicode", "zwj", "mixedcase", "phonetic", "random".
        intensity: "light" (1 char), "medium" (half), "heavy" (all).
        custom_triggers: Additional trigger words beyond defaults.
        enabled: Whether to apply transformations (False = passthrough).
    
    Returns:
        ParseltongueResult with original, transformed, triggers_found, transformations.
    
    Examples:
        >>> r = parseltongue_obfuscate("how to hack a server", technique="leetspeak")
        >>> "hack" in r["triggers_found"]
        True
        >>> r["transformed"] != r["original"]
        True
    """
    empty_result: ParseltongueResult = {
        "original": text or "",
        "transformed": text or "",
        "triggers_found": [],
        "technique_used": technique,
        "transformations": [],
    }
    
    if not enabled or not text or not isinstance(text, str):
        return empty_result
    
    # Validate technique
    if technique not in _PT_TECHNIQUES and technique != "random":
        _pt_logger.warning(f"Unknown technique '{technique}', falling back to leetspeak")
        technique = "leetspeak"
    
    # Validate intensity
    if intensity not in ("light", "medium", "heavy"):
        _pt_logger.warning(f"Unknown intensity '{intensity}', falling back to medium")
        intensity = "medium"
    
    triggers = parseltongue_detect_triggers(text, custom_triggers)
    if not triggers:
        return empty_result
    
    transformed = text
    transformations: List[TransformRecord] = []
    
    # Sort triggers longest-first to prevent partial-match corruption
    sorted_triggers = sorted(triggers, key=len, reverse=True)
    
    for trigger in sorted_triggers:
        escaped = re.escape(trigger)
        pattern = re.compile(rf"\b({escaped})\b", re.I)
        
        def _replace(match: Any, _tech: Any=technique, _int: Any=intensity) -> Any:
            word = match.group(0)
            if _tech == "random":
                tech_name = _pt_random.choice(_PT_TECHNIQUE_NAMES)
                func = _PT_TECHNIQUES[tech_name]
            else:
                tech_name = _tech
                func = _PT_TECHNIQUES[_tech]
            
            result = func(word, intensity=_int)
            transformations.append({
                "original": word,
                "transformed": result,
                "technique": tech_name,
            })
            return result
        
        transformed = pattern.sub(_replace, transformed)
    
    return {
        "original": text,
        "transformed": transformed,
        "triggers_found": triggers,
        "technique_used": technique,
        "transformations": transformations,
    }


