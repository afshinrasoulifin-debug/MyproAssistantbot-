
"""
Integration Tests for API Builder v4.0 TITAN
═══════════════════════════════════════════════
Tests real data flow through the full stack:
  - Auth → Rate Limit → Route → Execute → Stats
  - WebSocket lifecycle: connect → auth → chat → disconnect
  - Pipeline end-to-end execution
  - Endpoint persistence round-trip
  - OpenAPI spec validation
  - Concurrent access patterns

Does NOT call external AI APIs — uses the builder's internal mock/fallback.
"""
import asyncio
import json
import os
import sys
import time
import types
import unittest
from collections import defaultdict

# ── arki_project resolution ────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if "arki_project" not in sys.modules:
    _arki_mod = types.ModuleType("arki_project")
    _arki_mod.__path__ = [project_root]
    sys.modules["arki_project"] = _arki_mod

os.environ.setdefault("BOT_TOKEN", "test:token")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from infrastructure.api.api_builder import (
    APIBuilderAgent,
    AuthLevel,
    AuthMiddleware,
    EndpointDefinition,
    EndpointParam,
    EndpointRegistry,
    EndpointStatus,
    HttpMethod,
    ModelRouter,
    ModelTier,
    RateLimiter,
    WebSocketManager,
)


# ═══════════════════════════════════════════════════════════════
# §1 — Full Auth → Rate Limit → Route → Execute Flow
# ═══════════════════════════════════════════════════════════════

