
"""
TITANIUM v29.0 Test Runner
===========================
Runs all tests using direct module loading (bypasses tg_bot package imports).
"""
import importlib.util
import sys
import os


import logging
logger = logging.getLogger(__name__)
os.chdir(os.path.dirname(os.path.dirname(__file__)))

def load_module(name, path):
    """Load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Pre-load titanium modules into sys.modules so cross-imports work
TITANIUM_MODULES = {
    "tg_bot": type(sys)("tg_bot"),
    "arki_project.utils": type(sys)("arki_project.utils"),
    "arki_project.utils.titanium": None,  # will be loaded
}

# Create stub packages
for name, mod in TITANIUM_MODULES.items():
    if mod is not None:
        sys.modules[name] = mod

# Load actual titanium modules
module_files = [
    ("arki_project.utils.titanium.crypto", "utils/titanium/crypto.py"),
    ("arki_project.utils.titanium.compat", "utils/titanium/compat.py"),
    ("arki_project.utils.titanium.header_entropy", "utils/titanium/header_entropy.py"),
    ("arki_project.utils.titanium.timing", "utils/titanium/timing.py"),
    ("arki_project.utils.titanium.error_shield", "utils/titanium/error_shield.py"),
    ("arki_project.utils.titanium.config", "utils/titanium/config.py"),
    ("arki_project.utils.titanium.rate_limiter", "utils/titanium/rate_limiter.py"),
]

for name, path in module_files:
    try:
        load_module(name, path)
    except Exception as e:
        logger.info(f"⚠️  Could not load {name}: {e}")

# Load shielded_client (needs crypto)
try:
    load_module("arki_project.utils.titanium.shielded_client", "utils/titanium/shielded_client.py")
except Exception as e:
    logger.info(f"⚠️  Could not load shielded_client: {e}")

# Load integration (needs shielded_client)
try:
    load_module("arki_project.utils.titanium.integration", "utils/titanium/integration.py")
except Exception as e:
    logger.info(f"⚠️  Could not load integration: {e}")

# Load __init__
try:
    load_module("arki_project.utils.titanium", "utils/titanium/__init__.py")
except Exception as e:
    logger.info(f"⚠️  Could not load titanium __init__: {e}")


# ═══ TESTS ═══

passed = 0
failed = 0
errors = []

def run_test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        logger.info(f"  ✅ {name}")
    except Exception as e:
        failed += 1
        errors.append((name, e))
        logger.info(f"  ❌ {name}: {e}")


# ── Crypto Tests ──
logger.info("\n🔐 Crypto Tests:")
crypto = sys.modules["arki_project.utils.titanium.crypto"]

def test_csprng_int_range():
    for _ in range(1000):
        val = crypto.csprng_int(0, 10)
        assert 0 <= val <= 10

def test_csprng_float_range():
    for _ in range(500):
        val = crypto.csprng_float()
        assert 0.0 <= val < 1.0

def test_csprng_choice():
    items = ["a", "b", "c"]
    for _ in range(100):
        assert crypto.csprng_choice(items) in items

def test_csprng_weighted():
    items = ["heavy", "light"]
    weights = [100.0, 0.001]
    picks = [crypto.csprng_weighted_choice(items, weights) for _ in range(200)]
    assert picks.count("heavy") > 150

def test_request_ids_unique():
    ids = {crypto.secure_request_id() for _ in range(100)}
    assert len(ids) == 100

def test_hmac_sign_verify():
    sig = crypto.hmac_sign(b"secret_key", b"test message")
    assert crypto.hmac_verify(b"secret_key", b"test message", sig)
    assert not crypto.hmac_verify(b"wrong_key", b"test message", sig)
    assert not crypto.hmac_verify(b"secret_key", b"wrong data", sig)

run_test("csprng_int_range", test_csprng_int_range)
run_test("csprng_float_range", test_csprng_float_range)
run_test("csprng_choice", test_csprng_choice)
run_test("csprng_weighted", test_csprng_weighted)
run_test("request_ids_unique", test_request_ids_unique)
run_test("hmac_sign_verify", test_hmac_sign_verify)


# ── Compat Tests ──
logger.info("\n🔄 Compat Tests:")
compat = sys.modules["arki_project.utils.titanium.compat"]
sr = compat.secure_random

def test_compat_randint():
    for _ in range(500):
        assert 1 <= sr.randint(1, 100) <= 100

def test_compat_random():
    for _ in range(500):
        val = sr.random()
        assert 0.0 <= val < 1.0

def test_compat_uniform():
    for _ in range(500):
        val = sr.uniform(10.0, 20.0)
        assert 10.0 <= val <= 20.0

def test_compat_choice():
    items = [1, 2, 3, 4, 5]
    for _ in range(100):
        assert sr.choice(items) in items

def test_compat_shuffle():
    items = list(range(20))
    original = items.copy()
    sr.shuffle(items)
    assert sorted(items) == sorted(original)

def test_compat_sample():
    items = list(range(100))
    s = sr.sample(items, 10)
    assert len(s) == 10 and len(set(s)) == 10

def test_compat_gauss():
    vals = [sr.gauss(0, 1) for _ in range(1000)]
    mean = sum(vals) / len(vals)
    assert -0.5 < mean < 0.5

run_test("compat_randint", test_compat_randint)
run_test("compat_random", test_compat_random)
run_test("compat_uniform", test_compat_uniform)
run_test("compat_choice", test_compat_choice)
run_test("compat_shuffle", test_compat_shuffle)
run_test("compat_sample", test_compat_sample)
run_test("compat_gauss", test_compat_gauss)


# ── Header Entropy Tests ──
logger.info("\n🎭 Header Entropy Tests:")
he = sys.modules["arki_project.utils.titanium.header_entropy"]

def test_headers_required_fields():
    for _ in range(100):
        h = he.build_decoy_headers()
        assert "Accept-Language" in h
        assert "Accept-Encoding" in h
        assert "Connection" in h

def test_headers_entropy():
    samples = [str(he.build_decoy_headers()) for _ in range(50)]
    assert len(set(samples)) > 30

def test_ua_rotation():
    uas = set()
    for _ in range(200):
        h = he.build_decoy_headers()
        if "User-Agent" in h:
            uas.add(h["User-Agent"])
    assert len(uas) > 5

def test_no_empty_headers():
    for _ in range(100):
        for k, v in he.build_decoy_headers().items():
            assert isinstance(k, str) and len(k) > 0
            assert isinstance(v, str) and len(v) > 0

run_test("headers_required_fields", test_headers_required_fields)
run_test("headers_entropy", test_headers_entropy)
run_test("ua_rotation", test_ua_rotation)
run_test("no_empty_headers", test_no_empty_headers)


# ── Rate Limiter Tests ──
logger.info("\n⚡ Rate Limiter Tests:")
rl_mod = sys.modules["arki_project.utils.titanium.rate_limiter"]

def test_unlimited_mode():
    limiter = rl_mod.TitaniumRateLimiter()
    for i in range(500):
        assert limiter.check(f"user:{i % 10}") is True

def test_throughput_tracking():
    limiter = rl_mod.TitaniumRateLimiter()
    for _ in range(50):
        limiter.check("user:1")
    assert limiter.throughput("user:1") == 50

def test_remaining_unlimited():
    limiter = rl_mod.TitaniumRateLimiter()
    assert limiter.remaining("user:1") == 999999

def test_stats():
    limiter = rl_mod.TitaniumRateLimiter()
    for _ in range(10):
        limiter.check("user:1")
    stats = limiter.stats
    assert stats["mode"] == "unlimited"
    assert stats["total_checks"] == 10

run_test("unlimited_mode", test_unlimited_mode)
run_test("throughput_tracking", test_throughput_tracking)
run_test("remaining_unlimited", test_remaining_unlimited)
run_test("stats", test_stats)


# ── ShieldedClient Tests ──
logger.info("\n🛡️ ShieldedClient Tests:")
sc = sys.modules["arki_project.utils.titanium.shielded_client"]

def test_circuit_breaker_initial():
    cb = sc.CircuitBreaker(failure_threshold=3)
    assert not cb.is_open("test.com")

def test_circuit_breaker_opens():
    cb = sc.CircuitBreaker(failure_threshold=3, reset_timeout=10.0)
    for _ in range(3):
        cb.record_failure("bad.com")
    assert cb.is_open("bad.com")
    assert not cb.is_open("good.com")

def test_circuit_breaker_success_resets():
    cb = sc.CircuitBreaker(failure_threshold=3)
    cb.record_failure("test.com")
    cb.record_failure("test.com")
    cb.record_success("test.com")
    cb.record_failure("test.com")
    assert not cb.is_open("test.com")

def test_deduplicator():
    dd = sc.RequestDeduplicator(window_ms=1000)
    assert dd.get_pending("GET", "http://x.com/a", None) is None
    fut = dd.set_pending("GET", "http://x.com/a", None)
    assert fut is not None
    assert dd.get_pending("GET", "http://x.com/a", None) is not None
    assert dd.get_pending("GET", "http://x.com/b", None) is None

def test_shielded_response_json():
    resp = sc.ShieldedResponse(status=200, text='{"key": "value"}', success=True)
    assert resp.json() == {"key": "value"}

def test_shielded_response_invalid_json():
    resp = sc.ShieldedResponse(status=200, text='not json', success=True)
    assert resp.json() == {}

def test_pool_singleton():
    p1 = sc.get_shielded_pool(200)
    p2 = sc.get_shielded_pool(200)
    assert p1 is p2

def test_pool_stats():
    pool = sc.get_shielded_pool()
    stats = pool.stats
    assert "requests" in stats
    assert "errors" in stats
    assert "max_connections" in stats

run_test("circuit_breaker_initial", test_circuit_breaker_initial)
run_test("circuit_breaker_opens", test_circuit_breaker_opens)
run_test("circuit_breaker_success_resets", test_circuit_breaker_success_resets)
run_test("deduplicator", test_deduplicator)
run_test("shielded_response_json", test_shielded_response_json)
run_test("shielded_response_invalid_json", test_shielded_response_invalid_json)
run_test("pool_singleton", test_pool_singleton)
run_test("pool_stats", test_pool_stats)


# ── Integration Module Tests ──
logger.info("\n🔗 Integration Module Tests:")
integ = sys.modules["arki_project.utils.titanium.integration"]

def test_get_secure_random():
    sr = integ.get_secure_random()
    # get_secure_random returns a drop-in random module replacement
    assert hasattr(sr, 'randint')
    assert hasattr(sr, 'random')
    assert hasattr(sr, 'choice')
    for _ in range(100):
        val = sr.random()
        assert 0.0 <= val < 1.0

def test_shielded_funcs_exist():
    assert callable(integ.shielded_get)
    assert callable(integ.shielded_post)
    assert callable(integ.shielded_request)

import asyncio

def test_shielded_get_unreachable():
    async def _run():
        resp = await integ.shielded_get("http://127.0.0.1:1/test", timeout=0.5)
        assert resp.success is False
        assert hasattr(resp, 'status')
    asyncio.run(_run())

def test_shielded_post_unreachable():
    async def _run():
        resp = await integ.shielded_post("http://127.0.0.1:1/test", json_data={"a": 1}, timeout=0.5)
        assert resp.success is False
    asyncio.run(_run())

run_test("get_secure_random", test_get_secure_random)
run_test("shielded_funcs_exist", test_shielded_funcs_exist)
run_test("shielded_get_unreachable", test_shielded_get_unreachable)
run_test("shielded_post_unreachable", test_shielded_post_unreachable)


# ── Config Tests ──
logger.info("\n⚙️ Config Tests:")
cfg = sys.modules["arki_project.utils.titanium.config"]

def test_config_version():
    assert cfg.TITANIUM_CONFIG["version"] == "10.1.0"

def test_config_unlimited():
    assert cfg.TITANIUM_CONFIG["enforce_limits"] is False

def test_config_connections():
    assert cfg.TITANIUM_CONFIG["max_connections"] >= 200  # v10.2: 500

run_test("config_version", test_config_version)
run_test("config_unlimited", test_config_unlimited)
run_test("config_connections", test_config_connections)


# ── Boot Tests ──
logger.info("\n🚀 Boot Tests:")
ti = sys.modules["arki_project.utils.titanium"]

def test_version():
    assert ti.TITANIUM_VERSION == "26.1.0"

def test_codename():
    assert ti.TITANIUM_CODENAME == "OMEGA SHIELD"

def test_boot_shutdown():
    async def _run():
        await ti.boot_titanium()
        await ti.shutdown_titanium()
    asyncio.run(_run())

run_test("version", test_version)
run_test("codename", test_codename)
run_test("boot_shutdown", test_boot_shutdown)


# ═══ SUMMARY ═══
logger.info(f"\n{'='*50}")
logger.info(f"TITANIUM v29.0 Test Results: {passed} passed, {failed} failed")
logger.info(f"{'='*50}")

if errors:
    logger.info("\n❌ Failed tests:")
    for name, e in errors:
        logger.info(f"  {name}: {e}")

sys.exit(0 if failed == 0 else 1)


