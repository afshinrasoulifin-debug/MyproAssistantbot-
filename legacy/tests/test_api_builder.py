
"""
tests/test_api_builder.py — Comprehensive API Builder v4.0 Tests
═══════════════════════════════════════════════════════════════════
Real tests with real assertions. No fake quality scores.

Test categories:
  1. EndpointRegistry — CRUD operations
  2. ModelRouter — dynamic tier routing
  3. RateLimiter — token bucket behavior
  4. AuthMiddleware — key management + tier access
  5. PipelineExecutor — multi-step chains
  6. EndpointPersistence — save/load JSON
  7. APIBuilderAgent — initialization + endpoint execution
  8. OpenAPIGenerator — spec generation
  9. Validation — parameter checking
  10. Integration — end-to-end flow
"""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.api.api_builder import (
    APIBuilderAgent,
    AuthLevel,
    AuthMiddleware,
    EndpointDefinition,
    EndpointParam,
    EndpointPersistence,
    EndpointRegistry,
    EndpointStatus,
    HttpMethod,
    ModelRouter,
    ModelTier,
    Pipeline,
    PipelineExecutor,
    RateLimiter,
    OpenAPIGenerator,
)


# ═══════════════════════════════════════════════════════════════════
# §1 — EndpointRegistry Tests
# ═══════════════════════════════════════════════════════════════════

class TestEndpointRegistry(unittest.TestCase):
    """Tests for endpoint CRUD operations and stats tracking."""

    def setUp(self):
        # Reset singleton
        EndpointRegistry._instance = None
        self.registry = EndpointRegistry()

    def _make_ep(self, path="test/endpoint", name="Test", **kwargs):
        return EndpointDefinition(path=path, name=name, **kwargs)

    def test_register_and_get(self):
        ep = self._make_ep()
        ep_id = self.registry.register(ep)
        self.assertIsNotNone(ep_id)
        self.assertEqual(self.registry.get(ep_id), ep)

    def test_find_by_path(self):
        ep = self._make_ep(path="models/gemini_pro/chat")
        self.registry.register(ep)
        found = self.registry.find_by_path("models/gemini_pro/chat")
        self.assertIsNotNone(found)
        self.assertEqual(found.path, "models/gemini_pro/chat")

    def test_find_by_path_not_found(self):
        self.assertIsNone(self.registry.find_by_path("nonexistent"))

    def test_list_all(self):
        self.registry.register(self._make_ep("a/b"))
        self.registry.register(self._make_ep("c/d"))
        self.assertEqual(len(self.registry.list_all()), 2)

    def test_list_active(self):
        ep1 = self._make_ep("a/b")
        ep2 = self._make_ep("c/d")
        self.registry.register(ep1)
        ep2_id = self.registry.register(ep2)
        self.registry.deprecate(ep2_id)
        self.assertEqual(len(self.registry.list_active()), 1)

    def test_deprecate(self):
        ep = self._make_ep()
        ep_id = self.registry.register(ep)
        self.assertTrue(self.registry.deprecate(ep_id))
        self.assertEqual(self.registry.get(ep_id).status, EndpointStatus.DEPRECATED)

    def test_delete(self):
        ep = self._make_ep()
        ep_id = self.registry.register(ep)
        self.assertTrue(self.registry.delete(ep_id))
        self.assertIsNone(self.registry.get(ep_id))

    def test_record_call_and_stats(self):
        ep = self._make_ep()
        ep_id = self.registry.register(ep)
        self.registry.record_call(ep_id, 150.0, 500)
        self.registry.record_call(ep_id, 200.0, 600, error=True)
        stats = self.registry.get_stats(ep_id)
        self.assertEqual(stats["total_calls"], 2)
        self.assertEqual(stats["error_count"], 1)

    def test_count(self):
        self.assertEqual(self.registry.count, 0)
        self.registry.register(self._make_ep("a"))
        self.registry.register(self._make_ep("b"))
        self.assertEqual(self.registry.count, 2)


