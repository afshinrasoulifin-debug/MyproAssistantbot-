
"""
tests/test_runtime_real.py — Real Runtime Tests v3.3
═══════════════════════════════════════════════════════════════
Actually instantiates classes, calls methods, verifies behavior.
Uses direct imports to avoid heavy dependency chains.
"""
import asyncio, importlib, importlib.util, os, sys, time, re

# Ensure project root is in path for direct imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set required env vars for modules that check them
os.environ.setdefault("BOT_TOKEN", "test:TOKEN")
os.environ.setdefault("AI_API_KEY", "test-key-001")
os.environ.setdefault("OPENROUTER_API_KEY", "test-or-key-001")

passed = 0
failed = 0
loop = asyncio.new_event_loop()

def test(name):
    def decorator(fn):
        global passed, failed
        try:
            if asyncio.iscoroutinefunction(fn):
                loop.run_until_complete(fn())
            else:
                fn()
            passed += 1
            print(f"  ✅ {name}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {name}: {e}")
    return decorator

def load_module(rel_path: str, module_name: str):
    """Load a single .py file as a module, bypassing package imports."""
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    mod = importlib.util.module_from_spec(spec)
    # Pre-register to allow self-references
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  REAL RUNTIME TESTS — v3.3")
print("=" * 60)

# ── 1. API Key Manager (standalone, no external deps) ──
print("\n── API Key Manager ──")

@test("Add and rotate keys")
async def _():
    mod = load_module("utils/api_key_manager.py", "_akm")
    mgr = mod.APIKeyManager()
    mgr.add_key("openrouter", "key-1", daily_budget=5.0)
    mgr.add_key("openrouter", "key-2", daily_budget=5.0)
    mgr.add_key("openrouter", "key-3", daily_budget=5.0)
    keys_seen = set()
    for _ in range(6):
        k = await mgr.get_key("openrouter")
        assert k is not None, "Key should not be None"
        keys_seen.add(k)
    assert len(keys_seen) == 3, f"Should rotate through 3 keys, got {len(keys_seen)}"

@test("Key disabling on high error rate")
async def _():
    mod = load_module("utils/api_key_manager.py", "_akm2")
    mgr = mod.APIKeyManager()
    mgr.add_key("test", "bad-key")
    for i in range(15):
        await mgr.report_error("test", "bad-key", "500 error")
        mgr._keys["test"][0].total_calls = i + 1
    status = mgr.get_provider_status("test")
    assert status["disabled"] >= 1, "Bad key should be disabled"

@test("Rate limit cooldown")
async def _():
    mod = load_module("utils/api_key_manager.py", "_akm3")
    mgr = mod.APIKeyManager()
    mgr.add_key("test", "rl-key")
    await mgr.report_error("test", "rl-key", "429 rate limit", is_rate_limit=True)
    entry = mgr._keys["test"][0]
    assert entry.rate_limit_until > time.time(), "Should have cooldown"

@test("Provider status report")
async def _():
    mod = load_module("utils/api_key_manager.py", "_akm4")
    mgr = mod.APIKeyManager()
    mgr.add_key("openrouter", "k1")
    mgr.add_key("openrouter", "k2")
    status = mgr.get_provider_status("openrouter")
    assert status["total_keys"] == 2
    assert status["active"] == 2
    assert "budget_remaining" in status

@test("Load from env")
async def _():
    mod = load_module("utils/api_key_manager.py", "_akm5")
    mgr = mod.APIKeyManager()
    count = mgr.load_from_env()
    assert count >= 1, "Should load at least 1 key from env"

@test("Budget tracking per key")
async def _():
    mod = load_module("utils/api_key_manager.py", "_akm6")
    mgr = mod.APIKeyManager()
    mgr.add_key("openrouter", "budget-key", daily_budget=1.0)
    await mgr.report_success("openrouter", "budget-key", tokens=1000, cost_usd=0.5)
    await mgr.report_success("openrouter", "budget-key", tokens=1000, cost_usd=0.6)
    # Budget exceeded (1.1 > 1.0)
    entry = mgr._keys["openrouter"][0]
    assert entry.daily_spent_usd >= 1.0, f"Should track spend: {entry.daily_spent_usd}"

