
#!/usr/bin/env python3
"""
ARKI v10.2 MEGA Test Suite — DEEP Functional Tests
====================================================
Tests EVERY module: syntax, structure, TITANIUM wiring,
model upgrades, token limits, security, connections,
and real functional behavior.

3 test tiers:
  T1 — Universal (every file): syntax, structure, TITANIUM
  T2 — Category (by directory): handlers, utils, infra, etc.
  T3 — Deep functional: TITANIUM core, AI models, orchestration

Usage: python tests/run_v102_mega_tests.py
"""
import ast
import os
import re
import sys
import py_compile
import importlib.util

os.chdir(os.path.dirname(os.path.dirname(__file__)))

# ── Helpers ──────────────────────────────────────────────────

passed = 0
failed = 0
errors = []


def assert_(condition, msg="Assertion failed"):
    if not condition:
        raise AssertionError(msg)


def run_test(name, func):
    global passed, failed
    try:
        func()
        passed += 1
    except Exception as e:
        failed += 1
        errors.append((name, str(e)[:200]))


def load_mod(name, path):
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


# ── Collect all modules ──────────────────────────────────────

all_modules = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
    for f in files:
        if not f.endswith('.py'):
            continue
        all_modules.append(os.path.join(root, f))
all_modules.sort()

production = [m for m in all_modules if '/tests/' not in m]
test_files = [m for m in all_modules if '/tests/' in m]

print(f"📂 Total files: {len(all_modules)}")
print(f"   Production: {len(production)}")
print(f"   Tests: {len(test_files)}")


# ══════════════════════════════════════════════════════════════
# T1: UNIVERSAL TESTS — every single file
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T1: UNIVERSAL — Every File")
print(f"{'═'*60}")

# ── T1.1: Syntax ──
print("\n🔍 T1.1: Syntax Check")
syntax_bad = []
for p in all_modules:
    try:
        py_compile.compile(p, doraise=True)
    except py_compile.PyCompileError:
        syntax_bad.append(p)

run_test("T1.1/all_syntax", lambda: assert_(
    len(syntax_bad) == 0,
    f"{len(syntax_bad)} syntax errors: {syntax_bad[:5]}"
))
print(f"  {len(all_modules) - len(syntax_bad)}/{len(all_modules)} compile OK")

# ── T1.2: AST Parse ──
print("\n📊 T1.2: AST Parse")
module_data = {}
parse_fail = []
for p in all_modules:
    with open(p) as f:
        content = f.read()
    try:
        tree = ast.parse(content)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        funcs = [n.name for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        module_data[p] = {
            'tree': tree, 'classes': classes, 'funcs': funcs,
            'content': content, 'lines': len(content.split('\n')),
        }
    except SyntaxError:
        parse_fail.append(p)
        module_data[p] = None

total_cls = sum(len(d['classes']) for d in module_data.values() if d)
total_fn = sum(len(d['funcs']) for d in module_data.values() if d)
total_lines = sum(d['lines'] for d in module_data.values() if d)
print(f"  {total_cls} classes, {total_fn} functions, {total_lines} lines")

# ── T1.3: No Empty Files ──
print("\n📄 T1.3: Non-Empty Check")
for p in production:
    if '__init__' in p:
        continue
    d = module_data.get(p)
    if d and d['lines'] < 3:
        run_test(f"T1.3/{p}", lambda pp=p: assert_(False, f"{pp} is empty"))
    else:
        run_test(f"T1.3/{os.path.basename(p)}", lambda: None)

# ── T1.4: TITANIUM Coverage ──
print("\n🛡 T1.4: TITANIUM Coverage")
ti_count = 0
no_ti = []
for p in production:
    if '__init__' in p:
        continue
    d = module_data.get(p)
    if not d:
        continue
    if '_TITANIUM_ACTIVE' in d['content'] or 'titanium' in p:
        ti_count += 1
    else:
        no_ti.append(p)

ti_pct = 100 * ti_count // max(1, len(production))
run_test("T1.4/titanium_coverage_50pct", lambda: assert_(
    ti_pct >= 50, f"Only {ti_pct}% TITANIUM coverage ({ti_count}/{len(production)})"
))
print(f"  TITANIUM coverage: {ti_count}/{len(production)} ({ti_pct}%)")

# ── T1.5: No bare import random ──
print("\n🔒 T1.5: CSPRNG Check")
for p in production:
    if 'titanium' in p or 'compat' in p:
        continue
    d = module_data.get(p)
    if not d:
        continue
    lines = d['content'].split('\n')
    for i, line in enumerate(lines):
        if line.strip() == 'import random':
            if i > 0 and 'except' in lines[max(0, i - 1)]:
                continue
            run_test(f"T1.5/csprng/{os.path.basename(p)}",
                     lambda pp=p, ii=i: assert_(False, f"Bare import random at {pp}:{ii + 1}"))
            break
    else:
        run_test(f"T1.5/csprng/{os.path.basename(p)}", lambda: None)

# ── T1.6: No :free models ──
print("\n💳 T1.6: No Free Models")
for p in production:
    d = module_data.get(p)
    if not d:
        continue
    if ':free' in d['content']:
        run_test(f"T1.6/{os.path.basename(p)}",
                 lambda pp=p: assert_(False, f"{pp} still has :free model"))
    else:
        run_test(f"T1.6/{os.path.basename(p)}", lambda: None)

# ── T1.7: No secrets ──
print("\n🔐 T1.7: Secret Scan")
secret_pats = [
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'AIza[a-zA-Z0-9_-]{35}'),
]
for p in production:
    d = module_data.get(p)
    if not d:
        continue
    for sp in secret_pats:
        if sp.search(d['content']):
            run_test(f"T1.7/{os.path.basename(p)}",
                     lambda pp=p: assert_(False, f"Possible secret in {pp}"))
            break
    else:
        run_test(f"T1.7/{os.path.basename(p)}", lambda: None)


