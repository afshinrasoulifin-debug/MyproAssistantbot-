
#!/usr/bin/env python3
"""
Run all Arki Engine v9 tests with coverage reporting.

Usage:
    python -m pytest tests/ -v
    python tests/run_all_tests.py
"""

import subprocess
import sys
import os


import logging
logger = logging.getLogger(__name__)
def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("=" * 60)
    logger.info("🧪 ARKI ENGINE v9 — TEST SUITE")
    logger.info("=" * 60)
    
    # Run pytest with verbose output
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
        capture_output=False,
    )
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())