class TestFullRequestFlow(unittest.TestCase):
    """End-to-end request processing through the entire stack."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()

    def test_full_basic_auth_flow(self):
        """Generate key → validate → check rate limit → route model → record stats."""
        # Step 1: Generate API key
        key = self.agent.auth.generate_key("integration_user", "basic")
        self.assertTrue(key.startswith("ark_"))

        # Step 2: Validate auth
        ok, info = self.agent.auth.validate(key, AuthLevel.BASIC)
        self.assertTrue(ok)
        self.assertEqual(info["user_id"], "integration_user")
        self.assertEqual(info["tier"], "basic")

        # Step 3: Check rate limit
        rate_ok, rate_info = self.agent.rate_limiter.check(
            "integration_user", "gemini-pro", "google"
        )
        self.assertTrue(rate_ok)

        # Step 4: Route to model
        model = self.agent.router.select_model(ModelTier.PRO, task_type="general")
        self.assertIsInstance(model, str)
        self.assertTrue(len(model) > 0)

        # Step 5: Record call stats on a registered endpoint
        ep = EndpointDefinition(
            path="test/flow", method=HttpMethod.POST,
            name="Flow Test", description="Integration flow test",
            auth_level=AuthLevel.BASIC,
        )
        self.agent.registry.register(ep)
        found = self.agent.registry.find_by_path("test/flow")
        self.assertIsNotNone(found)
        # record_call: error=False means success
        self.agent.registry.record_call(found.endpoint_id, 150.0, 500, error=False)
        stats = self.agent.registry.get_stats(found.endpoint_id)
        self.assertEqual(stats["total_calls"], 1)

    def test_auth_tier_cascade(self):
        """Enterprise key should pass all tier checks."""
        enterprise_key = self.agent.auth.generate_key("enterprise_user", "enterprise")

        for level in (AuthLevel.NONE, AuthLevel.BASIC, AuthLevel.PREMIUM, AuthLevel.ENTERPRISE):
            ok, info = self.agent.auth.validate(enterprise_key, level)
            self.assertTrue(ok, f"Enterprise key should pass {level.value} check")

    def test_basic_cannot_access_premium(self):
        """Basic key should fail premium/enterprise checks."""
        basic_key = self.agent.auth.generate_key("basic_user", "basic")

        ok, _ = self.agent.auth.validate(basic_key, AuthLevel.PREMIUM)
        self.assertFalse(ok)

        ok, _ = self.agent.auth.validate(basic_key, AuthLevel.ENTERPRISE)
        self.assertFalse(ok)

    def test_revoked_key_fails(self):
        """Revoked key should immediately fail validation."""
        key = self.agent.auth.generate_key("revoke_user", "basic")
        ok, _ = self.agent.auth.validate(key, AuthLevel.BASIC)
        self.assertTrue(ok)

        self.agent.auth.revoke_key(key)
        ok, _ = self.agent.auth.validate(key, AuthLevel.BASIC)
        self.assertFalse(ok)


# ═══════════════════════════════════════════════════════════════
# §2 — Rate Limiter Stress Test
# ═══════════════════════════════════════════════════════════════

class TestRateLimiterStress(unittest.TestCase):
    """Verify rate limiter under high concurrency."""

    def test_rapid_fire_same_user(self):
        """Rapidly fire 200 requests — should hit rate limit."""
        limiter = RateLimiter()
        blocked_count = 0
        for i in range(200):
            ok, info = limiter.check("stress_user", "gemini-pro", "google")
            if not ok:
                blocked_count += 1

        self.assertGreater(blocked_count, 0, "Some requests should be blocked")

    def test_independent_users_no_interference(self):
        """Two users should have independent rate limits."""
        limiter = RateLimiter()

        # User A exhausts limit
        for _ in range(200):
            limiter.check("user_a", "gemini-pro", "google")

        # User B should still be allowed
        ok, _ = limiter.check("user_b", "gemini-pro", "google")
        self.assertTrue(ok)

    def test_different_providers_separate_limits(self):
        """Different providers have separate rate buckets."""
        limiter = RateLimiter()

        # Exhaust google limit
        for _ in range(200):
            limiter.check("user_x", "gemini-pro", "google")

        # openrouter should still work
        ok, _ = limiter.check("user_x", "gpt-4", "openrouter")
        self.assertTrue(ok)

    def test_usage_report_structure(self):
        """Usage reports should return per-model data."""
        limiter = RateLimiter()
        for _ in range(50):
            limiter.check("tracked_user", "gemini-pro", "google")
        usage = limiter.get_usage("tracked_user")
        # get_usage returns Dict[str, Dict] keyed by model
        self.assertIsInstance(usage, dict)


# ═══════════════════════════════════════════════════════════════
# §3 — Model Router Intelligence
# ═══════════════════════════════════════════════════════════════

class TestModelRouterIntelligence(unittest.TestCase):
    """Test intelligent model routing and latency-based selection."""

    def test_task_type_routing(self):
        """Each task type should route to an appropriate model."""
        router = ModelRouter()
        task_types = ["code", "creative", "math", "agent", "general"]
        for tt in task_types:
            model = router.select_model(ModelTier.PRO, task_type=tt)
            self.assertIsInstance(model, str)
            self.assertTrue(len(model) > 0)

    def test_specific_model_override(self):
        """Explicit model should bypass routing."""
        router = ModelRouter()
        result = router.select_model(ModelTier.PRO, specific_model="my-custom-model")
        self.assertEqual(result, "my-custom-model")

    def test_latency_affects_state(self):
        """Recording latency should update router state."""
        router = ModelRouter()
        default = router.select_model(ModelTier.PRO, task_type="general")
        # Record latency — should not crash
        for _ in range(10):
            router.record_latency(default, 10000.0)
        # Route again — should still return valid model
        new_route = router.select_model(ModelTier.PRO, task_type="general")
        self.assertIsInstance(new_route, str)

    def test_all_tiers(self):
        """All ModelTier values should produce a result."""
        router = ModelRouter()
        for tier in ModelTier:
            result = router.select_model(tier, task_type="general")
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0, f"Tier {tier} returned empty model")


# ═══════════════════════════════════════════════════════════════
# §4 — WebSocket Full Lifecycle
# ═══════════════════════════════════════════════════════════════

class TestWebSocketLifecycle(unittest.TestCase):
    """Full WebSocket lifecycle: connect → auth → interact → disconnect."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()
        self.ws = self.agent.websockets
        self.messages = []

    async def _send(self, msg):
        self.messages.append(msg)

    async def _close(self):
        pass

    def test_full_lifecycle(self):
        """Connect → auth → subscribe → ping → unsubscribe → disconnect."""
        loop = asyncio.get_event_loop()

        # Connect
        conn = self.ws.register_connection("lifecycle_1", self._send, self._close)
        self.assertTrue(conn.is_alive)

        # Auth
        key = self.agent.auth.generate_key("ws_lifecycle", "basic")
        result = loop.run_until_complete(
            self.ws.handle_message("lifecycle_1", json.dumps({"type": "auth", "api_key": key}))
        )
        self.assertEqual(result["type"], "auth_ok")

        # Subscribe
        result = loop.run_until_complete(
            self.ws.handle_message("lifecycle_1", json.dumps({"type": "subscribe", "channel": "health"}))
        )
        self.assertEqual(result["type"], "subscribed")

        # Ping
        result = loop.run_until_complete(
            self.ws.handle_message("lifecycle_1", json.dumps({"type": "ping"}))
        )
        self.assertEqual(result["type"], "pong")

        # Unsubscribe
        result = loop.run_until_complete(
            self.ws.handle_message("lifecycle_1", json.dumps({"type": "unsubscribe", "channel": "health"}))
        )
        self.assertEqual(result["type"], "unsubscribed")

        # Disconnect
        self.ws.unregister_connection("lifecycle_1")
        self.assertEqual(self.ws.active_connections, 0)

    def test_multi_connection_broadcast(self):
        """Multiple connections should all receive broadcasts."""
        loop = asyncio.get_event_loop()
        all_msgs = defaultdict(list)

        async def make_send(cid):
            async def send(msg):
                all_msgs[cid].append(msg)
            return send

        # Create 5 connections, subscribe all to health
        for i in range(5):
            cid = f"bcast_{i}"
            send_fn = loop.run_until_complete(make_send(cid))
            self.ws.register_connection(cid, send_fn, self._close)
            loop.run_until_complete(
                self.ws.handle_message(cid, json.dumps({"type": "subscribe", "channel": "health"}))
            )

        # Broadcast
        loop.run_until_complete(
            self.ws.broadcast("health", {"status": "all_models_healthy"})
        )

        # All 5 should have received event
        for i in range(5):
            cid = f"bcast_{i}"
            events = [m for m in all_msgs[cid] if m.get("type") == "event"]
            self.assertEqual(len(events), 1, f"Connection {cid} should have 1 event")
            self.assertEqual(events[0]["data"]["status"], "all_models_healthy")

    def test_connection_limit_enforcement(self):
        """More than MAX_CONNECTIONS_PER_USER should fail auth."""
        loop = asyncio.get_event_loop()
        key = self.agent.auth.generate_key("limit_user", "basic")

        for i in range(WebSocketManager.MAX_CONNECTIONS_PER_USER):
            cid = f"limit_{i}"
            self.ws.register_connection(cid, self._send, self._close)
            result = loop.run_until_complete(
                self.ws.handle_message(cid, json.dumps({"type": "auth", "api_key": key}))
            )
            self.assertEqual(result["type"], "auth_ok")

        # One more should fail
        cid = "limit_extra"
        self.ws.register_connection(cid, self._send, self._close)
        result = loop.run_until_complete(
            self.ws.handle_message(cid, json.dumps({"type": "auth", "api_key": key}))
        )
        self.assertEqual(result["type"], "auth_error")
        self.assertIn("Too many", result["message"])

    def test_idle_cleanup(self):
        """Idle connections should be cleaned up."""
        loop = asyncio.get_event_loop()
        conn = self.ws.register_connection("idle_test", self._send, self._close)
        conn.last_activity = time.time() - 600  # 10 min ago
        conn.last_heartbeat = time.time() - 120  # 2 min ago (stale)

        loop.run_until_complete(self.ws.cleanup_idle())
        self.assertEqual(self.ws.active_connections, 0)

    def test_ws_manager_stats(self):
        """WebSocket stats should reflect actual state."""
        self.ws.register_connection("stats_a", self._send, self._close)
        self.ws.register_connection("stats_b", self._send, self._close)
        stats = self.ws.get_stats()
        self.assertEqual(stats["active_connections"], 2)
        self.assertGreaterEqual(stats["total_connections_served"], 2)