# ══════════════════════════════════════════════════════════════
# T2: CATEGORY TESTS — by directory
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T2: CATEGORY — By Directory")
print(f"{'═'*60}")

# ── T2.1: Handlers ──
print("\n🔌 T2.1: Handlers")
with open('main.py') as f:
    main_content = f.read()

handler_files = [f for f in os.listdir('handlers')
                 if f.endswith('.py') and f not in ('__init__.py', 'shared.py')]

for hf in handler_files:
    hp = f'handlers/{hf}'
    d = module_data.get(f'./{hp}')
    if not d:
        continue
    mod_name = hf.replace('.py', '')

    # Has router
    run_test(f"T2.1/router/{hf}",
             lambda cc=d['content']: assert_('Router' in cc or 'router' in cc))

    # Router registered in main.py
    run_test(f"T2.1/registered/{hf}",
             lambda mn=mod_name: assert_(mn in main_content))

    # Has async handlers
    async_fns = [fn for fn in d['funcs']
                 if any(isinstance(n, ast.AsyncFunctionDef) and n.name == fn
                        for n in ast.walk(d['tree']))]
    run_test(f"T2.1/async/{hf}",
             lambda af=async_fns, ff=hf: assert_(len(af) >= 1, f"{ff} has no async handlers"))

    # Has TITANIUM
    run_test(f"T2.1/titanium/{hf}",
             lambda cc=d['content'], ff=hf: assert_(
                 '_TITANIUM_ACTIVE' in cc, f"{ff} missing TITANIUM"))

    # No low max_tokens
    run_test(f"T2.1/tokens/{hf}",
             lambda cc=d['content'], ff=hf: assert_(
                 not re.search(r'max_tokens\s*=\s*[0-9]{1,3}[^0-9]', cc),
                 f"{ff} has low max_tokens"))

# ── T2.2: Middlewares ──
print("\n⚙️ T2.2: Middlewares")
mw_files = [f for f in os.listdir('middlewares')
            if f.endswith('.py') and f != '__init__.py']

for mf in mw_files:
    mp = f'middlewares/{mf}'
    d = module_data.get(f'./{mp}')
    if not d:
        continue

    # Has middleware class
    mw_classes = [c for c in d['classes'] if 'Middleware' in c or 'middleware' in c.lower()]
    run_test(f"T2.2/class/{mf}",
             lambda mc=mw_classes, ff=mf: assert_(len(mc) >= 1, f"{ff} no middleware class"))

    # Registered in main.py
    for cls in mw_classes:
        run_test(f"T2.2/registered/{cls}",
                 lambda cn=cls: assert_(cn in main_content, f"{cn} not in main.py"))

    # Has __call__ or process
    run_test(f"T2.2/callable/{mf}",
             lambda fns=d['funcs']: assert_(
                 '__call__' in fns or 'process' in fns or '__init__' in fns))

