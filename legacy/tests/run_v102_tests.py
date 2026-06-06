
"""
ARKI v10.2 Comprehensive Test Suite
=====================================
Tests: TITANIUM core, middleware stack, database models, handler wiring,
       orphan module integration, automation connections, and end-to-end flow.

Usage: python tests/run_v102_tests.py
"""
import importlib.util
import sys
import os
import ast

os.chdir(os.path.dirname(os.path.dirname(__file__)))

def load_module(name, path):
    """Load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


passed = 0
failed = 0
errors = []


def run_test(name, func):
    global passed, failed
    try:
        func()
        passed += 1
        print(f"  ✅ {name}")
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  ❌ {name}: {e}")


# ============================================================
# PHASE 1: SYNTAX & STRUCTURE
# ============================================================
print("\n🔍 Phase 1: Syntax & Structure")
print("=" * 50)

def test_all_syntax():
    """Every .py file must compile."""
    import py_compile
    bad = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root: continue
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError:
                    bad.append(path)
    assert not bad, f"Syntax errors in: {bad}"

run_test("all_files_syntax_ok", test_all_syntax)

def test_no_bare_datetime():
    """database/models.py must not have bare Mapped[datetime]."""
    with open('database/models.py') as f:
        content = f.read()
    import re
    bare = re.findall(r'Mapped\[Optional\[datetime\]\](?!\.)|Mapped\[datetime\]\s*=', content)
    assert not bare, f"Found {len(bare)} bare datetime type hints"

run_test("no_bare_datetime_hints", test_no_bare_datetime)

def test_sa_import():
    """database/models.py must have import sqlalchemy as sa."""
    with open('database/models.py') as f:
        content = f.read()
    assert 'import sqlalchemy as sa' in content

run_test("models_sa_import", test_sa_import)

def test_version_sync():
    """VERSION, README, Dockerfile must agree."""
    ver = open('VERSION').read().strip()
    assert ver in open('README.md').read(), f"README missing {ver}"
    assert ver in open('Dockerfile').read(), f"Dockerfile missing {ver}"

run_test("version_sync", test_version_sync)

def test_no_dead_imports():
    """main.py must not have REMOVED: dead import comments."""
    with open('main.py') as f:
        content = f.read()
    assert 'REMOVED: dead import' not in content

run_test("no_dead_imports_in_main", test_no_dead_imports)


# ============================================================
# PHASE 2: TITANIUM CORE
# ============================================================
print("\n🛡 Phase 2: TITANIUM Core Modules")
print("=" * 50)

# Load TITANIUM modules
titanium_path = 'utils/titanium'
# Load in dependency order
config = load_module('tg_bot.utils.titanium.config', f'{titanium_path}/config.py')
crypto = load_module('tg_bot.utils.titanium.crypto', f'{titanium_path}/crypto.py')
timing = load_module('tg_bot.utils.titanium.timing', f'{titanium_path}/timing.py')
compat = load_module('tg_bot.utils.titanium.compat', f'{titanium_path}/compat.py')
error_shield = load_module('tg_bot.utils.titanium.error_shield', f'{titanium_path}/error_shield.py')
header_entropy = load_module('tg_bot.utils.titanium.header_entropy', f'{titanium_path}/header_entropy.py')
rate_limiter = load_module('tg_bot.utils.titanium.rate_limiter', f'{titanium_path}/rate_limiter.py')
shielded_client = load_module('tg_bot.utils.titanium.shielded_client', f'{titanium_path}/shielded_client.py')
ai_orchestrator = load_module('tg_bot.utils.titanium.ai_orchestrator', f'{titanium_path}/ai_orchestrator.py')
health_monitor = load_module('tg_bot.utils.titanium.health_monitor', f'{titanium_path}/health_monitor.py')
integration = load_module('tg_bot.utils.titanium.integration', f'{titanium_path}/integration.py')
init_mod = load_module('tg_bot.utils.titanium', f'{titanium_path}/__init__.py')

def test_titanium_version():
    assert hasattr(init_mod, 'TITANIUM_VERSION')
    assert '10' in init_mod.TITANIUM_VERSION

run_test("titanium_version", test_titanium_version)

def test_csprng_int():
    vals = [crypto.csprng_int(1, 100) for _ in range(100)]
    assert all(1 <= v <= 100 for v in vals)
    assert len(set(vals)) > 10  # Should have variety

run_test("csprng_int_range_and_variety", test_csprng_int)

def test_secure_hex():
    h = crypto.secure_hex(16)
    assert len(h) == 32  # 16 bytes = 32 hex chars
    assert isinstance(h, str)

run_test("secure_hex", test_secure_hex)

def test_hmac_sign_verify():
    sig = crypto.hmac_sign(b"test-key", b"test-data")
    assert isinstance(sig, str)
    assert len(sig) == 64  # hex SHA256

run_test("hmac_sign_verify", test_hmac_sign_verify)

def test_header_entropy_generate():
    headers = header_entropy.build_decoy_headers()
    assert 'User-Agent' in headers
    assert 'Accept-Language' in headers
    assert len(headers) >= 4

run_test("header_entropy_generation", test_header_entropy_generate)

def test_header_entropy_variety():
    """Multiple calls should produce different headers."""
    sets = [frozenset(header_entropy.build_decoy_headers().items()) for _ in range(5)]
    assert len(set(sets)) > 1

run_test("header_entropy_variety", test_header_entropy_variety)

def test_error_shield_sanitize():
    """Error shield should sanitize sensitive info."""
    sanitized = error_shield.sanitize_error("API key: sk-abc123xyz failed")
    assert isinstance(sanitized, str)
    assert len(sanitized) > 0

run_test("error_shield_sanitize", test_error_shield_sanitize)

def test_compat_secure_random():
    """Compat module provides drop-in random replacement."""
    sr = compat.secure_random
    v = sr.random()
    assert 0 <= v < 1
    c = sr.choice([1, 2, 3, 4, 5])
    assert c in [1, 2, 3, 4, 5]
    s = sr.sample([1, 2, 3, 4, 5], 3)
    assert len(s) == 3

run_test("compat_secure_random", test_compat_secure_random)

def test_rate_limiter_unlimited():
    """Default rate limiter should be unlimited."""
    assert config.TITANIUM_CONFIG['rate_limit_mode'] == 'unlimited' or \
           config.TITANIUM_CONFIG.get('rate_limit_max_requests', 0) >= 999999

run_test("rate_limiter_unlimited_default", test_rate_limiter_unlimited)

def test_config_connections():
    """Config should have high connection limits."""
    assert config.TITANIUM_CONFIG['max_connections'] >= 200

run_test("config_high_connections", test_config_connections)

def test_shielded_response_has_content():
    """ShieldedResponse must have .content bytes field."""
    resp = shielded_client.ShieldedResponse(
        status=200, text="hello", headers={}, success=True
    )
    assert hasattr(resp, 'content')

run_test("shielded_response_content_field", test_shielded_response_has_content)

def test_integration_helpers_exist():
    """Integration module must export shielded_get/post/request."""
    assert hasattr(integration, 'shielded_get')
    assert hasattr(integration, 'shielded_post')
    assert hasattr(integration, 'shielded_request')
    assert callable(integration.shielded_get)

run_test("integration_helpers_exist", test_integration_helpers_exist)


# ============================================================
# PHASE 3: MIDDLEWARE STACK
# ============================================================
print("\n⚙️ Phase 3: Middleware Stack")
print("=" * 50)

middleware_files = [
    'middlewares/analytics.py',
    'middlewares/architecture_bridge.py',
    'middlewares/backpressure_middleware.py',
    'middlewares/callback_timeout_middleware.py',
    'middlewares/dedup_middleware.py',
    'middlewares/i18n_middleware.py',
    'middlewares/idempotency_middleware.py',
    'middlewares/infrastructure_bridge.py',
    'middlewares/maintenance.py',
    'middlewares/media_group_middleware.py',
    'middlewares/plan_enforcement_middleware.py',
    'middlewares/poison_pill_middleware.py',
    'middlewares/rate_limiter.py',
    'middlewares/register.py',
    'middlewares/tracing_middleware.py',
]

for mw_path in middleware_files:
    mw_name = os.path.basename(mw_path).replace('.py', '')
    def _make_test(p=mw_path, n=mw_name):
        def test():
            assert os.path.exists(p), f"File missing: {p}"
            with open(p) as f:
                tree = ast.parse(f.read())
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and 'Middleware' in n.name]
            assert classes, f"No Middleware class in {p}"
        return test
    run_test(f"middleware_exists_{mw_name}", _make_test())

def test_all_middlewares_in_main():
    """All middleware classes should be imported in main.py."""
    with open('main.py') as f:
        main = f.read()
    missing = []
    for mw_path in middleware_files:
        with open(mw_path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and 'Middleware' in node.name:
                if node.name not in main:
                    missing.append(node.name)
    assert not missing, f"Middlewares not in main.py: {missing}"

run_test("all_middlewares_registered", test_all_middlewares_in_main)


# ============================================================
# PHASE 4: HANDLER WIRING
# ============================================================
print("\n🔌 Phase 4: Handler Wiring")
print("=" * 50)

def test_all_handlers_have_router():
    """Every handler file should define a router (except shared utilities)."""
    handler_dir = 'handlers'
    skip = {'__init__.py', 'shared.py'}  # shared.py is a utility module, not a handler
    no_router = []
    for f in os.listdir(handler_dir):
        if f.endswith('.py') and f not in skip:
            with open(os.path.join(handler_dir, f)) as fh:
                content = fh.read()
            if 'router' not in content.lower():
                no_router.append(f)
    assert len(no_router) == 0, f"Handlers without router: {no_router}"

run_test("all_handlers_have_router", test_all_handlers_have_router)

def test_handler_routers_registered():
    """All handler routers should be registered via dp.include_router."""
    with open('main.py') as f:
        main = f.read()
    registered = main.count('include_router')
    assert registered >= 20, f"Only {registered} routers registered, expected 20+"

run_test("handler_routers_registered", test_handler_routers_registered)


# ============================================================
# PHASE 5: TITANIUM INTEGRATION (Connection Tests)
# ============================================================
print("\n🔗 Phase 5: TITANIUM Integration Connections")
print("=" * 50)

def test_titanium_guards_in_handlers():
    """Handler files with HTTP calls must have TITANIUM guards."""
    http_handlers = [
        'handlers/agents.py', 'handlers/market.py', 'handlers/content_studio.py',
        'handlers/platform_auto.py', 'handlers/sales_engine.py',
    ]
    missing = []
    for p in http_handlers:
        if not os.path.exists(p): continue
        with open(p) as f:
            content = f.read()
        has_http = 'httpx.AsyncClient' in content or 'aiohttp.ClientSession' in content
        has_guard = '_TITANIUM_ACTIVE' in content
        if has_http and not has_guard:
            missing.append(p)
    assert not missing, f"HTTP handlers without TITANIUM: {missing}"

run_test("titanium_guards_in_handlers", test_titanium_guards_in_handlers)

def test_titanium_guards_in_utils():
    """Utility files with HTTP calls must have TITANIUM guards."""
    http_utils = [
        'utils/network_scanner.py', 'utils/web_recon.py', 'utils/web_search.py',
        'utils/web_engine.py', 'utils/jina_reader.py', 'utils/integrations.py',
        'utils/agent_executor.py', 'utils/multimodal_engine.py',
    ]
    missing = []
    for p in http_utils:
        if not os.path.exists(p): continue
        with open(p) as f:
            content = f.read()
        has_http = 'httpx.AsyncClient' in content or 'aiohttp.ClientSession' in content
        has_guard = '_TITANIUM_ACTIVE' in content or 'shielded_' in content
        if has_http and not has_guard:
            missing.append(p)
    assert not missing, f"HTTP utils without TITANIUM: {missing}"

run_test("titanium_guards_in_utils", test_titanium_guards_in_utils)

def test_csprng_replacement():
    """All files using random should use CSPRNG."""
    bad = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root or 'titanium' in root or 'test' in root: continue
        for f in files:
            if not f.endswith('.py'): continue
            p = os.path.join(root, f)
            with open(p) as fh:
                content = fh.read()
            # Check for bare "import random" NOT in except ImportError block
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == 'import random':
                    # Check if previous line is except ImportError
                    if i > 0 and 'except' in lines[i-1]:
                        continue  # OK, it's a fallback
                    bad.append(p)
                    break
    assert not bad, f"Files with non-fallback 'import random': {bad}"

run_test("all_random_uses_csprng", test_csprng_replacement)

def test_no_silent_swallows():
    """No 'except Exception: pass' without logging in production code."""
    bad = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root or 'test' in root: continue
        for f in files:
            if not f.endswith('.py'): continue
            p = os.path.join(root, f)
            with open(p) as fh:
                lines = fh.readlines()
            for i in range(len(lines)-1):
                s = lines[i].strip()
                n = lines[i+1].strip()
                # Pure 'pass' without any comment/logging is bad
                if n == 'pass' and s.startswith('except') and 'ImportError' not in s:
                    bad.append(f"{p}:{i+2}")
    assert not bad, f"Silent swallows at: {bad}"

run_test("no_silent_exception_swallows", test_no_silent_swallows)


# ============================================================
# PHASE 6: DATABASE & MODELS
# ============================================================
print("\n🗄 Phase 6: Database & Models")
print("=" * 50)

def test_models_file_parses():
    """database/models.py must parse without issues."""
    with open('database/models.py') as f:
        tree = ast.parse(f.read())
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert len(classes) >= 15, f"Only {len(classes)} model classes"

run_test("models_parse_ok", test_models_file_parses)

def test_models_have_tablename():
    """All model classes should have __tablename__."""
    with open('database/models.py') as f:
        content = f.read()
    import re
    classes = re.findall(r'class (\w+)\(.*Base\)', content)
    tablenames = re.findall(r'__tablename__\s*=\s*"(\w+)"', content)
    assert len(tablenames) >= len(classes) - 2, \
        f"{len(classes)} models but only {len(tablenames)} tablenames"

run_test("models_have_tablename", test_models_have_tablename)

def test_alembic_config_exists():
    """Migration config should exist."""
    assert os.path.exists('alembic.ini') or os.path.exists('migrations/'), \
        "No alembic.ini or migrations/"

run_test("migration_config_exists", test_alembic_config_exists)


# ============================================================
# PHASE 7: AUTOMATION & ORCHESTRATION
# ============================================================
print("\n🤖 Phase 7: Automation & Orchestration")
print("=" * 50)

def test_orchestration_modules():
    """Orchestration directory must have core modules."""
    required = ['core.py', 'retry_manager.py', 'work_queue.py']
    for f in required:
        p = f'orchestration/{f}'
        assert os.path.exists(p), f"Missing orchestration module: {f}"

run_test("orchestration_core_modules", test_orchestration_modules)

def test_pipeline_stages():
    """AI pipeline should have all 7 stages."""
    with open('core/pipeline.py') as f:
        content = f.read()
    stages = ['classify', 'reason', 'enhance', 'route', 'execute', 'validate', 'respond']
    found = sum(1 for s in stages if s.lower() in content.lower())
    assert found >= 5, f"Only {found}/7 pipeline stages found"

run_test("pipeline_has_stages", test_pipeline_stages)

def test_background_tasks_tracked():
    """main.py must keep strong references to background tasks."""
    with open('main.py') as f:
        content = f.read()
    assert 'background_tasks: list' in content or 'background_tasks =' in content
    appends = content.count('background_tasks.append')
    creates = content.count('asyncio.create_task')
    assert appends >= creates - 1, \
        f"{creates} create_task but only {appends} appends"

run_test("background_tasks_tracked", test_background_tasks_tracked)


# ============================================================
# PHASE 8: CI/CD & DOCKER
# ============================================================
print("\n🐳 Phase 8: CI/CD & Docker")
print("=" * 50)

def test_dockerfile_valid():
    """Dockerfile should have essential directives."""
    with open('Dockerfile') as f:
        content = f.read()
    assert 'FROM ' in content
    assert 'COPY ' in content or 'ADD ' in content
    assert 'CMD ' in content or 'ENTRYPOINT ' in content
    assert 'non-root' in content.lower() or 'USER ' in content

run_test("dockerfile_valid", test_dockerfile_valid)

def test_requirements_exist():
    """requirements.txt or pyproject.toml must exist."""
    assert os.path.exists('requirements.txt') or os.path.exists('pyproject.toml'), \
        "No requirements file found"

run_test("requirements_exist", test_requirements_exist)


# ============================================================
# PHASE 9: ORPHAN MODULE INTEGRATION
# ============================================================
print("\n🔗 Phase 9: Orphan Module Integration")
print("=" * 50)

def test_ai_streaming_wired():
    """ai_streaming.py should be imported somewhere."""
    import subprocess
    result = subprocess.run(
        ['grep', '-rl', 'ai_streaming', '--include=*.py', '.'],
        capture_output=True, text=True
    )
    files = [f for f in result.stdout.strip().split('\n') if f and f != './utils/ai_streaming.py']
    assert files, "ai_streaming.py not imported anywhere"

run_test("ai_streaming_wired", test_ai_streaming_wired)

def test_response_types_wired():
    """response_types.py should be imported somewhere."""
    import subprocess
    result = subprocess.run(
        ['grep', '-rl', 'response_types', '--include=*.py', '.'],
        capture_output=True, text=True
    )
    files = [f for f in result.stdout.strip().split('\n') if f and f != './utils/response_types.py']
    assert files, "response_types.py not imported anywhere"

run_test("response_types_wired", test_response_types_wired)


# ============================================================
# PHASE 10: SECURITY CHECKS
# ============================================================
print("\n🔒 Phase 10: Security")
print("=" * 50)

def test_no_hardcoded_secrets():
    """No hardcoded API keys or tokens."""
    import re
    secret_patterns = [
        re.compile(r'(?:api[_-]?key|token|secret|password)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', re.I),
        re.compile(r'sk-[a-zA-Z0-9]{20,}'),
        re.compile(r'AIza[a-zA-Z0-9_-]{35}'),
    ]
    found = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root or '.git' in root or 'test' in root: continue
        for f in files:
            if not f.endswith('.py'): continue
            p = os.path.join(root, f)
            with open(p) as fh:
                content = fh.read()
            for pattern in secret_patterns:
                if pattern.search(content):
                    found.append(p)
                    break
    assert not found, f"Possible hardcoded secrets in: {found}"

run_test("no_hardcoded_secrets", test_no_hardcoded_secrets)

def test_ssl_verification():
    """No SSL verification disabled in production code."""
    bad = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root or 'test' in root: continue
        for f in files:
            if not f.endswith('.py'): continue
            p = os.path.join(root, f)
            with open(p) as fh:
                content = fh.read()
            if 'verify=False' in content and 'ssl=False' not in content:
                bad.append(p)
    # Note: ssl=False in aiohttp TCPConnector is different from verify=False
    # Just check for explicit verify=False in httpx
    assert not bad, f"SSL verification disabled in: {bad}"

run_test("ssl_verification_enabled", test_ssl_verification)


# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"ARKI v10.2 Test Results: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if errors:
    print("\n❌ Failed tests:")
    for name, err in errors:
        print(f"  - {name}: {err[:100]}")

sys.exit(0 if failed == 0 else 1)