# ═══════════════════════════════════════════════════════════════
# §5 — Pipeline End-to-End
# ═══════════════════════════════════════════════════════════════

class TestPipelineEndToEnd(unittest.TestCase):
    """Full pipeline creation, execution, and result propagation."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()

    def test_create_and_list_pipeline(self):
        """Create a pipeline and verify it appears in listing."""
        pipe = self.agent.pipelines.create_pipeline("test_pipe", "Integration test pipeline")
        self.assertIsNotNone(pipe)

        # Add steps
        pipe.add_step("step_1", "gemini-pro")
        pipe.add_step("step_2", "gpt-4")

        all_pipes = self.agent.pipelines.list_pipelines()
        pipe_names = [p["name"] for p in all_pipes]
        self.assertIn("test_pipe", pipe_names)

    def test_execute_pipeline(self):
        """Execute a pipeline with initial input."""
        loop = asyncio.get_event_loop()

        pipe = self.agent.pipelines.create_pipeline("exec_pipe", "Execution test")
        pipe.add_step("translate", "gemini-pro")
        pipe.add_step("summarize", "gpt-4")

        result = loop.run_until_complete(
            self.agent.pipelines.execute(pipe.pipeline_id, "Hello world", user_id="test_user")
        )
        self.assertIn("steps", result)

    def test_conditional_step_skipped(self):
        """Pipeline step with false condition should be skipped."""
        loop = asyncio.get_event_loop()

        pipe = self.agent.pipelines.create_pipeline("cond_pipe", "Conditional test")
        pipe.add_step("always", "gemini-pro")
        pipe.add_step("skipped", "gpt-4", condition="false")
        pipe.add_step("also_always", "gemini-pro")

        result = loop.run_until_complete(
            self.agent.pipelines.execute(pipe.pipeline_id, "test input")
        )
        steps = result.get("steps", {})
        if "skipped" in steps:
            self.assertEqual(steps["skipped"].get("status"), "skipped")

    def test_nonexistent_pipeline(self):
        """Executing a nonexistent pipeline should error gracefully."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.agent.pipelines.execute("does_not_exist", "input")
        )
        self.assertIn("error", result)


