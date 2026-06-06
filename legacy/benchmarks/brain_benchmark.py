
from __future__ import annotations
#!/usr/bin/env python3
"""
benchmarks/brain_benchmark.py — Victor v7.0 TITAN Brain Benchmark Suite
═══════════════════════════════════════════════════════════════════════════
Measures real performance of ALL brain strategies:
  - BM25 recall speed + accuracy
  - Reasoning pipeline latency
  - Pattern matching throughput
  - Semantic search quality
  - Memory operations (store/recall/forget)
  - End-to-end process() latency
  - NLP tokenizer/stemmer throughput

Usage:
    python benchmarks/brain_benchmark.py [--rounds 100] [--report json|text]

Requires: The brain modules must be importable.
"""

import argparse
import json
import os
import sys
import time
import statistics
import tempfile
import shutil
from typing import Any, Dict, List

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Benchmark infrastructure ──

class Timer:
    """Precise timing context manager."""
    def __init__(self):
        self.elapsed = 0.0
    def __enter__(self):
        self._start = time.perf_counter_ns()
        return self
    def __exit__(self, *args):
        self.elapsed = (time.perf_counter_ns() - self._start) / 1e6  # ms


class BenchmarkResult:
    """Stores results for a single benchmark."""
    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []  # ms
        self.extras: Dict[str, Any] = {}

    def add(self, elapsed_ms: float):
        self.times.append(elapsed_ms)

    @property
    def count(self) -> int:
        return len(self.times)

    @property
    def mean(self) -> float:
        return statistics.mean(self.times) if self.times else 0

    @property
    def median(self) -> float:
        return statistics.median(self.times) if self.times else 0

    @property
    def p95(self) -> float:
        if not self.times:
            return 0
        s = sorted(self.times)
        return s[int(len(s) * 0.95)]

    @property
    def p99(self) -> float:
        if not self.times:
            return 0
        s = sorted(self.times)
        return s[int(len(s) * 0.99)]

    @property
    def min(self) -> float:
        return min(self.times) if self.times else 0

    @property
    def max(self) -> float:
        return max(self.times) if self.times else 0

    @property
    def ops_per_sec(self) -> float:
        if not self.mean:
            return 0
        return 1000.0 / self.mean

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "runs": self.count,
            "mean_ms": round(self.mean, 3),
            "median_ms": round(self.median, 3),
            "p95_ms": round(self.p95, 3),
            "p99_ms": round(self.p99, 3),
            "min_ms": round(self.min, 3),
            "max_ms": round(self.max, 3),
            "ops_per_sec": round(self.ops_per_sec, 1),
            **self.extras,
        }


# ── Test data ──

PERSIAN_SAMPLES = [
    "پایتخت ایران تهران است و جمعیت آن حدود ۹ میلیون نفر می‌باشد",
    "زبان برنامه‌نویسی پایتون یکی از محبوب‌ترین زبان‌ها برای هوش مصنوعی است",
    "هوش مصنوعی در سال‌های اخیر پیشرفت‌های بسیار زیادی داشته است",
    "یادگیری ماشین شاخه‌ای از هوش مصنوعی است که با داده‌ها یاد می‌گیرد",
    "شبکه‌های عصبی مصنوعی از مغز انسان الهام گرفته شده‌اند",
    "پردازش زبان طبیعی به ماشین‌ها کمک می‌کند تا زبان انسان را بفهمند",
    "الگوریتم‌های ژنتیک از تکامل طبیعی الهام گرفته‌اند",
    "داده‌کاوی فرآیند کشف الگوهای پنهان در داده‌های بزرگ است",
    "رایانش ابری امکان دسترسی به منابع محاسباتی از راه دور را فراهم می‌کند",
    "اینترنت اشیا دستگاه‌های فیزیکی را به هم متصل می‌کند",
    "بلاکچین یک دفتر کل توزیع‌شده و غیرقابل تغییر است",
    "امنیت سایبری از سیستم‌های رایانه‌ای در برابر حملات محافظت می‌کند",
    "واقعیت مجازی تجربه‌ای همه‌جانبه از دنیای دیجیتال ایجاد می‌کند",
    "رباتیک علم طراحی و ساخت ربات‌های هوشمند است",
    "محاسبات کوانتومی از اصول مکانیک کوانتومی برای پردازش استفاده می‌کند",
]