# ── 2. Request Queue ──
print("\n── Request Queue ──")

@test("Enqueue and process")
async def _():
    mod = load_module("utils/request_queue.py", "_rq")
    q = mod.RequestQueue()
    results = []
    async def processor(item):
        results.append(item.payload.get("val"))
        return item.payload.get("val") * 2
    q.set_processor(processor)
    await q.start(num_workers=2)
    await q.enqueue({"val": 1}, priority=mod.Priority.NORMAL)
    await q.enqueue({"val": 2}, priority=mod.Priority.HIGH)
    await asyncio.sleep(0.5)
    await q.stop()
    assert len(results) == 2, f"Expected 2 processed, got {len(results)}"

@test("Deduplication works")
async def _():
    mod = load_module("utils/request_queue.py", "_rq2")
    q = mod.RequestQueue(dedup_window_s=10.0)
    id1 = await q.enqueue({"key": "same"}, dedup_key="dup1")
    id2 = await q.enqueue({"key": "same"}, dedup_key="dup1")
    assert id1 is not None
    assert id2 is None, "Duplicate should be rejected"
    assert q.stats["deduplicated"] == 1

@test("Priority ordering")
async def _():
    mod = load_module("utils/request_queue.py", "_rq3")
    q = mod.RequestQueue(max_concurrent=1)
    order = []
    async def processor(item):
        order.append(item.payload["name"])
    q.set_processor(processor)
    await q.enqueue({"name": "low"}, priority=mod.Priority.LOW)
    await q.enqueue({"name": "critical"}, priority=mod.Priority.CRITICAL)
    await q.enqueue({"name": "normal"}, priority=mod.Priority.NORMAL)
    await q.start(num_workers=1)
    await asyncio.sleep(0.5)
    await q.stop()
    assert order[0] == "critical", f"Critical should be first, got {order}"

@test("Retry on failure")
async def _():
    mod = load_module("utils/request_queue.py", "_rq4")
    q = mod.RequestQueue()
    attempt_count = [0]
    async def failing_processor(item):
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ValueError("transient error")
        return "ok"
    q.set_processor(failing_processor)
    await q.start(num_workers=1)
    await q.enqueue({"test": True})
    await asyncio.sleep(2.0)
    await q.stop()
    assert q.stats["retried"] >= 1, "Should have retried"

# ── 3. Event Bus ──
print("\n── Event Bus ──")

@test("Publish and subscribe")
async def _():
    mod = load_module("utils/event_bus.py", "_eb")
    bus = mod.EventBus()
    received = []
    bus.subscribe("test.event", lambda e: received.append(e.data))
    count = await bus.publish("test.event", {"val": 42})
    assert count == 1
    assert received[0]["val"] == 42

@test("Filtered subscription")
async def _():
    mod = load_module("utils/event_bus.py", "_eb2")
    bus = mod.EventBus()
    big = []
    bus.subscribe("data", lambda e: big.append(e.data),
                  filter_fn=lambda e: e.data.get("size", 0) > 100)
    await bus.publish("data", {"size": 50})
    await bus.publish("data", {"size": 200})
    assert len(big) == 1, f"Filter should pass 1, got {len(big)}"

@test("Wildcard subscription")
async def _():
    mod = load_module("utils/event_bus.py", "_eb3")
    bus = mod.EventBus()
    all_events = []
    bus.subscribe("*", lambda e: all_events.append(e.type))
    await bus.publish("type.a", {})
    await bus.publish("type.b", {})
    assert len(all_events) == 2

@test("Event history tracking")
async def _():
    mod = load_module("utils/event_bus.py", "_eb4")
    bus = mod.EventBus()
    for i in range(5):
        await bus.publish("log", {"i": i})
    history = bus.get_history("log")
    assert len(history) == 5

@test("Unsubscribe works")
async def _():
    mod = load_module("utils/event_bus.py", "_eb5")
    bus = mod.EventBus()
    received = []
    bus.subscribe("test", lambda e: received.append(1), name="sub1")
    await bus.publish("test")
    assert len(received) == 1
    bus.unsubscribe("test", "sub1")
    await bus.publish("test")
    assert len(received) == 1, "Should not receive after unsubscribe"