# ═══════════════════════════════════════════════════════════════════
# §2 — ModelRouter Tests
# ═══════════════════════════════════════════════════════════════════

class TestModelRouter(unittest.TestCase):
    """Tests for dynamic model routing."""

    def setUp(self):
        self.router = ModelRouter()

    def test_specific_model_override(self):
        """When specific_model is given, always return it."""
        result = self.router.select_model(ModelTier.FAST, specific_model="g-qwen37-max")
        self.assertEqual(result, "g-qwen37-max")

    def test_auto_code_task(self):
        result = self.router.select_model(ModelTier.AUTO, task_type="code")
        self.assertEqual(result, "g-qwen3-coder")

    def test_auto_math_task(self):
        result = self.router.select_model(ModelTier.AUTO, task_type="math")
        self.assertEqual(result, "g-deepseek-r1")

    def test_auto_creative_task(self):
        result = self.router.select_model(ModelTier.AUTO, task_type="creative")
        self.assertEqual(result, "g-qwen37-max")

    def test_auto_agent_task(self):
        result = self.router.select_model(ModelTier.AUTO, task_type="agent")
        self.assertEqual(result, "g-kimi26-think")

    def test_auto_default(self):
        result = self.router.select_model(ModelTier.AUTO, task_type="general")
        self.assertEqual(result, "gemini-pro")

    def test_consortium_marker(self):
        result = self.router.select_model(ModelTier.CONSORTIUM)
        self.assertEqual(result, "__consortium__")

    def test_record_and_use_latency(self):
        """Router should prefer lower-latency models."""
        self.router.record_latency("model_a", 100.0)
        self.router.record_latency("model_b", 500.0)
        stats = self.router.get_model_stats()
        self.assertIn("model_a", stats)
        self.assertLess(stats["model_a"]["avg_latency_ms"], stats["model_b"]["avg_latency_ms"])


# ═══════════════════════════════════════════════════════════════════
# §3 — RateLimiter Tests
# ═══════════════════════════════════════════════════════════════════

class TestRateLimiter(unittest.TestCase):
    """Tests for token bucket rate limiting."""

    def setUp(self):
        self.limiter = RateLimiter()

    def test_first_request_allowed(self):
        ok, info = self.limiter.check("user1", "gemini-pro", "gemini")
        self.assertTrue(ok)
        self.assertIsNone(info)

    def test_rate_limit_exhaust(self):
        """After exhausting RPM, should be blocked."""
        # Gemini has 60 RPM
        for i in range(60):
            ok, _ = self.limiter.check("user1", "gemini-pro", "gemini")
            self.assertTrue(ok, f"Request {i+1} should be allowed")

        # 61st should be blocked
        ok, info = self.limiter.check("user1", "gemini-pro", "gemini")
        self.assertFalse(ok)
        self.assertIn("retry_after_seconds", info)

    def test_different_users_independent(self):
        """Different users have separate rate limits."""
        for _ in range(60):
            self.limiter.check("user1", "gemini-pro", "gemini")

        # user2 should still be OK
        ok, _ = self.limiter.check("user2", "gemini-pro", "gemini")
        self.assertTrue(ok)

    def test_different_models_independent(self):
        """Different models have separate rate limits."""
        for _ in range(60):
            self.limiter.check("user1", "gemini-pro", "gemini")

        # Same user, different model should still be OK
        ok, _ = self.limiter.check("user1", "gemini-flash", "gemini")
        self.assertTrue(ok)

    def test_usage_tracking(self):
        self.limiter.check("user1", "gemini-pro", "gemini")
        self.limiter.check("user1", "gemini-flash", "gemini")
        usage = self.limiter.get_usage("user1")
        self.assertIn("gemini-pro", usage)
        self.assertIn("gemini-flash", usage)
        self.assertEqual(usage["gemini-pro"]["daily_used"], 1)


# ═══════════════════════════════════════════════════════════════════
# §4 — AuthMiddleware Tests
# ═══════════════════════════════════════════════════════════════════

