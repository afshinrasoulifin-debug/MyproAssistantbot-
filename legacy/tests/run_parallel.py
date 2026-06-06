
from __future__ import annotations
"""
tests/run_parallel.py — Parallel Async Test Runner
═══════════════════════════════════════════════════
Runs all test suites concurrently for maximum speed.
"""

import asyncio
import os
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TESTS_DIR)

# All test files to run
TEST_FILES = [
    "test_runtime_real.py",
    "test_phase13_real_only.py",
    "test_api_builder_infra.py",
    "test_mega_stress.py",
    "test_104_models_real.py",
    "test_phase14_no_stubs.py",
    "test_phase15_optimization.py",
]


async def run_test(test_file: str) -> dict:
    """Run a single test file and capture results."""
    t0 = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, os.path.join(TESTS_DIR, test_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=BASE_DIR,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() + stderr.decode()

        # Parse results
        passed = 0
        total = 0
        for line in output.split("\n"):
            if "passed" in line and "/" in line:
                import re
                m = re.search(r"(\d+)/(\d+)\s+passed", line)
                if m:
                    passed = int(m.group(1))
                    total = int(m.group(2))
            elif "ALL TESTS PASSED" in line:
                passed = total = -1  # Marker for "all passed"

        return {
            "file": test_file,
            "passed": passed, "total": total,
            "returncode": proc.returncode,
            "duration_ms": int((time.time() - t0) * 1000),
            "output": output[-500:],  # Last 500 chars
        }
    except Exception as e:
        return {
            "file": test_file, "passed": 0, "total": 0,
            "returncode": -1, "duration_ms": int((time.time() - t0) * 1000),
            "error": str(e),
        }


async def main():
    print("\n" + "=" * 70)
    print("  PARALLEL TEST RUNNER — Enterprise CI/CD")
    print("=" * 70)

    t0 = time.time()
    tasks = [run_test(f) for f in TEST_FILES if os.path.exists(os.path.join(TESTS_DIR, f))]
    results = await asyncio.gather(*tasks)

    total_passed = 0
    total_tests = 0
    all_ok = True

    print()
    for r in results:
        status = "✅" if r["returncode"] == 0 else "❌"
        p, t = r["passed"], r["total"]
        if p == -1:
            score = "ALL PASSED"
        elif t > 0:
            score = f"{p}/{t}"
            total_passed += p
            total_tests += t
        else:
            score = "?"
        if r["returncode"] != 0:
            all_ok = False
        print(f"  {status} {r['file']:35s} {score:>12s}  ({r['duration_ms']}ms)")

    elapsed = int((time.time() - t0) * 1000)
    print(f"\n  Total: {total_passed}/{total_tests} in {elapsed}ms")
    if all_ok:
        print("  🏆 ALL SUITES PASSED")
    else:
        print("  ⚠️  SOME SUITES FAILED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())