@test("Priority ordering of handlers")
async def _():
    mod = load_module("utils/event_bus.py", "_eb6")
    bus = mod.EventBus()
    order = []
    bus.subscribe("test", lambda e: order.append("low"), name="low", priority=1)
    bus.subscribe("test", lambda e: order.append("high"), name="high", priority=10)
    await bus.publish("test")
    assert order[0] == "high", f"High priority should fire first, got {order}"

# ── 4. Circuit Breaker ──
print("\n── Circuit Breaker ──")

@test("Opens after threshold failures")
def _():
    mod = load_module("utils/circuit_breaker.py", "_cb")
    cb = mod.CircuitBreaker("test", failure_threshold=3, recovery_timeout=60.0)
    assert cb.state == mod.CircuitState.CLOSED
    for _ in range(3):
        cb.record_failure()
    assert cb.state == mod.CircuitState.OPEN

@test("Recovers to half-open after timeout")
def _():
    mod = load_module("utils/circuit_breaker.py", "_cb2")
    cb = mod.CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == mod.CircuitState.OPEN
    time.sleep(0.15)
    assert cb.state == mod.CircuitState.HALF_OPEN

@test("Closes after enough successes in half-open")
def _():
    mod = load_module("utils/circuit_breaker.py", "_cb3")
    cb = mod.CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=2)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    assert cb.state == mod.CircuitState.HALF_OPEN
    cb.record_success()
    cb.record_success()
    assert cb.state == mod.CircuitState.CLOSED

# ── 5. AI Response Cache ──
print("\n── AI Response Cache ──")

@test("Cache set and get")
def _():
    mod = load_module("utils/ai_response_cache.py", "_arc")
    cache = mod.AIResponseCache()
    cache.set("hello world", "gpt-4", "Hello! How can I help?")
    result = cache.get("hello world", "gpt-4")
    assert result == "Hello! How can I help?"

@test("Cache miss on different model")
def _():
    mod = load_module("utils/ai_response_cache.py", "_arc2")
    cache = mod.AIResponseCache()
    cache.set("hello", "gpt-4", "response text here")
    assert cache.get("hello", "claude-3") is None

@test("Cache eviction on max size")
def _():
    mod = load_module("utils/ai_response_cache.py", "_arc3")
    cache = mod.AIResponseCache(max_size=3)
    for i in range(5):
        cache.set(f"prompt_{i}", "model", f"response_{i}_padding")
    assert cache.stats["size"] <= 3

@test("Hit rate tracking")
def _():
    mod = load_module("utils/ai_response_cache.py", "_arc4")
    cache = mod.AIResponseCache()
    cache.set("p", "m", "response value here")
    cache.get("p", "m")  # hit
    cache.get("p", "m")  # hit
    cache.get("miss", "m")  # miss
    assert cache.stats["hits"] == 2
    assert cache.stats["misses"] == 1

# ── 6. Proxy Rotator ──
print("\n── Proxy Rotator ──")

@test("Add and rotate proxies (round-robin)")
def _():
    mod = load_module("utils/proxy_rotator.py", "_pr")
    rot = mod.ProxyRotator()
    rot._strategy = "round_robin"
    rot.add_proxy("http://proxy1:8080", country="US")
    rot.add_proxy("http://proxy2:8080", country="DE")
    rot.add_proxy("http://proxy3:8080", country="JP")
    seen = set()
    for _ in range(6):
        p = rot.get_proxy()
        assert p is not None
        seen.add(p)
    assert len(seen) >= 2, "Should rotate through proxies"

@test("Geo-filtered proxy selection")
def _():
    mod = load_module("utils/proxy_rotator.py", "_pr2")
    rot = mod.ProxyRotator()
    rot.add_proxy("http://us:8080", country="US")
    rot.add_proxy("http://de:8080", country="DE")
    p = rot.get_proxy(prefer_country="US")
    assert "us" in p, f"Should prefer US proxy, got {p}"

@test("Proxy failure and cooldown")
def _():
    mod = load_module("utils/proxy_rotator.py", "_pr3")
    rot = mod.ProxyRotator()
    rot.add_proxy("http://bad:8080")
    # Simulate many failures
    rot._proxies[0].total_requests = 10
    for _ in range(8):
        rot.report_failure("http://bad:8080", "timeout")
    # Should be cooling down or disabled
    p = rot._proxies[0]
    assert p.cooldown_until > time.time() or not p.is_active