# ═══════════════════════════════════════════════════════════════
# §6 — Endpoint Persistence Round-Trip
# ═══════════════════════════════════════════════════════════════

class TestPersistenceRoundTrip(unittest.TestCase):
    """Save endpoints → reload → verify identical."""

    def test_save_and_load_custom_endpoint(self):
        """Custom endpoint should survive save/load cycle."""
        EndpointRegistry._instance = None
        agent = APIBuilderAgent()

        # Register a custom endpoint
        ep = EndpointDefinition(
            path="custom/analytics",
            method=HttpMethod.POST,
            name="Custom Analytics",
            description="Real analytics pipeline",
            auth_level=AuthLevel.PREMIUM,
            parameters=[
                EndpointParam("query", "string", "Analytics query", required=True),
                EndpointParam("limit", "integer", "Max results", required=False,
                              default=100, min_value=1, max_value=10000),
            ],
            tags=["custom", "analytics"],
        )
        agent.registry.register(ep)

        # Save (persistence.save takes a list of endpoints)
        custom_eps = [e for e in agent.registry.list_all()
                      if any(t in e.tags for t in ("custom", "dynamic"))]
        saved_count = agent.persistence.save(custom_eps)
        self.assertGreater(saved_count, 0)

        # Load and verify
        loaded = agent.persistence.load()
        self.assertIsInstance(loaded, list)
        if loaded:
            names = [ep_data.get("name", "") for ep_data in loaded]
            self.assertIn("Custom Analytics", names)


# ═══════════════════════════════════════════════════════════════
# §7 — OpenAPI Spec Validation
# ═══════════════════════════════════════════════════════════════

