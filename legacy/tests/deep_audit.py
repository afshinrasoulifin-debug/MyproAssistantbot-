
"""
TITANIUM v29.0 DEEP AUDIT — Find every real issue.
"""
import os
import re


import logging
logger = logging.getLogger(__name__)
ROOT = os.path.dirname(os.path.dirname(__file__))
os.chdir(ROOT)

issues = []

def scan_file(path):
    """Scan a single Python file for issues."""
    try:
        with open(path, 'r', errors='replace') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception:
        return
    
    rel = os.path.relpath(path, ROOT)
    if '__pycache__' in rel or 'tests/' in rel:
        return
    if 'utils/titanium/' in rel:
        return  # Don't audit TITANIUM itself
    
    # 1. Real HTTP library imports (not just string mentions)
    real_http_imports = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.match(r'^\s*(import\s+httpx|import\s+aiohttp|import\s+requests\b|from\s+httpx|from\s+aiohttp|from\s+requests\b)', stripped):
            real_http_imports.append((i, stripped))
    
    # 2. Actual HTTP call patterns
    http_calls = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'httpx\.AsyncClient|aiohttp\.ClientSession|requests\.(get|post|put|delete|patch|request)\(', stripped):
            http_calls.append((i, stripped[:100]))
    
    has_titanium = '_TITANIUM_ACTIVE' in content or 'shielded_get' in content or 'shielded_post' in content
    
    if http_calls and not has_titanium:
        issues.append(('NO_TITANIUM', rel, http_calls))
    
    # 3. Check for unguarded HTTP calls (has TITANIUM import but raw calls outside else: blocks)
    if has_titanium and http_calls:
        # Count actual if _TITANIUM_ACTIVE checks
        guards = len(re.findall(r'if _TITANIUM_ACTIVE', content))
        if len(http_calls) > 0 and guards == 0:
            # Has import but no guards — just has inline try/except style
            inline_titanium = len(re.findall(r'shielded_get|shielded_post|shielded_request', content))
            unguarded = [c for c in http_calls if 'else:' not in content[max(0, content.find(c[1][:30])-200):content.find(c[1][:30])]]
            if len(unguarded) > inline_titanium:
                issues.append(('PARTIAL_TITANIUM', rel, unguarded))
    
    # 4. Silent exception swallowing
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped in ('except Exception:', 'except:', 'except Exception as e:'):
            # Check next non-empty line
            for j in range(i, min(i+3, len(lines))):
                next_line = lines[j].strip()
                if next_line == 'pass':
                    issues.append(('SILENT_EXCEPT', rel, [(i, stripped + ' → pass')]))
                    break
    
    # 5. Raw random usage (not CSPRNG)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'\brandom\.(randint|random|uniform|choice|shuffle|sample|randrange)\(', stripped):
            # Check if this file uses CSPRNG random
            if 'from arki_project.utils.titanium.compat import secure_random as random' not in content:
                if 'except ImportError' not in content[:content.find(stripped[:20])+1] or 'import random' not in content:
                    pass  # It's inside a fallback block
                issues.append(('RAW_RANDOM', rel, [(i, stripped[:80])]))


# Scan all Python files
for root, dirs, files in os.walk(ROOT):
    for f in files:
        if f.endswith('.py'):
            scan_file(os.path.join(root, f))

# Report
logger.info("=" * 60)
logger.info("TITANIUM v29.0 DEEP AUDIT RESULTS")
logger.info("=" * 60)

by_type = {}
for issue_type, path, details in issues:
    by_type.setdefault(issue_type, []).append((path, details))

for itype, items in sorted(by_type.items()):
    logger.info(f"\n{'─'*40}")
    logger.info(f"❌ {itype} ({len(items)} files)")
    logger.info(f"{'─'*40}")
    for path, details in items:
        logger.info(f"  📄 {path}")
        for line_no, desc in details[:3]:
            logger.info(f"     L{line_no}: {desc}")

logger.info(f"\n{'='*60}")
logger.info(f"Total issues: {len(issues)}")


