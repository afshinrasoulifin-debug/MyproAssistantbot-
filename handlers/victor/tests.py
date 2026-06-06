
from __future__ import annotations
"""
Victor v7.0 TITAN — Unit tests (Phase 4)
Run: python -m pytest handlers/victor_pkg/tests.py -v
Or:  python handlers/victor_pkg/tests.py
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# ── Test NLP ──

from .nlp import PersianNLP, PersianTextToolkit
from .models import Memory, KnowledgeEdge, InferenceRule
from typing import Any


class TestPersianNLP(unittest.TestCase):
    """Test PersianNLP tokenization, stemming, sentiment, etc."""

    def test_normalize(self) -> Any:
        text = "سلام\u200cکه\u200cهستید"  # with ZWNJs
        result = PersianNLP.normalize(text)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_tokenize(self) -> Any:
        tokens = PersianNLP.tokenize("سلام به همه دوستان")
        self.assertIsInstance(tokens, list)
        self.assertIn("سلام", tokens)

    def test_stem(self) -> Any:
        # Should remove known suffixes
        stemmed = PersianNLP.stem("کتاب‌ها")
        self.assertIsInstance(stemmed, str)

    def test_stopwords(self) -> Any:
        self.assertIn("و", PersianNLP.STOPWORDS)
        self.assertIn("از", PersianNLP.STOPWORDS)
        self.assertIn("که", PersianNLP.STOPWORDS)

    def test_sentiment_basic(self) -> Any:
        result = PersianNLP.simple_sentiment("عالی بود خیلی خوب")
        self.assertIsInstance(result, str)
        self.assertIn(result, ["positive", "negative", "neutral"])

    def test_sentiment_negative(self) -> Any:
        result = PersianNLP.simple_sentiment("بد بود خیلی افتضاح")
        self.assertEqual(result, "negative")

    def test_extract_entities(self) -> Any:
        entities = PersianNLP.extract_entities("ایمیل من test@example.com و شماره ۰۹۱۲۱۲۳۴۵۶۷ است")
        self.assertIsInstance(entities, dict)

    def test_ngrams(self) -> Any:
        grams = PersianNLP.char_ngrams("سلام", 2)
        self.assertIsInstance(grams, list)
        self.assertTrue(len(grams) > 0)

    def test_fuzzy_match(self) -> Any:
        score = PersianNLP.fuzzy_match("سلام", "سلم")
        self.assertIsInstance(score, (int, float))
        self.assertGreater(score, 0)

    def test_enhanced_sentiment_v7(self) -> Any:
        result = PersianNLP.enhanced_sentiment_v7("خیلی خوشحالم امروز")
        self.assertIsInstance(result, dict)
        # Should have emotion keys
        self.assertIn("joy", result)

    def test_spell_check(self) -> Any:
        corrected = PersianNLP.correct_spelling("برنامه نویسی")
        self.assertIsInstance(corrected, str)

    def test_question_type(self) -> Any:
        qtype = PersianNLP.detect_question_type("چرا این کار نمی‌شود؟")
        self.assertIsInstance(qtype, str)

    def test_detect_formality(self) -> Any:
        formality = PersianNLP.detect_formality("سلام حالت چطوره داداش")
        self.assertIsInstance(formality, str)
        self.assertIn(formality, ["formal", "informal", "neutral"])

    def test_compound_words(self) -> Any:
        self.assertGreater(len(PersianNLP.COMPOUND_WORDS), 0)

    def test_relation_patterns(self) -> Any:
        self.assertGreater(len(PersianNLP.RELATION_PATTERNS), 0)


class TestPersianTextToolkit(unittest.TestCase):
    """Test PersianTextToolkit utilities."""

    def test_to_persian_digits(self) -> Any:
        result = PersianTextToolkit.to_persian_digits("123")
        self.assertEqual(result, "۱۲۳")

    def test_to_english_digits(self) -> Any:
        result = PersianTextToolkit.to_english_digits("۱۲۳")
        self.assertEqual(result, "123")

    def test_extract_numbers(self) -> Any:
        nums = PersianTextToolkit.extract_numbers("من ۱۲ کتاب و 5 دفتر دارم")
        self.assertIsInstance(nums, list)
        self.assertGreater(len(nums), 0)

    def test_text_statistics(self) -> Any:
        stats = PersianTextToolkit.text_statistics("سلام. این یک جمله تست است. جمله دیگر.")
        self.assertIsInstance(stats, dict)
        self.assertIn("words", stats)
        self.assertIn("sentences", stats)

    def test_word_frequency(self) -> Any:
        freq = PersianTextToolkit.word_frequency("سلام سلام خوبی")
        self.assertIsInstance(freq, list)
        self.assertEqual(freq[0][0], "سلام")

    def test_classify_text_type(self) -> Any:
        result = PersianTextToolkit.classify_text_type("آیا این درست است؟")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "سوال")


# ── Test Models ──

class TestModels(unittest.TestCase):
    """Test data model creation."""

    def test_memory_creation(self) -> Any:
        m = Memory(
            id="test1", content="تست", memory_type="fact",
            topic="test", keywords=["تست"], created_at="2024-01-01",
            access_count=0, last_accessed="2024-01-01",
            associations=[], sentiment="neutral", source="admin",
            confidence=1.0, decay_rate=0.005,
            emotional_context={}
        )
        self.assertEqual(m.id, "test1")
        self.assertEqual(m.content, "تست")

    def test_knowledge_edge(self) -> Any:
        e = KnowledgeEdge(source="A", target="B", relation="related_to", weight=1.0)
        self.assertEqual(e.source, "A")

    def test_inference_rule(self) -> Any:
        r = InferenceRule(
            id="r1", condition_topic="python",
            condition_keywords=["زبان"], conclusion="برنامه‌نویسی",
            confidence=0.9, uses=0
        )
        self.assertEqual(r.id, "r1")


# ── Test MemoryStore ──

class TestMemoryStore(unittest.TestCase):
    """Test MemoryStore CRUD operations."""

    def setUp(self) -> Any:
        self.tmpdir = tempfile.mkdtemp()
        from .memory import MemoryStore
        self.store = MemoryStore(Path(self.tmpdir))

    def tearDown(self) -> Any:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_store_and_recall(self) -> Any:
        self.store.store("پایتون یک زبان برنامه‌نویسی است", "python", "fact", ["پایتون", "زبان"])
        results = self.store.recall("پایتون چیست", top_k=3)
        self.assertGreater(len(results), 0)
        self.assertIn("پایتون", results[0][0].content)

    def test_store_persistence(self) -> Any:
        self.store.store("تست ذخیره‌سازی", "test", "fact", ["تست"])
        self.store._save_memories()
        # Reload
        from .memory import MemoryStore
        store2 = MemoryStore(Path(self.tmpdir))
        self.assertEqual(len(store2.memories), 1)

    def test_graph_operations(self) -> Any:
        self.store.add_graph_edge("python", "programming", "is_a")
        neighbors = self.store.get_graph_neighbors("python")
        self.assertIn("programming", [n[0] for n in neighbors])

    def test_stats(self) -> Any:
        stats = self.store.get_stats()
        self.assertIn("total_memories", stats)
        self.assertIn("graph_edges", stats)

    def test_find_contradictions(self) -> Any:
        self.store.store("زمین گرد است", "earth", "fact", ["زمین"])
        contradictions = self.store.find_contradictions("زمین صاف است", "earth")
        self.assertIsInstance(contradictions, list)


# ── Test PatternEngine ──

class TestPatternEngine(unittest.TestCase):
    def setUp(self) -> Any:
        self.tmpdir = tempfile.mkdtemp()
        from .memory import MemoryStore
        from .patterns import PatternEngine
        store = MemoryStore(Path(self.tmpdir))
        self.engine = PatternEngine(store)

    def tearDown(self) -> Any:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_match_intent(self) -> Any:
        result = self.engine.match_intent("سلام")
        self.assertIsInstance(result, (tuple, type(None)))

    def test_add_pattern(self) -> Any:
        self.engine.add_pattern("تست", "پاسخ تست")
        result = self.engine.match("تست")
        self.assertIsNotNone(result)


# ── Test InputGuard ──

class TestInputGuard(unittest.TestCase):
    def setUp(self) -> Any:
        from .security import InputGuard
        self.guard = InputGuard()

    def test_normal_input(self) -> Any:
        ok, msg = self.guard.check_input("سلام خوبی؟", user_id=123)
        self.assertTrue(ok)

    def test_injection_detection(self) -> Any:
        ok, msg = self.guard.check_input("'; DROP TABLE users; --", user_id=123)
        self.assertFalse(ok)

    def test_rate_limit(self) -> Any:
        # Send many messages quickly
        for i in range(20):
            self.guard.check_input(f"پیام {i}", user_id=999)
        ok, msg = self.guard.check_input("یه پیام دیگه", user_id=999)
        # Should be rate limited after 15/min
        self.assertFalse(ok)

    def test_file_upload_safety(self) -> Any:
        ok, msg = self.guard.check_file_upload(1024, "test.txt")
        self.assertTrue(ok)

    def test_file_upload_dangerous(self) -> Any:
        ok, msg = self.guard.check_file_upload(1024, "malware.exe")
        self.assertFalse(ok)

    def test_file_upload_too_large(self) -> Any:
        ok, msg = self.guard.check_file_upload(25 * 1024 * 1024, "big.zip")
        self.assertFalse(ok)


# ── Test FileProcessor ──

class TestFileProcessor(unittest.TestCase):
    def setUp(self) -> Any:
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self) -> Any:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_text_file(self) -> Any:
        from .files import FileProcessor
        path = os.path.join(self.tmpdir, "test.txt")
        FileProcessor.create_text_file(path, "سلام دنیا")
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "سلام دنیا")

    def test_create_csv(self) -> Any:
        from .files import FileProcessor
        path = os.path.join(self.tmpdir, "test.csv")
        FileProcessor.create_csv(path, "نام,سن\nعلی,25\nمریم,30")
        self.assertTrue(os.path.exists(path))

    def test_create_json(self) -> Any:
        from .files import FileProcessor
        path = os.path.join(self.tmpdir, "test.json")
        FileProcessor.create_json(path, '{"name": "تست"}')
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["name"], "تست")

    def test_analyze_text(self) -> Any:
        from .files import FileProcessor
        path = os.path.join(self.tmpdir, "sample.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("خط اول\nخط دوم\nخط سوم\n")
        result = FileProcessor.analyze_file(path)
        self.assertIsInstance(result, str)
        self.assertIn("خط", result)

    def test_format_size(self) -> Any:
        from .files import FileProcessor
        self.assertEqual(FileProcessor._format_size(1024), "1.0 KB")
        self.assertIn("MB", FileProcessor._format_size(1024 * 1024))


# ── Test ReasoningEngine ──

class TestReasoningEngine(unittest.TestCase):
    def setUp(self) -> Any:
        self.tmpdir = tempfile.mkdtemp()
        from .memory import MemoryStore
        from .reasoning import ReasoningEngine
        self.store = MemoryStore(Path(self.tmpdir))
        self.engine = ReasoningEngine(self.store)

    def tearDown(self) -> Any:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_reason_empty(self) -> Any:
        results = self.engine.reason("سوال بدون جواب", top_k=3)
        self.assertIsInstance(results, list)

    def test_reason_with_data(self) -> Any:
        self.store.store("پایتون زبان برنامه‌نویسی است", "python", "fact", ["پایتون"])
        results = self.engine.reason("پایتون", top_k=3)
        self.assertIsInstance(results, list)


# ── Test VictorBrain ──

class TestVictorBrain(unittest.TestCase):
    def setUp(self) -> Any:
        self.tmpdir = tempfile.mkdtemp()
        os.environ["VICTOR_BRAIN_DIR"] = self.tmpdir
        # Re-import to pick up new env var
        from .brain import VictorBrain
        self.brain = VictorBrain()

    def tearDown(self) -> Any:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_teach_and_recall(self) -> Any:
        mem, contradictions = self.brain.teach("python", "پایتون زبان برنامه‌نویسی است")
        self.assertIsNotNone(mem)
        self.assertEqual(mem.topic, "python")

    def test_status(self) -> Any:
        status = self.brain.status()
        self.assertIsInstance(status, str)
        self.assertIn("TITAN", status)

    def test_save_all(self) -> Any:
        self.brain.teach("test", "این یک تست است")
        self.brain.save_all()  # Should not raise

    def test_get_memory_dump_empty(self) -> Any:
        dump = self.brain.get_memory_dump()
        self.assertIn("خالی", dump)

    def test_teach_pattern(self) -> Any:
        self.brain.teach_pattern("سلام", "سلام! حالت چطوره؟")
        result = self.brain.patterns.match("سلام")
        self.assertIsNotNone(result)


# ── Test MemoryBackup ──

class TestMemoryBackup(unittest.TestCase):
    def setUp(self) -> Any:
        self.tmpdir = tempfile.mkdtemp()
        # Create some fake data files
        for fname in ["memories.json", "graph.json"]:
            with open(os.path.join(self.tmpdir, fname), "w") as f:
                json.dump({"test": True}, f)
        from .security import MemoryBackup
        self.backup = MemoryBackup(Path(self.tmpdir))

    def tearDown(self) -> Any:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_backup(self) -> Any:
        result = self.backup.create_backup()
        self.assertIn("✅", result)

    def test_list_backups(self) -> Any:
        self.backup.create_backup()
        listing = self.backup.list_backups()
        self.assertIsInstance(listing, str)


if __name__ == "__main__":
    unittest.main()