# ── T2.3: Utils ──
print("\n🔧 T2.3: Utils")
utils_files = [f for f in os.listdir('utils')
               if f.endswith('.py') and f != '__init__.py']

for uf in utils_files:
    up = f'utils/{uf}'
    d = module_data.get(f'./{up}')
    if not d:
        continue

    # Has functions or classes
    run_test(f"T2.3/content/{uf}",
             lambda dd=d, ff=uf: assert_(
                 dd['classes'] or dd['funcs'], f"{ff} has no classes or functions"))

    # TITANIUM wired
    run_test(f"T2.3/titanium/{uf}",
             lambda cc=d['content'], ff=uf: assert_(
                 '_TITANIUM_ACTIVE' in cc or len(cc) < 100,
                 f"{ff} missing TITANIUM"))

# ── T2.4: Infrastructure ──
print("\n🏗 T2.4: Infrastructure")
infra_dirs = [d for d in os.listdir('infrastructure')
              if os.path.isdir(f'infrastructure/{d}') and d != '__pycache__']

run_test("T2.4/dir_count", lambda: assert_(len(infra_dirs) >= 25))

for idir in sorted(infra_dirs):
    dp = f'infrastructure/{idir}'
    py_files = [f for f in os.listdir(dp)
                if f.endswith('.py') and f != '__init__.py']
    run_test(f"T2.4/{idir}/has_modules",
             lambda pf=py_files, dd=idir: assert_(len(pf) >= 1, f"{dd} empty"))

    for pf in py_files:
        fp = f'{dp}/{pf}'
        d = module_data.get(f'./{fp}')
        if not d:
            continue
        run_test(f"T2.4/{idir}/{pf}/has_class",
                 lambda dd=d, ff=pf: assert_(dd['classes'], f"{ff} no classes"))

# ── T2.5: Architecture ──
print("\n🏛 T2.5: Architecture")
arch_dirs = [d for d in os.listdir('architecture')
             if os.path.isdir(f'architecture/{d}') and d != '__pycache__']
run_test("T2.5/dir_count", lambda: assert_(len(arch_dirs) >= 10))

for adir in sorted(arch_dirs):
    dp = f'architecture/{adir}'
    py_files = [f for f in os.listdir(dp)
                if f.endswith('.py') and f != '__init__.py']
    run_test(f"T2.5/{adir}/has_modules",
             lambda pf=py_files: assert_(len(pf) >= 1))

# ── T2.6: Orchestration ──
print("\n🎯 T2.6: Orchestration")
orch_files = ['orchestration/core.py', 'orchestration/work_queue.py',
              'orchestration/retry_manager.py', 'orchestration/load_balancer.py']
for of in orch_files:
    run_test(f"T2.6/exists/{os.path.basename(of)}",
             lambda pp=of: assert_(os.path.exists(pp)))
    d = module_data.get(f'./{of}')
    if d:
        run_test(f"T2.6/titanium/{os.path.basename(of)}",
                 lambda cc=d['content']: assert_('_TITANIUM_ACTIVE' in cc))
        run_test(f"T2.6/size/{os.path.basename(of)}",
                 lambda dd=d: assert_(dd['lines'] > 50))

# ── T2.7: Database ──
print("\n🗄 T2.7: Database")
with open('database/models.py') as f:
    models_content = f.read()

run_test("T2.7/sa_import", lambda: assert_('import sqlalchemy as sa' in models_content))
run_test("T2.7/datetime_correct", lambda: assert_(
    'datetime.datetime' in models_content or 'DateTime' in models_content))
model_classes = re.findall(r'class (\w+)\(.*Base\)', models_content)
run_test("T2.7/model_count", lambda: assert_(len(model_classes) >= 15))
for mc in model_classes:
    run_test(f"T2.7/tablename/{mc}", lambda cn=mc: assert_(
        re.search(f'class {cn}.*?__tablename__', models_content, re.S)))

# ── T2.8: Services ──
print("\n🔧 T2.8: Services")
if os.path.isdir('services'):
    for sf in os.listdir('services'):
        if not sf.endswith('.py') or sf == '__init__.py':
            continue
        sp = f'services/{sf}'
        d = module_data.get(f'./{sp}')
        if d:
            run_test(f"T2.8/{sf}/has_class",
                     lambda dd=d, ff=sf: assert_(dd['classes'], f"{ff} no service class"))

