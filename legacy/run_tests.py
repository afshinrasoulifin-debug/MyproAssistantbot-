
#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  ARKI ENGINE v29.0.0 — Real Test Runner
═══════════════════════════════════════════════════════════════════
  Uses pytest to actually run all tests in tests/ directory.
  Usage:
    python run_tests.py              # run all tests
    python run_tests.py --unit       # only unit tests
    python run_tests.py --integration # only integration tests
    python run_tests.py -k "pattern" # filter by name
═══════════════════════════════════════════════════════════════════
"""
import subprocess
import sys
import os


import logging
logger = logging.getLogger(__name__)
def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    args = ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
    
    if "--unit" in sys.argv:
        args.extend(["-m", "unit"])
        sys.argv.remove("--unit")
    elif "--integration" in sys.argv:
        args.extend(["-m", "integration"])
        sys.argv.remove("--integration")
    
    # Pass through any extra args (like -k "pattern")
    extra = [a for a in sys.argv[1:] if a not in ("--unit", "--integration")]
    args.extend(extra)
    
    logger.info("=" * 72)
    logger.info("  🧪 ARKI ENGINE v29.0.0 — Running Tests")
    logger.info("=" * 72)
    logger.info(f"  Command: {' '.join(args)}")
    logger.info("=" * 72)
    
    result = subprocess.run(args)
    
    logger.info("\n" + "=" * 72)
    if result.returncode == 0:
        logger.info("  ✅ ALL TESTS PASSED")
    else:
        logger.info(f"  ❌ TESTS FAILED (exit code: {result.returncode})")
    logger.info("=" * 72)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()