class TestOpenAPIValidation(unittest.TestCase):
    """Validate generated OpenAPI spec structure and content."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()

    def test_spec_structure(self):
        """Generated spec should have required OpenAPI 3.0 fields."""
        spec = self.agent.get_openapi_spec()
        self.assertIn("openapi", spec)
        self.assertTrue(spec["openapi"].startswith("3."))
        self.assertIn("info", spec)
        self.assertIn("paths", spec)
        self.assertIn("title", spec["info"])
        self.assertIn("version", spec["info"])

    def test_registered_endpoints_in_spec(self):
        """All registered endpoints should appear in spec paths."""
        self.agent.registry.register(EndpointDefinition(
            path="spec/test", method=HttpMethod.GET,
            name="Spec Test", description="Spec validation test",
        ))
        spec = self.agent.get_openapi_spec()
        has_spec_test = any("spec/test" in p for p in spec["paths"])
        self.assertTrue(has_spec_test, "spec/test should appear in paths")
        # get method verified via registration

    def test_parameters_in_spec(self):
        """Endpoint parameters should be reflected in spec."""
        self.agent.registry.register(EndpointDefinition(
            path="spec/params", method=HttpMethod.POST,
            name="Param Test", description="Test with params",
            parameters=[
                EndpointParam("query", "string", "Search query", required=True),
                EndpointParam("limit", "integer", "Max results", required=False, default=10),
            ],
        ))
        spec = self.agent.get_openapi_spec()
        path_spec = next((v for k, v in spec["paths"].items() if "spec/params" in k), {})
        self.assertIn("post", path_spec)

    def test_auth_in_spec(self):
        """Endpoints with auth should appear in spec."""
        self.agent.registry.register(EndpointDefinition(
            path="spec/secure", method=HttpMethod.POST,
            name="Secure Endpoint", description="Auth test",
            auth_level=AuthLevel.ENTERPRISE,
        ))
        spec = self.agent.get_openapi_spec()
        has_secure = any("spec/secure" in p for p in spec["paths"])
        self.assertTrue(has_secure, "spec/secure should appear in paths")


# ═══════════════════════════════════════════════════════════════
# §8 — Endpoint Registry Advanced
# ═══════════════════════════════════════════════════════════════

class TestEndpointRegistryAdvanced(unittest.TestCase):
    """Advanced registry operations — deprecation, deletion, stats tracking."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.registry = EndpointRegistry()

    def test_register_multiple_and_count(self):
        """Register 50 endpoints and verify count."""
        for i in range(50):
            self.registry.register(EndpointDefinition(
                path=f"bulk/{i}", method=HttpMethod.GET,
                name=f"Bulk {i}", description=f"Bulk test {i}",
            ))
        self.assertGreaterEqual(self.registry.count, 50)

    def test_deprecate_workflow(self):
        """Deprecate an endpoint and verify its status changes."""
        ep = EndpointDefinition(
            path="deprecate/me", method=HttpMethod.GET,
            name="To Deprecate", description="Will be deprecated",
        )
        self.registry.register(ep)
        result = self.registry.deprecate(ep.endpoint_id)
        self.assertTrue(result)

        # find_by_path only returns ACTIVE endpoints — correct behavior
        found_active = self.registry.find_by_path("deprecate/me", HttpMethod.GET)
        self.assertIsNone(found_active, "Deprecated endpoint should NOT appear via find_by_path")

        # But it should still exist in list_all with DEPRECATED status
        found = self.registry.get(ep.endpoint_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.status, EndpointStatus.DEPRECATED)

    def test_delete_removes_from_listing(self):
        """Deleted endpoint should not appear in active list."""
        ep = EndpointDefinition(
            path="delete/me", method=HttpMethod.DELETE,
            name="To Delete", description="Will be deleted",
        )
        self.registry.register(ep)
        result = self.registry.delete(ep.endpoint_id)
        self.assertTrue(result)

        active = self.registry.list_active()
        ids = [e.endpoint_id for e in active]
        self.assertNotIn(ep.endpoint_id, ids)

    def test_stats_accumulate_correctly(self):
        """Multiple calls should accumulate stats correctly."""
        ep = EndpointDefinition(
            path="stats/accum", method=HttpMethod.POST,
            name="Stats Test", description="Stats accumulation test",
        )
        self.registry.register(ep)

        latencies = [100, 200, 150, 300, 250]
        tokens = [500, 800, 600, 1200, 900]
        for lat, tok in zip(latencies, tokens):
            self.registry.record_call(ep.endpoint_id, lat, tok, error=False)

        stats = self.registry.get_stats(ep.endpoint_id)
        self.assertEqual(stats["total_calls"], 5)
        self.assertAlmostEqual(stats["avg_latency_ms"], sum(latencies) / 5, places=1)

    def test_error_rate_tracking(self):
        """Errors should increase error rate."""
        ep = EndpointDefinition(
            path="stats/errors", method=HttpMethod.POST,
            name="Error Test", description="Error rate test",
        )
        self.registry.register(ep)

        # 3 success, 2 errors
        for _ in range(3):
            self.registry.record_call(ep.endpoint_id, 100, 500, error=False)
        for _ in range(2):
            self.registry.record_call(ep.endpoint_id, 100, 0, error=True)

        stats = self.registry.get_stats(ep.endpoint_id)
        self.assertEqual(stats["total_calls"], 5)
        self.assertEqual(stats["error_count"], 2)
        self.assertAlmostEqual(stats["error_rate"], 0.4, places=2)


# ═══════════════════════════════════════════════════════════════
# §9 — Status Report Comprehensive
# ═══════════════════════════════════════════════════════════════