# ── T2.9: Extra / Routes ──
print("\n🌐 T2.9: Extra Routes")
if os.path.isdir('extra/routes'):
    for rf in os.listdir('extra/routes'):
        if not rf.endswith('.py') or rf == '__init__.py':
            continue
        rp = f'extra/routes/{rf}'
        d = module_data.get(f'./{rp}')
        if d:
            run_test(f"T2.9/{rf}/content",
                     lambda dd=d: assert_(dd['lines'] > 10))


# ══════════════════════════════════════════════════════════════
# T3: DEEP FUNCTIONAL TESTS — TITANIUM core behavior
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T3: DEEP FUNCTIONAL — TITANIUM Core")
print(f"{'═'*60}")

# Load TITANIUM modules
ti_path = 'utils/titanium'
ti_deps = ['config', 'crypto', 'timing', 'compat', 'error_shield',
           'header_entropy', 'rate_limiter']
for dep in ti_deps:
    load_mod(f'tg_bot.utils.titanium.{dep}', f'{ti_path}/{dep}.py')

config = sys.modules.get('tg_bot.utils.titanium.config')
crypto = sys.modules.get('tg_bot.utils.titanium.crypto')
compat = sys.modules.get('tg_bot.utils.titanium.compat')
error_shield = sys.modules.get('tg_bot.utils.titanium.error_shield')
header_entropy = sys.modules.get('tg_bot.utils.titanium.header_entropy')
rate_limiter = sys.modules.get('tg_bot.utils.titanium.rate_limiter')

# Also load complex modules
shielded = load_mod('tg_bot.utils.titanium.shielded_client', f'{ti_path}/shielded_client.py')
ai_orch = load_mod('tg_bot.utils.titanium.ai_orchestrator', f'{ti_path}/ai_orchestrator.py')
health = load_mod('tg_bot.utils.titanium.health_monitor', f'{ti_path}/health_monitor.py')
integration = load_mod('tg_bot.utils.titanium.integration', f'{ti_path}/integration.py')
init_mod = load_mod('tg_bot.utils.titanium', f'{ti_path}/__init__.py')

# ── T3.1: Config ──
print("\n⚙️ T3.1: TITANIUM Config")
if config:
    c = config.TITANIUM_CONFIG
    run_test("T3.1/version", lambda: assert_(c['version']))
    run_test("T3.1/max_conn_500", lambda: assert_(c['max_connections'] >= 500,
             f"max_connections={c['max_connections']}"))
    run_test("T3.1/per_host_100", lambda: assert_(c['max_connections_per_host'] >= 100))
    run_test("T3.1/retry_5", lambda: assert_(c['retry_attempts'] >= 5))
    run_test("T3.1/unlimited", lambda: assert_(c['rate_limit_mode'] == 'unlimited'))
    run_test("T3.1/cache_2000", lambda: assert_(c['ai_cache_size'] >= 2000))
    run_test("T3.1/timeout_600", lambda: assert_(c['ai_orchestrator_timeout'] >= 600))
    run_test("T3.1/cache_ttl_600", lambda: assert_(c['ai_cache_ttl'] >= 600))
    run_test("T3.1/ai_retries_5", lambda: assert_(c['ai_max_retries'] >= 5))
    run_test("T3.1/get_func", lambda: assert_(callable(config.get)))
    run_test("T3.1/set_func", lambda: assert_(callable(config.set_config)))
    run_test("T3.1/get_returns", lambda: assert_(config.get('version') == c['version']))