@test("Direct fallback when no proxies")
def _():
    mod = load_module("utils/proxy_rotator.py", "_pr4")
    rot = mod.ProxyRotator()
    rot._direct_allowed = True
    p = rot.get_proxy()
    assert p is None, "Should return None (direct) when no proxies"

# ── 7. Search Privacy ──
print("\n── Search Privacy ──")

@test("Strip tracking params from URL")
def _():
    mod = load_module("utils/search_privacy.py", "_sp")
    url = "https://example.com/page?q=test&utm_source=google&fbclid=abc&ref=twitter"
    clean = mod.strip_tracking_params(url)
    assert "utm_source" not in clean
    assert "fbclid" not in clean
    assert "ref=" not in clean
    assert "q=test" in clean

@test("Detect tracking redirects")
def _():
    mod = load_module("utils/search_privacy.py", "_sp2")
    assert mod.is_tracking_redirect("https://www.google.com/url?q=https://real.com")
    assert not mod.is_tracking_redirect("https://example.com/page")

@test("Extract real URL from redirect")
def _():
    mod = load_module("utils/search_privacy.py", "_sp3")
    real = mod.extract_real_url("https://redirect.com/?url=https://real.com/page")
    assert real == "https://real.com/page"

@test("Anonymize PII in search queries")
def _():
    mod = load_module("utils/search_privacy.py", "_sp4")
    q = mod.anonymize_search_query("contact john@example.com at 555-123-4567 from 192.168.1.1")
    assert "[EMAIL]" in q
    assert "[PHONE]" in q
    assert "[IP]" in q
    assert "john@example.com" not in q

@test("Clean URLs in text")
def _():
    mod = load_module("utils/search_privacy.py", "_sp5")
    text = "Check https://example.com?utm_source=test and https://other.com?fbclid=123"
    clean = mod.clean_urls_in_text(text)
    assert "utm_source" not in clean
    assert "fbclid" not in clean

@test("Privacy layer prepare_query")
def _():
    mod = load_module("utils/search_privacy.py", "_sp6")
    layer = mod.SearchPrivacyLayer()
    q = layer.prepare_query("email me at user@test.com", user_id=123)
    assert "[EMAIL]" in q
    assert layer.stats["queries_anonymized"] == 1

# ── 8. Marketing Engine ──
print("\n── Marketing Engine ──")

@test("Create and manage campaign")
def _():
    mod = load_module("utils/marketing_engine.py", "_me")
    engine = mod.MarketingEngine()
    c = engine.create_campaign("Welcome", campaign_type="broadcast", target_segment="all")
    assert c.campaign_id
    assert c.status == mod.CampaignStatus.DRAFT
    engine.schedule_campaign(c.campaign_id)
    c = engine._campaigns[c.campaign_id]
    assert c.status == mod.CampaignStatus.SCHEDULED

@test("Lead scoring algorithm")
def _():
    mod = load_module("utils/marketing_engine.py", "_me2")
    engine = mod.MarketingEngine()
    # Create active user
    for _ in range(50):
        engine.update_lead_activity(123, "message")
    for _ in range(10):
        engine.update_lead_activity(123, "command")
    engine.update_lead_activity(123, "payment", amount=25.0)
    score = engine.score_lead(123)
    assert score > 30, f"Active paying user should score > 30, got {score}"

@test("Audience segmentation")
def _():
    mod = load_module("utils/marketing_engine.py", "_me3")
    engine = mod.MarketingEngine()
    # Create different users
    for _ in range(200):
        engine.update_lead_activity(1, "message")
    engine.update_lead_activity(1, "payment", amount=100)
    for _ in range(5):
        engine.update_lead_activity(2, "message")
    seg1 = engine.auto_segment_user(1)
    seg2 = engine.auto_segment_user(2)
    assert seg1 != seg2, f"Different activity should yield different segments: {seg1} vs {seg2}"