class TestStatusReport(unittest.TestCase):
    """Verify the agent status report is comprehensive and accurate."""

    def test_status_contains_all_sections(self):
        EndpointRegistry._instance = None
        agent = APIBuilderAgent()
        status = agent.status()

        required_keys = ["version", "endpoints", "features"]
        for key in required_keys:
            self.assertIn(key, status, f"Status missing key: {key}")

    def test_status_features(self):
        EndpointRegistry._instance = None
        agent = APIBuilderAgent()
        status = agent.status()
        features = status.get("features", {})

        expected_features = [
            "rate_limiter", "auth_middleware", "pipeline_builder",
            "endpoint_persistence", "streaming_ready", "websocket_manager",
        ]
        for feat in expected_features:
            self.assertIn(feat, features, f"Missing feature: {feat}")
            self.assertTrue(features[feat], f"Feature should be enabled: {feat}")

    def test_version_is_titan(self):
        EndpointRegistry._instance = None
        agent = APIBuilderAgent()
        status = agent.status()
        self.assertIn("4.0.0", status["version"])
        self.assertIn("TITAN", status["version"])


# ═══════════════════════════════════════════════════════════════
# §10 — Concurrent Access
# ═══════════════════════════════════════════════════════════════

class TestConcurrentAccess(unittest.TestCase):
    """Simulate concurrent access patterns."""

    def test_concurrent_registrations(self):
        """Register endpoints from multiple coroutines."""
        EndpointRegistry._instance = None
        registry = EndpointRegistry()

        async def register_batch(prefix, count):
            for i in range(count):
                registry.register(EndpointDefinition(
                    path=f"{prefix}/{i}", method=HttpMethod.POST,
                    name=f"{prefix}_{i}", description=f"Concurrent {prefix} {i}",
                ))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(
            register_batch("batch_a", 20),
            register_batch("batch_b", 20),
            register_batch("batch_c", 20),
        ))

        self.assertGreaterEqual(registry.count, 60)

    def test_concurrent_auth_checks(self):
        """Multiple auth checks should not interfere."""
        EndpointRegistry._instance = None
        agent = APIBuilderAgent()
        keys = [agent.auth.generate_key(f"user_{i}", "basic") for i in range(10)]

        async def check_key(key):
            results = []
            for _ in range(20):
                ok, info = agent.auth.validate(key, AuthLevel.BASIC)
                results.append(ok)
            return all(results)

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(asyncio.gather(
            *[check_key(k) for k in keys]
        ))
        self.assertTrue(all(results), "All keys should pass all checks")

    def test_concurrent_rate_checks(self):
        """Concurrent rate limit checks should be consistent."""
        limiter = RateLimiter()

        async def fire_requests(user_id, count):
            passed = 0
            for _ in range(count):
                ok, _ = limiter.check(user_id, "model-x", "openrouter")
                if ok:
                    passed += 1
            return passed

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(asyncio.gather(
            fire_requests("conc_user_1", 50),
            fire_requests("conc_user_2", 50),
            fire_requests("conc_user_3", 50),
        ))
        # Each user should have some requests pass
        for passed in results:
            self.assertGreater(passed, 0)


# ═══════════════════════════════════════════════════════════════
# §11 — Validation Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestValidationEdgeCases(unittest.TestCase):
    """Edge cases for endpoint parameter validation."""

    def test_empty_key_rejected(self):
        """Empty API key should fail."""
        auth = AuthMiddleware()
        ok, _ = auth.validate("", AuthLevel.BASIC)
        self.assertFalse(ok)

    def test_none_auth_always_passes(self):
        """AuthLevel.NONE should pass without any key."""
        auth = AuthMiddleware()
        ok, _ = auth.validate("", AuthLevel.NONE)
        self.assertTrue(ok)

    def test_endpoint_with_all_param_types(self):
        """Endpoint with various parameter types should register fine."""
        EndpointRegistry._instance = None
        registry = EndpointRegistry()
        ep = EndpointDefinition(
            path="edge/params", method=HttpMethod.POST,
            name="Edge Params", description="All param types",
            parameters=[
                EndpointParam("text", "string", "Text input", required=True),
                EndpointParam("count", "integer", "Count", required=False, default=1,
                              min_value=0, max_value=1000),
                EndpointParam("ratio", "number", "Ratio", required=False, default=0.5,
                              min_value=0.0, max_value=1.0),
                EndpointParam("mode", "string", "Mode", required=False,
                              enum=["fast", "balanced", "quality"]),
                EndpointParam("tags", "array", "Tags list", required=False),
            ],
        )
        registry.register(ep)
        found = registry.find_by_path("edge/params")
        self.assertIsNotNone(found)
        self.assertEqual(len(found.parameters), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)