class TestAuthMiddleware(unittest.TestCase):
    """Tests for API key authentication and tier access."""

    def setUp(self):
        self.auth = AuthMiddleware()

    def test_none_level_always_passes(self):
        ok, info = self.auth.validate("", AuthLevel.NONE)
        self.assertTrue(ok)
        self.assertEqual(info["user_id"], "anonymous")

    def test_basic_with_valid_key(self):
        key = self.auth.generate_key("user1", "basic")
        ok, info = self.auth.validate(key, AuthLevel.BASIC)
        self.assertTrue(ok)
        self.assertEqual(info["user_id"], "user1")

    def test_basic_with_no_key(self):
        ok, info = self.auth.validate("", AuthLevel.BASIC)
        self.assertFalse(ok)

    def test_basic_with_wrong_key(self):
        ok, info = self.auth.validate("wrong_key_123", AuthLevel.BASIC)
        self.assertFalse(ok)

    def test_tier_escalation_blocked(self):
        """Basic key can't access enterprise endpoint."""
        key = self.auth.generate_key("user1", "basic")
        ok, info = self.auth.validate(key, AuthLevel.ENTERPRISE)
        self.assertFalse(ok)

    def test_enterprise_can_access_basic(self):
        """Enterprise key can access basic endpoint."""
        key = self.auth.generate_key("admin", "enterprise")
        ok, info = self.auth.validate(key, AuthLevel.BASIC)
        self.assertTrue(ok)

    def test_revoke_key(self):
        key = self.auth.generate_key("user1", "basic")
        self.auth.revoke_key(key)
        ok, info = self.auth.validate(key, AuthLevel.BASIC)
        self.assertFalse(ok)

    def test_request_count_tracking(self):
        key = self.auth.generate_key("user1", "basic")
        self.auth.validate(key, AuthLevel.BASIC)
        self.auth.validate(key, AuthLevel.BASIC)
        # Key info should track 2 requests
        key_hash = __import__("hashlib").sha256(key.encode()).hexdigest()
        self.assertEqual(self.auth._api_keys[key_hash]["request_count"], 2)


# ═══════════════════════════════════════════════════════════════════
# §5 — PipelineExecutor Tests
# ═══════════════════════════════════════════════════════════════════

class TestPipeline(unittest.TestCase):
    """Tests for multi-step pipeline definitions."""

    def test_pipeline_creation(self):
        p = Pipeline(name="Test Pipeline")
        p.add_step("translate", "gemini-pro", system_prompt="Translate to English")
        p.add_step("summarize", "gemini-flash", system_prompt="Summarize")
        self.assertEqual(len(p.steps), 2)
        self.assertEqual(p.steps[0].name, "translate")

    def test_pipeline_chaining(self):
        p = Pipeline(name="Chain Test")
        result = p.add_step("a", "m1").add_step("b", "m2").add_step("c", "m3")
        self.assertEqual(result, p)  # Returns self for chaining
        self.assertEqual(len(p.steps), 3)


class TestPipelineExecutor(unittest.TestCase):
    """Tests for pipeline execution."""

    def setUp(self):
        self.mock_builder = MagicMock()
        self.mock_builder.quick_chat = AsyncMock(return_value="Mock response")
        self.executor = PipelineExecutor(self.mock_builder)

    def test_create_and_list(self):
        p = self.executor.create_pipeline("Test", "A test pipeline")
        pipelines = self.executor.list_pipelines()
        self.assertEqual(len(pipelines), 1)
        self.assertEqual(pipelines[0]["name"], "Test")

    def test_execute_pipeline(self):
        p = self.executor.create_pipeline("Test")
        p.add_step("step1", "gemini-pro")
        p.add_step("step2", "gemini-flash")

        result = asyncio.get_event_loop().run_until_complete(
            self.executor.execute(p.pipeline_id, "Hello")
        )
        self.assertEqual(result["total_steps"], 2)
        self.assertEqual(result["successful_steps"], 2)
        self.assertEqual(self.mock_builder.quick_chat.call_count, 2)

    def test_execute_nonexistent(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.executor.execute("fake_id", "Hello")
        )
        self.assertIn("error", result)

    def test_conditional_step(self):
        """Step with false condition should be skipped."""
        p = self.executor.create_pipeline("Conditional")
        p.add_step("always", "m1")
        p.add_step("conditional", "m2", condition="len(prev_output) > 99999")

        self.mock_builder.quick_chat = AsyncMock(return_value="Short")
        result = asyncio.get_event_loop().run_until_complete(
            self.executor.execute(p.pipeline_id, "Test")
        )
        self.assertEqual(result["executed_steps"], 1)  # Only first step executed