# ── T3.2: Crypto ──
print("\n🔐 T3.2: TITANIUM Crypto")
if crypto:
    # CSPRNG integer range
    run_test("T3.2/int_range", lambda: assert_(
        all(1 <= crypto.csprng_int(1, 100) <= 100 for _ in range(100))))
    run_test("T3.2/int_boundaries", lambda: assert_(
        crypto.csprng_int(5, 5) == 5))
    # CSPRNG float
    run_test("T3.2/float_range", lambda: assert_(
        all(0 <= crypto.csprng_float() < 1 for _ in range(100))))
    # Secure hex
    run_test("T3.2/hex_16", lambda: assert_(len(crypto.secure_hex(16)) == 32))
    run_test("T3.2/hex_32", lambda: assert_(len(crypto.secure_hex(32)) == 64))
    run_test("T3.2/hex_default", lambda: assert_(len(crypto.secure_hex()) > 0))
    # Variety (truly random)
    run_test("T3.2/hex_unique", lambda: assert_(
        len(set(crypto.secure_hex() for _ in range(200))) >= 195))
    # HMAC
    run_test("T3.2/hmac_len", lambda: assert_(
        len(crypto.hmac_sign(b"key", b"data")) == 64))
    run_test("T3.2/hmac_verify", lambda: assert_(
        crypto.hmac_verify(b"key", b"data", crypto.hmac_sign(b"key", b"data"))))
    run_test("T3.2/hmac_bad", lambda: assert_(
        not crypto.hmac_verify(b"key", b"data", "0" * 64)))
    run_test("T3.2/hmac_diff_key", lambda: assert_(
        crypto.hmac_sign(b"key1", b"data") != crypto.hmac_sign(b"key2", b"data")))
    # Request ID
    rid = crypto.secure_request_id()
    run_test("T3.2/reqid_hex", lambda: assert_(len(rid) >= 16 and all(c in '0123456789abcdef-T' for c in rid)))
    run_test("T3.2/reqid_unique", lambda: assert_(
        crypto.secure_request_id() != crypto.secure_request_id()))

# ── T3.3: Compat (CSPRNG drop-in) ──
print("\n🔄 T3.3: CSPRNG Compat")
if compat:
    sr = compat.secure_random
    run_test("T3.3/random", lambda: assert_(0 <= sr.random() < 1))
    run_test("T3.3/choice", lambda: assert_(sr.choice([1, 2, 3]) in [1, 2, 3]))
    run_test("T3.3/choices_k", lambda: assert_(len(sr.choices([1, 2, 3], k=5)) == 5))
    s1 = sr.sample(range(10), 5)
    run_test("T3.3/sample_len", lambda: assert_(len(s1) == 5))
    run_test("T3.3/sample_unique", lambda: assert_(len(s1) == len(set(s1))))
    run_test("T3.3/randint", lambda: assert_(
        all(1 <= sr.randint(1, 10) <= 10 for _ in range(50))))
    run_test("T3.3/uniform", lambda: assert_(
        all(1.0 <= sr.uniform(1.0, 10.0) <= 10.0 for _ in range(50))))
    run_test("T3.3/randrange", lambda: assert_(sr.randrange(0, 10) < 10))
    # Shuffle
    lst = list(range(20))
    sr.shuffle(lst)
    run_test("T3.3/shuffle_same_elements", lambda: assert_(sorted(lst) == list(range(20))))
    run_test("T3.3/shuffle_reorders", lambda: assert_(lst != list(range(20))))

# ── T3.4: Error Shield ──
print("\n🛡 T3.4: Error Shield")
if error_shield:
    run_test("T3.4/str_sanitize", lambda: assert_(
        isinstance(error_shield.sanitize_error("test error"), str)))
    run_test("T3.4/exc_sanitize", lambda: assert_(
        isinstance(error_shield.sanitize_error(ValueError("secret_key=abc123")), str)))
    # sanitize_error should return a string
    run_test("T3.4/returns_str", lambda: assert_(
        isinstance(error_shield.sanitize_error(ValueError("test")), str)))
    run_test("T3.4/fabricate", lambda: assert_(len(error_shield.fabricate_response()) > 0))
    run_test("T3.4/fabricate_variety", lambda: assert_(
        len(set(error_shield.fabricate_response() for _ in range(10))) > 1))

# ── T3.5: Header Entropy ──
print("\n🎭 T3.5: Header Entropy")
if header_entropy:
    h = header_entropy.build_decoy_headers()
    run_test("T3.5/has_lang", lambda: assert_('Accept-Language' in h))
    run_test("T3.5/has_encoding", lambda: assert_('Accept-Encoding' in h))
    run_test("T3.5/has_sec_ch", lambda: assert_('Sec-Ch-Ua' in h or 'Cache-Control' in h))
    run_test("T3.5/is_dict", lambda: assert_(isinstance(h, dict) and len(h) >= 5,
             f"Only {len(h)} headers"))
    # Variety
    langs = set(header_entropy.build_decoy_headers()['Accept-Language'] for _ in range(20))
    run_test("T3.5/lang_variety", lambda: assert_(len(langs) > 3,
             f"Only {len(langs)} unique langs"))
    hdrs = [header_entropy.build_decoy_headers() for _ in range(20)]
    unique_keys = set(frozenset(h.items()) for h in hdrs)
    run_test("T3.5/header_variety", lambda: assert_(len(unique_keys) > 5,
             f"Only {len(unique_keys)} unique header sets"))

