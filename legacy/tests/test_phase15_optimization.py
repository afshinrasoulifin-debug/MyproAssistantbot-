
#!/usr/bin/env python3
"""
Phase 15 Tests: Deep Optimization Verification.
Checks infrastructure quality, no thin files, no bare excepts, no prints.
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)

SKIP = {"__pycache__", "arki_project", "node_modules", ".git"}
passed = 0
failed = 0
total = 0


def check(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  ❌ {name}: {detail}")


# L1: No thin infrastructure files
thin_infra = 0
for root, dirs, files in os.walk("infrastructure", followlinks=False):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            fp = os.path.join(root, f)
            lines = len(open(fp).readlines())
            if lines < 35:
                thin_infra += 1

check("L01 No thin infra files (<35L)", thin_infra == 0, f"{thin_infra} thin files remain")

# L2: All infra files have async methods
infra_with_async = 0
infra_total = 0
for root, dirs, files in os.walk("infrastructure", followlinks=False):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            fp = os.path.join(root, f)
            code = open(fp).read()
            infra_total += 1
            if "async def" in code or "await " in code:
                infra_with_async += 1

pct = (infra_with_async / infra_total * 100) if infra_total else 0
check("L02 Infra files with async >= 80%", pct >= 80, f"{pct:.0f}% ({infra_with_async}/{infra_total})")

# L3: All infra files have get_stats or get_status
infra_with_stats = 0
for root, dirs, files in os.walk("infrastructure", followlinks=False):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            code = open(os.path.join(root, f)).read()
            if "get_stats" in code or "get_status" in code:
                infra_with_stats += 1

pct2 = (infra_with_stats / infra_total * 100) if infra_total else 0
check("L03 Infra files with stats >= 45%", pct2 >= 45, f"{pct2:.0f}% ({infra_with_stats}/{infra_total})")

# L4: All infra files have logging
infra_with_log = 0
for root, dirs, files in os.walk("infrastructure", followlinks=False):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            code = open(os.path.join(root, f)).read()
            if "logger" in code or "logging" in code:
                infra_with_log += 1

pct3 = (infra_with_log / infra_total * 100) if infra_total else 0
check("L04 Infra files with logging >= 90%", pct3 >= 90, f"{pct3:.0f}%")

# L5: No bare excepts in test files
bare = 0
for root, dirs, files_list in os.walk("tests", followlinks=False):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files_list:
        if f.endswith(".py"):
            test_code = open(os.path.join(root, f)).read()
            for ln in test_code.split("\n"):
                s = ln.strip()
                if re.match(r'except\s*:', s) and not s.startswith('#') and not s.startswith('"') and not s.startswith("'"):
                    bare += 1

check("L05 No bare excepts in tests", bare == 0, f"{bare} bare excepts")

# L6: No print statements in handlers/utils
prints = 0
for folder in ["handlers", "utils"]:
    for root, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                for line in open(os.path.join(root, f)):
                    if re.match(r'\s*print\(', line) and "# debug" not in line.lower():
                        prints += 1

check("L06 No print stmts in handlers/utils", prints == 0, f"{prints} prints")

# L7: No hardcoded localhost (outside tests/scripts)
hardcoded = 0
for root, dirs, files in os.walk(".", followlinks=False):
    dirs[:] = [d for d in dirs if d not in SKIP and d != "tests" and d != "scripts"]
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            for line in open(fp):
                if re.search(r'"http://(localhost|127\.0\.0\.1):\d+"', line):
                    hardcoded += 1

check("L07 No hardcoded localhost (max 2 env fallbacks)", hardcoded <= 2, f"{hardcoded} hardcoded URLs")

# L8: All infra syntax valid
syntax_errors = 0
for root, dirs, files in os.walk("infrastructure", followlinks=False):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                compile(open(fp).read(), fp, "exec")
            except SyntaxError:
                syntax_errors += 1

check("L08 All infra syntax valid", syntax_errors == 0, f"{syntax_errors} errors")

# L9: Architecture layers enhanced
arch_thin = 0
for root, dirs, files in os.walk("architecture/layer", followlinks=False):
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            if len(open(os.path.join(root, f)).readlines()) < 35:
                arch_thin += 1

check("L09 Architecture layers enhanced", arch_thin == 0, f"{arch_thin} thin")

# L10: Extra routes enhanced
extra_thin = 0
for f in ["extra/routes/docs.py", "extra/routes/model_select.py"]:
    if os.path.exists(f) and len(open(f).readlines()) < 35:
        extra_thin += 1

check("L10 Extra routes enhanced", extra_thin == 0, f"{extra_thin} thin")

# L11: Total project Python lines increased
total_lines = 0
total_py = 0
for root, dirs, files in os.walk(".", followlinks=False):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if f.endswith(".py"):
            total_py += 1
            total_lines += len(open(os.path.join(root, f)).readlines())

check("L11 Total Python lines >= 175000", total_lines >= 175000, f"only {total_lines:,}")
check("L12 Total Python files >= 815", total_py >= 815, f"only {total_py}")

# Summary
print(f"\n{'=' * 60}")
print(f"  Phase 15: {passed}/{total} passed ({passed * 100 // total}%)")
print(f"{'=' * 60}")

sys.exit(0 if failed == 0 else 1)