# ═══════════════════════════════════════════════════════════════════
# §6 — EndpointPersistence Tests
# ═══════════════════════════════════════════════════════════════════

class TestEndpointPersistence(unittest.TestCase):
    """Tests for endpoint save/load to JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "endpoints.json")
        self.persistence = EndpointPersistence(self.path)

    def test_save_and_load(self):
        ep = EndpointDefinition(
            path="custom/test",
            name="Custom Test",
            tags=["custom"],
            parameters=[EndpointParam("prompt", "string", "Test prompt")],
        )
        count = self.persistence.save([ep])
        self.assertEqual(count, 1)

        loaded = self.persistence.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["path"], "custom/test")

    def test_load_nonexistent(self):
        p = EndpointPersistence("/tmp/nonexistent_12345.json")
        self.assertEqual(p.load(), [])

    def test_only_saves_custom(self):
        """Only endpoints with 'custom' or 'dynamic' tags are saved."""
        ep1 = EndpointDefinition(path="builtin/chat", name="Chat", tags=["core"])
        ep2 = EndpointDefinition(path="my/custom", name="Custom", tags=["custom"])
        count = self.persistence.save([ep1, ep2])
        self.assertEqual(count, 1)  # Only ep2

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)


# ═══════════════════════════════════════════════════════════════════
# §7 — OpenAPIGenerator Tests
# ═══════════════════════════════════════════════════════════════════

class TestOpenAPIGenerator(unittest.TestCase):
    """Tests for OpenAPI spec generation."""

    def test_generate_spec(self):
        endpoints = [
            EndpointDefinition(
                path="chat/completions",
                method=HttpMethod.POST,
                name="Chat",
                description="Chat completion",
                parameters=[
                    EndpointParam("messages", "array", "Chat messages"),
                    EndpointParam("model", "string", "Model key", required=False),
                ],
            ),
        ]
        spec = OpenAPIGenerator.generate(endpoints)
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("/v1/chat/completions", spec["paths"])
        self.assertIn("post", spec["paths"]["/v1/chat/completions"])

    def test_empty_endpoints(self):
        spec = OpenAPIGenerator.generate([])
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertEqual(len(spec["paths"]), 0)


# ═══════════════════════════════════════════════════════════════════
# §8 — Validation Tests
# ═══════════════════════════════════════════════════════════════════

class TestValidation(unittest.TestCase):
    """Tests for parameter validation logic."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()

    def test_required_param_missing(self):
        ep = EndpointDefinition(
            path="test",
            name="Test",
            parameters=[EndpointParam("messages", "array", "Required", required=True)],
        )
        errors = self.agent._validate_params(ep, {})
        self.assertEqual(len(errors), 1)
        self.assertIn("messages", errors[0])

    def test_required_param_present(self):
        ep = EndpointDefinition(
            path="test",
            name="Test",
            parameters=[EndpointParam("messages", "array", "Required", required=True)],
        )
        errors = self.agent._validate_params(ep, {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(len(errors), 0)

    def test_enum_validation(self):
        ep = EndpointDefinition(
            path="test",
            name="Test",
            parameters=[
                EndpointParam("tier", "string", "Tier", enum=["fast", "pro", "ultra"]),
            ],
        )
        errors = self.agent._validate_params(ep, {"tier": "invalid"})
        self.assertEqual(len(errors), 1)

    def test_min_max_validation(self):
        ep = EndpointDefinition(
            path="test",
            name="Test",
            parameters=[
                EndpointParam("temperature", "number", "Temp", min_value=0, max_value=2),
            ],
        )
        errors = self.agent._validate_params(ep, {"temperature": 5.0})
        self.assertEqual(len(errors), 1)

        errors = self.agent._validate_params(ep, {"temperature": 0.7})
        self.assertEqual(len(errors), 0)


# ═══════════════════════════════════════════════════════════════════
# §9 — APIBuilderAgent Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestAPIBuilderAgent(unittest.TestCase):
    """Integration tests for the API builder."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()

    def test_create_endpoint(self):
        ep = self.agent.create_endpoint(
            path="custom/test",
            name="Custom Test",
            description="A custom endpoint",
            system_prompt="You are a test assistant.",
            model_tier="pro",
        )
        self.assertEqual(ep.path, "custom/test")
        self.assertIn("custom", ep.tags)

    def test_dynamic_registration(self):
        """Verify dynamic registration creates endpoints from MODELS dict."""
        # Check if models_registry is available in this environment
        try:
            registry_available = True
        except Exception:
            registry_available = False

        self.agent._register_per_model_endpoints()
        count = self.agent.registry.count

        if registry_available:
            self.assertGreater(count, 0, "Should register at least some endpoints")
        else:
            # models_registry not loadable (missing deps) — verify graceful degradation
            self.assertEqual(count, 0, "Should register 0 endpoints without registry")

    def test_status_report(self):
        status = self.agent.status()
        self.assertIn("version", status)
        self.assertIn("4.0.0", status["version"])
        self.assertTrue(status["features"]["websocket_manager"])
        self.assertIn("features", status)
        self.assertTrue(status["features"]["rate_limiter"])
        self.assertTrue(status["features"]["pipeline_builder"])

    def test_pipeline_access(self):
        """Pipeline executor should be lazily created."""
        p = self.agent.pipelines
        self.assertIsInstance(p, PipelineExecutor)

    def test_get_openapi_spec(self):
        self.agent._register_builtin_endpoints()
        spec = self.agent.get_openapi_spec()
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertGreater(len(spec["paths"]), 0)


# ═══════════════════════════════════════════════════════════════════
# §10 — Model Count Verification
# ═══════════════════════════════════════════════════════════════════

class TestModelCount(unittest.TestCase):
    """Verify model counts match across components."""

    def test_get_all_model_keys_v2(self):
        """get_all_model_keys_v2 should return all models from registry."""
        EndpointRegistry._instance = None
        agent = APIBuilderAgent()
        models = agent.get_all_model_keys_v2()

        # Check if models_registry loaded successfully
        try:
            registry_available = True
        except Exception:
            registry_available = False

        if registry_available:
            self.assertGreater(len(models), 100, "Should have 100+ models")
            for m in models[:5]:
                self.assertIn("key", m)
                self.assertIn("id", m)
                self.assertIn("provider", m)
                self.assertIn("tier", m)
        else:
            # Without registry, get_all_model_keys_v2 returns []
            self.assertEqual(len(models), 0, "Should return [] without registry")




# ═══════════════════════════════════════════════════════════════════
# §11 — WebSocket Manager Tests
# ═══════════════════════════════════════════════════════════════════

class TestWebSocketManager(unittest.TestCase):
    """Tests for the real WebSocket manager."""

    def setUp(self):
        EndpointRegistry._instance = None
        self.agent = APIBuilderAgent()
        self.ws = self.agent.websockets
        self._sent_messages = []

    async def _mock_send(self, msg):
        self._sent_messages.append(msg)

    async def _mock_close(self):
        pass

    def test_register_and_unregister(self):
        conn = self.ws.register_connection(
            "test_conn_1",
            send_fn=self._mock_send,
            close_fn=self._mock_close,
        )
        self.assertEqual(conn.conn_id, "test_conn_1")
        self.assertEqual(self.ws.active_connections, 1)

        self.ws.unregister_connection("test_conn_1")
        self.assertEqual(self.ws.active_connections, 0)

    def test_auth_flow(self):
        """Auth with valid key should succeed."""
        key = self.agent.auth.generate_key("ws_user", "basic")
        conn = self.ws.register_connection("auth_test", self._mock_send, self._mock_close)

        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("auth_test", json.dumps({"type": "auth", "api_key": key}))
        )
        self.assertEqual(result["type"], "auth_ok")
        self.assertEqual(result["user_id"], "ws_user")

    def test_auth_invalid_key(self):
        """Auth with invalid key should fail."""
        self.ws.register_connection("auth_fail", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("auth_fail", json.dumps({"type": "auth", "api_key": "invalid"}))
        )
        self.assertEqual(result["type"], "auth_error")

    def test_ping_pong(self):
        """Ping should return pong with server time."""
        self.ws.register_connection("ping_test", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("ping_test", json.dumps({"type": "ping"}))
        )
        self.assertEqual(result["type"], "pong")
        self.assertIn("server_time", result)

    def test_subscribe_valid_channel(self):
        self.ws.register_connection("sub_test", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("sub_test", json.dumps({"type": "subscribe", "channel": "health"}))
        )
        self.assertEqual(result["type"], "subscribed")
        self.assertEqual(result["channel"], "health")

    def test_subscribe_invalid_channel(self):
        self.ws.register_connection("sub_fail", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("sub_fail", json.dumps({"type": "subscribe", "channel": "nonexistent"}))
        )
        self.assertEqual(result["type"], "error")

    def test_chat_requires_auth(self):
        """Chat without authentication should be rejected."""
        self.ws.register_connection("noauth", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("noauth", json.dumps({
                "type": "chat", "model": "gemini-pro", "prompt": "Hello"
            }))
        )
        self.assertEqual(result["type"], "error")
        self.assertIn("Authentication required", result["message"])

    def test_invalid_json(self):
        self.ws.register_connection("json_fail", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("json_fail", "not json at all")
        )
        self.assertEqual(result["type"], "error")
        self.assertIn("Invalid JSON", result["message"])

    def test_unknown_message_type(self):
        self.ws.register_connection("unknown", self._mock_send, self._mock_close)
        result = asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("unknown", json.dumps({"type": "foobar"}))
        )
        self.assertEqual(result["type"], "error")

    def test_stats(self):
        self.ws.register_connection("stats_test", self._mock_send, self._mock_close)
        stats = self.ws.get_stats()
        self.assertEqual(stats["active_connections"], 1)
        self.assertGreaterEqual(stats["total_connections_served"], 1)

    def test_connection_is_alive(self):
        conn = self.ws.register_connection("alive_test", self._mock_send, self._mock_close)
        self.assertTrue(conn.is_alive)
        conn._closed = True
        self.assertFalse(conn.is_alive)

    def test_broadcast(self):
        """Broadcast should send to all subscribers."""
        sent_a = []
        sent_b = []
        async def send_a(msg): sent_a.append(msg)
        async def send_b(msg): sent_b.append(msg)

        self.ws.register_connection("bcast_a", send_a, self._mock_close)
        self.ws.register_connection("bcast_b", send_b, self._mock_close)

        # Subscribe both to health channel
        asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("bcast_a", json.dumps({"type": "subscribe", "channel": "health"}))
        )
        asyncio.get_event_loop().run_until_complete(
            self.ws.handle_message("bcast_b", json.dumps({"type": "subscribe", "channel": "health"}))
        )

        asyncio.get_event_loop().run_until_complete(
            self.ws.broadcast("health", {"status": "ok"})
        )

        # Both should have received the broadcast (plus the subscribe ack)
        health_a = [m for m in sent_a if m.get("type") == "event"]
        health_b = [m for m in sent_b if m.get("type") == "event"]
        self.assertEqual(len(health_a), 1)
        self.assertEqual(len(health_b), 1)
        self.assertEqual(health_a[0]["data"]["status"], "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)


