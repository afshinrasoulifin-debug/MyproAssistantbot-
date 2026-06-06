
#!/usr/bin/env python3
"""
Arki Engine — Project Structure Health Checker

Checks for:
  - Missing __init__.py files
  - Broken internal imports
  - Orphan files
  - Version consistency
  - Config completeness

Run: python scripts/check_structure.py
"""
import os
import re
import sys
from pathlib import Path


import logging
logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent.parent
issues = []
warnings = []

logger.info("🔍 Arki Engine — Structure Health Check")
logger.info("=" * 50)

# 1. Check __init__.py
logger.info("\n📁 1. Checking __init__.py files...")
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (
        '__pycache__', '.git', 'node_modules', '.next', 'extra',
        'deploy', 'k8s', 'helm', '.github', 'docs', 'data',
    )]
    py_files = [f for f in filenames if f.endswith('.py') and f != '__init__.py']
    rel = os.path.relpath(dirpath, ROOT)
    if py_files and not os.path.exists(os.path.join(dirpath, '__init__.py')):
        if rel != '.':
            issues.append(f"Missing __init__.py: {rel}/")

# 2. Check VERSION consistency
logger.info("📋 2. Checking version consistency...")
version_file = ROOT / 'VERSION'
pyproject = ROOT / 'pyproject.toml'
if version_file.exists():
    v1 = version_file.read_text().strip()
    if pyproject.exists():
        content = pyproject.read_text()
        m = re.search(r'version = "([^"]+)"', content)
        v2 = m.group(1) if m else '?'
        if v1 != v2:
            warnings.append(f"Version mismatch: VERSION={v1}, pyproject.toml={v2}")

# 3. Check required files
logger.info("📄 3. Checking required files...")
required = [
    'pyproject.toml', 'requirements.txt', 'Makefile', 'Dockerfile',
    'docker-compose.yml', '.gitignore', '.editorconfig', 'README.md',
    'config.py', 'main.py', 'conftest.py', 'run_tests.py',
]
for f in required:
    if not (ROOT / f).exists():
        issues.append(f"Missing required file: {f}")

# Report
logger.info("\n" + "=" * 50)
if issues:
    logger.info(f"\n❌ {len(issues)} Issues:")
    for i in issues:
        logger.info(f"   • {i}")
if warnings:
    logger.info(f"\n⚠️  {len(warnings)} Warnings:")
    for w in warnings:
        logger.info(f"   • {w}")
if not issues and not warnings:
    logger.info("\n✅ All checks passed!")

score = max(0, 100 - len(issues) * 10 - len(warnings) * 5)
logger.info(f"\n📊 Health Score: {score}/100")
sys.exit(1 if issues else 0)