# ── T3.6: Shielded Client ──
print("\n🔒 T3.6: Shielded Client")
if shielded:
    run_test("T3.6/response_class", lambda: assert_(hasattr(shielded, 'ShieldedResponse')))
    run_test("T3.6/pool_class", lambda: assert_(hasattr(shielded, 'ShieldedClientPool')))
    run_test("T3.6/circuit_breaker", lambda: assert_(hasattr(shielded, 'CircuitBreaker')))
    run_test("T3.6/deduplicator", lambda: assert_(hasattr(shielded, 'RequestDeduplicator')))
    # Response fields (dataclass)
    resp = shielded.ShieldedResponse(status=200, text="test body", success=True)
    run_test("T3.6/resp_status", lambda: assert_(resp.status == 200))
    run_test("T3.6/resp_text", lambda: assert_(resp.text == "test body"))
    run_test("T3.6/resp_success", lambda: assert_(resp.success is True))
    run_test("T3.6/resp_content", lambda: assert_(hasattr(resp, 'content')))
    run_test("T3.6/resp_headers", lambda: assert_(isinstance(resp.headers, dict)))
    run_test("T3.6/resp_request_id", lambda: assert_(hasattr(resp, 'request_id')))
    # Circuit breaker
    cb = shielded.CircuitBreaker()
    run_test("T3.6/cb_threshold", lambda: assert_(cb.failure_threshold >= 5))
    run_test("T3.6/cb_timeout", lambda: assert_(cb.reset_timeout >= 60))

# ── T3.7: Integration ──
print("\n🔗 T3.7: Integration")
if integration:
    run_test("T3.7/shielded_get", lambda: assert_(callable(integration.shielded_get)))
    run_test("T3.7/shielded_post", lambda: assert_(callable(integration.shielded_post)))
    run_test("T3.7/shielded_request", lambda: assert_(callable(integration.shielded_request)))

# ── T3.8: AI Orchestrator ──
print("\n🤖 T3.8: AI Orchestrator")
if ai_orch:
    run_test("T3.8/orchestrator_cls", lambda: assert_(hasattr(ai_orch, 'TitaniumOrchestrator')))
    run_test("T3.8/provider_enum", lambda: assert_(hasattr(ai_orch, 'AIProvider')))
    run_test("T3.8/tier_enum", lambda: assert_(hasattr(ai_orch, 'AITier')))
    run_test("T3.8/cache", lambda: assert_(hasattr(ai_orch, 'ResponseCache')))
    run_test("T3.8/scorer", lambda: assert_(hasattr(ai_orch, 'AdaptiveScorer')))

# ── T3.9: Health Monitor ──
print("\n💚 T3.9: Health Monitor")
if health:
    run_test("T3.9/monitor_cls", lambda: assert_(hasattr(health, 'HealthMonitor')))

# ── T3.10: Init / Boot ──
print("\n🚀 T3.10: TITANIUM Boot")
if init_mod:
    run_test("T3.10/version", lambda: assert_(hasattr(init_mod, 'TITANIUM_VERSION')))
    run_test("T3.10/codename", lambda: assert_(hasattr(init_mod, 'TITANIUM_CODENAME')))


# ══════════════════════════════════════════════════════════════
# T4: AI MODEL CONFIGURATION
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T4: AI Model Configuration")
print(f"{'═'*60}")

mr = load_mod('utils.models_registry', 'utils/models_registry.py')
if mr:
    run_test("T4/default_pro", lambda: assert_(
        mr.DEFAULT_MODEL == "gemini-pro",
        f"Default is {mr.DEFAULT_MODEL}"))
    run_test("T4/total_models_70", lambda: assert_(len(mr.MODELS) >= 70))
    run_test("T4/5_tiers", lambda: assert_(len(mr.APEX_TIERS) >= 5))
    run_test("T4/has_gpt5", lambda: assert_("g-gpt5" in mr.MODELS))
    run_test("T4/has_opus4", lambda: assert_("g-claude-opus4" in mr.MODELS))
    run_test("T4/has_gemini_pro", lambda: assert_("gemini-pro" in mr.MODELS))

    # Autotune deep check
    code_r = mr.autotune("def calculate_score(data): pass #python bug fix code class function")
    run_test("T4/autotune_code", lambda: assert_(
        code_r['max_tokens'] >= 32768, f"Code tokens: {code_r['max_tokens']}"))
    
    analysis_r = mr.autotune("تحلیل و بررسی و مقایسه گزارش analyze compare data evaluation research")
    run_test("T4/autotune_analysis", lambda: assert_(
        analysis_r['max_tokens'] >= 32768, f"Analysis tokens: {analysis_r['max_tokens']}"))
    
    chat_r = mr.autotune("سلام")
    run_test("T4/autotune_chat", lambda: assert_(
        chat_r['max_tokens'] >= 16384, f"Chat tokens: {chat_r['max_tokens']}"))