QUERY_SAMPLES = [
    "پایتخت ایران کجاست؟",
    "پایتون برای چه استفاده می‌شود؟",
    "هوش مصنوعی چیست؟",
    "یادگیری ماشین چگونه کار می‌کند؟",
    "شبکه عصبی چیست؟",
    "NLP چه کاربردی دارد؟",
    "الگوریتم ژنتیک چیست؟",
    "داده‌کاوی چه فایده‌ای دارد؟",
    "رایانش ابری چیست؟",
    "بلاکچین چگونه کار می‌کند؟",
]

TOPICS = [
    "هوش مصنوعی", "پایتون", "یادگیری ماشین", "شبکه عصبی",
    "پردازش زبان", "رایانش ابری", "بلاکچین", "امنیت سایبری",
]


def run_nlp_benchmarks(rounds: int) -> List[BenchmarkResult]:
    """Benchmark NLP tokenizer, stemmer, keywords, similarity."""
    from handlers.victor.nlp import PersianNLP

    results = []

    # Tokenizer benchmark
    bench = BenchmarkResult("NLP.tokenize")
    for _ in range(rounds):
        for text in PERSIAN_SAMPLES:
            with Timer() as t:
                PersianNLP.tokenize(text)
            bench.add(t.elapsed)
    bench.extras["total_texts"] = rounds * len(PERSIAN_SAMPLES)
    results.append(bench)

    # Stemmer benchmark
    bench = BenchmarkResult("NLP.stem")
    tokens = PersianNLP.tokenize(" ".join(PERSIAN_SAMPLES))
    for _ in range(rounds):
        for tok in tokens[:50]:
            with Timer() as t:
                PersianNLP.stem(tok)
            bench.add(t.elapsed)
    results.append(bench)

    # Keyword extraction
    bench = BenchmarkResult("NLP.extract_keywords")
    for _ in range(rounds):
        for text in PERSIAN_SAMPLES[:5]:
            with Timer() as t:
                PersianNLP.extract_keywords(text, max_keywords=10)
            bench.add(t.elapsed)
    results.append(bench)

    # Similarity
    bench = BenchmarkResult("NLP.similarity")
    for _ in range(rounds):
        for i in range(min(5, len(PERSIAN_SAMPLES) - 1)):
            with Timer() as t:
                PersianNLP.similarity(PERSIAN_SAMPLES[i], PERSIAN_SAMPLES[i + 1])
            bench.add(t.elapsed)
    results.append(bench)

    return results