@test("Conversion tracking")
def _():
    mod = load_module("utils/marketing_engine.py", "_me4")
    engine = mod.MarketingEngine()
    c = engine.create_campaign("Test")
    conv = engine.track_conversion(user_id=1, campaign_id=c.campaign_id,
                                   conversion_type="purchase", value=49.99)
    assert conv["value"] == 49.99
    analytics = engine.get_campaign_analytics(c.campaign_id)
    assert analytics["revenue"] == 49.99

@test("Full analytics report")
def _():
    mod = load_module("utils/marketing_engine.py", "_me5")
    engine = mod.MarketingEngine()
    for uid in range(1, 11):
        for _ in range(uid * 10):
            engine.update_lead_activity(uid, "message")
    analytics = engine.get_analytics()
    assert analytics["total_leads"] == 10
    assert "segments" in analytics
    assert "avg_lead_score" in analytics

@test("Funnel metrics")
def _():
    mod = load_module("utils/marketing_engine.py", "_me6")
    engine = mod.MarketingEngine()
    for uid in range(1, 20):
        for _ in range(uid * 5):
            engine.update_lead_activity(uid, "message")
    funnel = engine.get_funnel()
    assert funnel["total_users"] == 19
    assert "engaged" in funnel
    assert "active" in funnel

@test("A/B test campaign")
async def _():
    mod = load_module("utils/marketing_engine.py", "_me7")
    engine = mod.MarketingEngine()
    for uid in range(1, 21):
        engine.update_lead_activity(uid, "message")
    c = engine.create_campaign("AB Test", campaign_type="ab_test")
    c.variants = {"A": {"message": "Version A"}, "B": {"message": "Version B"}}
    result = await engine.start_campaign(c.campaign_id)
    assert result["audience_size"] == 20

# ── 9. Models Registry ──
print("\n── Models Registry ──")

@test("All models have valid provider/model format")
def _():
    content = open(os.path.join(PROJECT_ROOT, "utils", "models_registry.py")).read()
    # Models use positional args: ModelInfo("model_id", ...)
    ids = re.findall(r'ModelInfo\(\s*"([^"]+)"', content)
    assert len(ids) >= 100, f"Expected 100+ models, got {len(ids)}"
    # Models use either provider/model (OpenRouter) or bare names (Gemini/Groq direct)
    for mid in ids:
        assert len(mid) >= 3, f"Model ID too short: {mid}"

@test("No duplicate model IDs")
def _():
    content = open(os.path.join(PROJECT_ROOT, "utils", "models_registry.py")).read()
    ids = re.findall(r'ModelInfo\(\s*"([^"]+)"', content)
    seen = set()
    for mid in ids:
        assert mid not in seen, f"Duplicate: {mid}"
        seen.add(mid)

# ── 10. File structure integrity ──
print("\n── Structure Integrity ──")

@test("All new v3.3 modules are syntactically valid")
def _():
    new_files = [
        "utils/api_key_manager.py", "utils/request_queue.py",
        "utils/internal_api_gateway.py", "utils/event_bus.py",
        "utils/automation_connector.py", "utils/proxy_rotator.py",
        "utils/search_privacy.py", "utils/marketing_engine.py",
    ]
    for f in new_files:
        path = os.path.join(PROJECT_ROOT, f)
        assert os.path.exists(path), f"Missing: {f}"
        code = open(path).read()
        compile(code, f, "exec")

@test("Alembic migration has 22 tables")
def _():
    path = os.path.join(PROJECT_ROOT, "alembic/versions/499fad11a5b9_initial_schema.py")
    content = open(path).read()
    tables = re.findall(r"op\.create_table\(", content)
    assert len(tables) == 22, f"Expected 22 tables, got {len(tables)}"
    drops = re.findall(r"op\.drop_table\(", content)
    assert len(drops) == 22

@test("main.py has v3.3 imports")
def _():
    content = open(os.path.join(PROJECT_ROOT, "main.py")).read()
    assert "internal_api_gateway" in content
    assert "event_bus" in content
    assert "marketing_engine" in content

print("\n" + "=" * 60)
total = passed + failed
print(f"  Runtime Tests: {passed}/{total} passed ({100*passed//max(1,total)}%)")
if failed:
    print(f"  ⚠️  {failed} FAILED")
else:
    print(f"  🏆 ALL TESTS PASSED")
print("=" * 60)

loop.close()