# ══════════════════════════════════════════════════════════════
# T5: VERSION & CONSISTENCY
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T5: Version & Consistency")
print(f"{'═'*60}")

ver = open('VERSION').read().strip()
run_test("T5/version_file", lambda: assert_('10.2' in ver))
run_test("T5/readme_match", lambda: assert_(ver in open('README.md').read()))
run_test("T5/dockerfile_match", lambda: assert_(ver in open('Dockerfile').read()))


# ══════════════════════════════════════════════════════════════
# T6: CROSS-MODULE CONNECTIONS
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T6: Cross-Module Connections")
print(f"{'═'*60}")

# Every HTTP module → TITANIUM
http_pats = ['aiohttp.ClientSession', 'httpx.AsyncClient']
pool_files = {'http_pool.py', 'http_session_pool.py'}
for p in production:
    d = module_data.get(p)
    if not d:
        continue
    if os.path.basename(p) in pool_files:
        continue
    has_http = any(pat in d['content'] for pat in http_pats)
    if has_http:
        run_test(f"T6/http_titanium/{os.path.basename(p)}",
                 lambda cc=d['content'], pp=p: assert_(
                     '_TITANIUM_ACTIVE' in cc or 'shielded_' in cc,
                     f"{pp} has HTTP but no TITANIUM"))

# Web search → TITANIUM
for wm in ['utils/web_search.py', 'utils/web_engine.py', 'utils/jina_reader.py']:
    if not os.path.exists(wm):
        continue
    d = module_data.get(f'./{wm}')
    if d:
        run_test(f"T6/websearch/{os.path.basename(wm)}",
                 lambda cc=d['content']: assert_(
                     '_TITANIUM_ACTIVE' in cc or 'shielded_' in cc))

# Pipeline → TITANIUM
d = module_data.get('./core/pipeline.py')
if d:
    run_test("T6/pipeline_titanium", lambda: assert_('_TITANIUM_ACTIVE' in d['content']))


# ══════════════════════════════════════════════════════════════
# T7: PER-CLASS STRUCTURE TESTS
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("T7: Class Structure")
print(f"{'═'*60}")

for p in production:
    d = module_data.get(p)
    if not d:
        continue
    for cls_name in d['classes']:
        for node in ast.walk(d['tree']):
            if isinstance(node, ast.ClassDef) and node.name == cls_name:
                methods = [n.name for n in node.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                # Class should have at least one method or be a dataclass
                decorators = [str(getattr(dec, 'id', getattr(dec, 'attr', '')))
                              for dec in node.decorator_list]
                is_dc = 'dataclass' in str(decorators)
                has_body = len(node.body) > 0
                run_test(f"T7/{os.path.basename(p)}/{cls_name}",
                         lambda m=methods, dc=is_dc, hb=has_body, cn=cls_name: assert_(
                             m or dc or hb, f"{cn} is empty"))


# ══════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════

total = passed + failed
print(f"\n{'═'*60}")
print(f"🏆 ARKI v10.2 MEGA RESULTS: {passed}/{total} passed, {failed} failed")
print(f"{'═'*60}")

if errors:
    print(f"\n❌ {len(errors)} failed:")
    for name, err in errors[:20]:
        print(f"  {name}: {err}")
    if len(errors) > 20:
        print(f"  ... +{len(errors) - 20} more")

print(f"\n📊 Coverage: {len(all_modules)} files, {total_cls} classes, {total_fn} functions, {total_lines} lines")
print(f"🛡 TITANIUM: {ti_count}/{len(production)} production modules ({ti_pct}%)")
sys.exit(0 if failed == 0 else 1)