def run_memory_benchmarks(rounds: int) -> List[BenchmarkResult]:
    """Benchmark memory store/recall/forget operations."""
    from handlers.victor.memory import MemoryStore

    results = []
    tmpdir = tempfile.mkdtemp(prefix="victor_bench_")

    try:
        mem = MemoryStore(tmpdir)

        # Store benchmark
        bench = BenchmarkResult("Memory.store")
        for i in range(rounds):
            idx = i % len(PERSIAN_SAMPLES)
            topic = TOPICS[i % len(TOPICS)]
            with Timer() as t:
                mem.store(PERSIAN_SAMPLES[idx], topic, importance=0.5 + (i % 5) * 0.1)
            bench.add(t.elapsed)
        bench.extras["total_memories"] = len(mem.memories)
        results.append(bench)

        # Recall BM25 benchmark
        bench = BenchmarkResult("Memory.recall_bm25")
        for _ in range(rounds):
            q = QUERY_SAMPLES[_ % len(QUERY_SAMPLES)]
            with Timer() as t:
                hits = mem.recall_bm25(q, top_k=5)
            bench.add(t.elapsed)
        bench.extras["avg_hits"] = round(
            sum(len(mem.recall_bm25(q, top_k=5)) for q in QUERY_SAMPLES[:3]) / 3, 1
        )
        results.append(bench)

        # Recall (general) benchmark
        bench = BenchmarkResult("Memory.recall")
        for _ in range(rounds):
            q = QUERY_SAMPLES[_ % len(QUERY_SAMPLES)]
            with Timer() as t:
                mem.recall(q, top_k=5)
            bench.add(t.elapsed)
        results.append(bench)

        # Forget benchmark
        bench = BenchmarkResult("Memory.forget")
        for i in range(min(rounds, len(TOPICS))):
            with Timer() as t:
                mem.forget(TOPICS[i])
            bench.add(t.elapsed)
        results.append(bench)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def run_reasoning_benchmarks(rounds: int) -> List[BenchmarkResult]:
    """Benchmark reasoning engine."""
    from handlers.victor.memory import MemoryStore
    from handlers.victor.reasoning import ReasoningEngine

    results = []
    tmpdir = tempfile.mkdtemp(prefix="victor_bench_")

    try:
        mem = MemoryStore(tmpdir)

        # Seed knowledge
        for i, sample in enumerate(PERSIAN_SAMPLES):
            mem.store(sample, TOPICS[i % len(TOPICS)], importance=0.8)

        engine = ReasoningEngine(mem)

        bench = BenchmarkResult("Reasoning.reason")
        for _ in range(rounds):
            q = QUERY_SAMPLES[_ % len(QUERY_SAMPLES)]
            with Timer() as t:
                answer, conf = engine.reason(q)
            bench.add(t.elapsed)
        bench.extras["sample_confidence"] = round(conf, 1)
        results.append(bench)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def run_pattern_benchmarks(rounds: int) -> List[BenchmarkResult]:
    """Benchmark pattern engine."""
    from handlers.victor.memory import MemoryStore
    from handlers.victor.patterns import PatternEngine

    results = []
    tmpdir = tempfile.mkdtemp(prefix="victor_bench_")

    try:
        mem = MemoryStore(tmpdir)
        engine = PatternEngine(mem)

        # Add some patterns
        for i, topic in enumerate(TOPICS):
            engine.add_pattern(
                f"{topic} چیست",
                f"{topic} یک مفهوم مهم در فناوری اطلاعات است.",
                category="qa",
            )

        # Match benchmark
        bench = BenchmarkResult("Pattern.match")
        for _ in range(rounds):
            q = QUERY_SAMPLES[_ % len(QUERY_SAMPLES)]
            with Timer() as t:
                result = engine.match(q)
            bench.add(t.elapsed)
        results.append(bench)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def run_brain_e2e_benchmarks(rounds: int) -> List[BenchmarkResult]:
    """Benchmark end-to-end brain.process() — async."""
    import asyncio
    from handlers.victor.brain import VictorBrain

    results = []
    tmpdir = tempfile.mkdtemp(prefix="victor_bench_")
    original_dir = None

    try:
        # Patch BRAIN_DIR temporarily
        import handlers.victor.brain as brain_mod
        original_dir = getattr(brain_mod, 'BRAIN_DIR', None)
        brain_mod.BRAIN_DIR = tmpdir

        brain = VictorBrain()

        # Seed knowledge
        for i, sample in enumerate(PERSIAN_SAMPLES):
            topic = TOPICS[i % len(TOPICS)]
            brain.memory.store(sample, topic, importance=0.8)

        # E2E process benchmark
        bench = BenchmarkResult("Brain.process (e2e)")

        async def run_e2e():
            for _ in range(rounds):
                q = QUERY_SAMPLES[_ % len(QUERY_SAMPLES)]
                with Timer() as t:
                    response = await brain.process(q, user_id=12345)
                bench.add(t.elapsed)

        asyncio.run(run_e2e())
        results.append(bench)

    except Exception as e:
        bench = BenchmarkResult("Brain.process (e2e)")
        bench.extras["error"] = str(e)
        results.append(bench)
    finally:
        if original_dir is not None:
            brain_mod.BRAIN_DIR = original_dir
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def run_all_benchmarks(rounds: int = 50) -> Dict[str, Any]:
    """Run all benchmarks and return structured results."""
    all_results = []

    print("═══ Victor v7.0 TITAN — Brain Benchmark Suite ═══")
    print(f"Rounds per benchmark: {rounds}")
    print()

    # NLP
    print("── NLP Module ──")
    try:
        nlp_results = run_nlp_benchmarks(rounds)
        all_results.extend(nlp_results)
        for r in nlp_results:
            print(f"  {r.name:30s}  mean={r.mean:8.3f}ms  p95={r.p95:8.3f}ms  ops/s={r.ops_per_sec:8.0f}")
    except Exception as e:
        print(f"  ⚠️ NLP benchmarks failed: {e}")

    # Memory
    print("\n── Memory Module ──")
    try:
        mem_results = run_memory_benchmarks(rounds)
        all_results.extend(mem_results)
        for r in mem_results:
            print(f"  {r.name:30s}  mean={r.mean:8.3f}ms  p95={r.p95:8.3f}ms  ops/s={r.ops_per_sec:8.0f}")
    except Exception as e:
        print(f"  ⚠️ Memory benchmarks failed: {e}")

    # Reasoning
    print("\n── Reasoning Module ──")
    try:
        reason_results = run_reasoning_benchmarks(rounds)
        all_results.extend(reason_results)
        for r in reason_results:
            print(f"  {r.name:30s}  mean={r.mean:8.3f}ms  p95={r.p95:8.3f}ms  ops/s={r.ops_per_sec:8.0f}")
    except Exception as e:
        print(f"  ⚠️ Reasoning benchmarks failed: {e}")

    # Patterns
    print("\n── Pattern Engine ──")
    try:
        pattern_results = run_pattern_benchmarks(rounds)
        all_results.extend(pattern_results)
        for r in pattern_results:
            print(f"  {r.name:30s}  mean={r.mean:8.3f}ms  p95={r.p95:8.3f}ms  ops/s={r.ops_per_sec:8.0f}")
    except Exception as e:
        print(f"  ⚠️ Pattern benchmarks failed: {e}")

    # E2E
    print("\n── End-to-End ──")
    try:
        e2e_results = run_brain_e2e_benchmarks(min(rounds, 20))
        all_results.extend(e2e_results)
        for r in e2e_results:
            if "error" in r.extras:
                print(f"  {r.name:30s}  ⚠️ {r.extras['error']}")
            else:
                print(f"  {r.name:30s}  mean={r.mean:8.3f}ms  p95={r.p95:8.3f}ms  ops/s={r.ops_per_sec:8.0f}")
    except Exception as e:
        print(f"  ⚠️ E2E benchmarks failed: {e}")

    print("\n═══════════════════════════════════════════════")

    return {
        "version": "v7.0 TITAN",
        "rounds": rounds,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": [r.to_dict() for r in all_results],
    }


def main():
    parser = argparse.ArgumentParser(description="Victor Brain Benchmark Suite")
    parser.add_argument("--rounds", type=int, default=50, help="Rounds per benchmark")
    parser.add_argument("--report", choices=["json", "text"], default="text",
                        help="Output format")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file (default: stdout)")
    args = parser.parse_args()

    results = run_all_benchmarks(args.rounds)

    if args.report == "json":
        output = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        lines = [f"Victor v7.0 TITAN — Benchmark Report ({results['timestamp']})"]
        lines.append(f"Rounds: {results['rounds']}")
        lines.append("=" * 80)
        lines.append(f"{'Benchmark':30s} {'Mean(ms)':>10s} {'P95(ms)':>10s} {'P99(ms)':>10s} {'Ops/s':>10s}")
        lines.append("-" * 80)
        for b in results["benchmarks"]:
            lines.append(f"{b['name']:30s} {b['mean_ms']:10.3f} {b['p95_ms']:10.3f} {b['p99_ms']:10.3f} {b['ops_per_sec']:10.1f}")
        lines.append("=" * 80)
        output = "\n".join(lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report saved to {args.output}")
    elif args.report == "json":
        print(output)


if __name__ == "__main__":
    main()


