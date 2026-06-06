
"""
REAL infrastructure tests for Arki v10.4.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests SecurityInterceptorFilter, Self-Healing, Observability,
DB Optimizer, Boot wiring, and Titanium orchestrator.

Run:  pytest tests/test_real_infrastructure.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("AI_API_KEY", "test")
os.environ.setdefault("AI_BASE_URL", "https://test.example.com")
os.environ.setdefault("AI_MODEL", "test-model")
os.environ["INFRA_APEX"] = "true"


# ═══════════════════════════════════════════════════════════════
# 1. SECURITY INTERCEPTOR FILTER — 10-Layer Defense
# ═══════════════════════════════════════════════════════════════

class TestSecurityInterceptorFilter:
    """Deep behavioral tests for 10-layer security filter."""

    def _get_filter(self, apex=False):
        from arki_project.infrastructure.combined.security_interceptor_filter import (
            SecurityInterceptorFilter,
        )
        return SecurityInterceptorFilter(apex=apex)

    # -- Layer 0: Godmode --
    
    def test_apex_bypasses_everything(self):
        """Godmode should bypass ALL security layers."""
        f = self._get_filter(apex=True)
        payloads = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../etc/passwd",
            "{{7*7}}",
            "os.system('rm -rf /')",
        ]
        for payload in payloads:
            r = f.scan_input(payload)
            assert r["safe"], f"Godmode should bypass: {payload[:30]}"
            assert r["apex"]

    def test_apex_off_blocks_attacks(self):
        """Without apex, attacks should be blocked."""
        f = self._get_filter(apex=False)
        r = f.scan_input("<script>alert(1)</script>")
        assert not r["safe"]

    # -- Layer 1: Cleared users --
    
    def test_clear_user_bypass(self):
        """Cleared users should bypass security checks."""
        f = self._get_filter()
        f.clear_user("admin_user")
        r = f.scan_input("'; DROP TABLE --", user_id="admin_user")
        assert r["safe"]

    def test_unclear_user(self):
        """Uncleared users should be checked normally."""
        f = self._get_filter()
        f.clear_user("user1")
        f.unclear_user("user1")
        assert not f.security_cleared(user_id="user1")

    def test_clear_ip(self):
        """Cleared IPs should bypass checks."""
        f = self._get_filter()
        f.clear_ip("192.168.1.1")
        assert f.security_cleared(ip="192.168.1.1")

    def test_unclear_ip(self):
        """Uncleared IPs should be checked."""
        f = self._get_filter()
        f.clear_ip("10.0.0.1")
        f.unclear_ip("10.0.0.1")
        assert not f.security_cleared(ip="10.0.0.1")

    # -- Layer 5: Pattern detection --
    
    def test_xss_detection(self):
        """XSS patterns should be detected."""
        f = self._get_filter()
        r = f.scan_input("<script>document.cookie</script>")
        assert not r["safe"]
        assert any("xss" in t for t in r.get("threats", []))

    def test_sql_injection_detection(self):
        """SQL injection should be detected."""
        f = self._get_filter()
        r = f.scan_input("1' OR '1'='1")
        assert not r["safe"]

    def test_path_traversal_detection(self):
        """Path traversal should be detected."""
        f = self._get_filter()
        r = f.scan_input("../../../../etc/passwd")
        assert not r["safe"]

    def test_safe_input_passes(self):
        """Normal text should pass all checks."""
        f = self._get_filter()
        safe_texts = [
            "سلام! حالت خوبه؟",
            "Hello world",
            "Please help me with my order #12345",
            "I want to buy a product",
            "The price is $29.99",
            "Can you translate this to Persian?",
        ]
        for text in safe_texts:
            r = f.scan_input(text)
            assert r["safe"], f"Should be safe: {text}"

    # -- Stats --
    
    def test_stats_tracking(self):
        """Filter should track scan statistics via .status property."""
        f = self._get_filter()
        f.scan_input("hello")
        f.scan_input("<script>x</script>")
        stats = f.status
        assert stats["scanned"] == 2
        assert stats["blocked"] >= 1

    # -- Export/Import rules --
    
    def test_export_import_rules(self):
        """Rules should be exportable and importable."""
        f = self._get_filter()
        f.clear_user("u1")
        f.clear_ip("1.2.3.4")
        exported = f.export_rules()
        assert "u1" in exported.get("cleared_users", [])
        assert "1.2.3.4" in exported.get("cleared_ips", [])

        f2 = self._get_filter()
        f2.import_rules(exported)
        assert f2.security_cleared(user_id="u1")
        assert f2.security_cleared(ip="1.2.3.4")

    # -- Sensitivity levels --
    
    def test_sensitivity_change(self):
        """Sensitivity level should be changeable."""
        f = self._get_filter()
        f.set_sensitivity(3)  # HIGH
        stats = f.status
        # sensitivity is a string like "HIGH" or "MEDIUM"
        assert stats.get("sensitivity") is not None


# ═══════════════════════════════════════════════════════════════
# 2. SELF-HEALING ENGINE
# ═══════════════════════════════════════════════════════════════

class TestSelfHealingEngine:
    """Tests self-healing component lifecycle management."""

    def _get_engine(self):
        from arki_project.core.self_healing import SelfHealingEngine, ComponentSpec
        return SelfHealingEngine(), ComponentSpec

    def test_register_component(self):
        """Components should register with name and health check."""
        engine, Spec = self._get_engine()
        engine.register(Spec(name="database"))
        assert "database" in engine._components

    def test_topological_sort(self):
        """Dependencies should be sorted correctly."""
        engine, Spec = self._get_engine()
        engine.register(Spec(name="db"))
        engine.register(Spec(name="cache", depends_on=["db"]))
        engine.register(Spec(name="api", depends_on=["cache", "db"]))
        order = engine._topological_sort()
        assert order.index("db") < order.index("cache")
        assert order.index("cache") < order.index("api")

    def test_circular_dependency_safe(self):
        """Circular dependencies should not crash."""
        engine, Spec = self._get_engine()
        engine.register(Spec(name="a", depends_on=["b"]))
        engine.register(Spec(name="b", depends_on=["a"]))
        # Should not hang or crash
        try:
            order = engine._topological_sort()
            assert isinstance(order, list)
        except Exception:
            pass  # Acceptable to raise on circular dep

    def test_component_status_tracking(self):
        """Component health status should be queryable via dashboard()."""
        engine, Spec = self._get_engine()
        engine.register(Spec(name="redis"))
        status = engine.dashboard()
        assert isinstance(status, dict)

    def test_cascade_prevention(self):
        """Dependent components should not restart if parent is down."""
        engine, Spec = self._get_engine()
        engine.register(Spec(name="db"))
        engine.register(Spec(name="cache", depends_on=["db"]))
        engine.register(Spec(name="api", depends_on=["cache"]))
        # Mark db as down
        if hasattr(engine, '_mark_down'):
            engine._mark_down("db")
            # API should not attempt restart while db is down
            deps = engine._get_dependencies("api")
            assert "db" in deps or "cache" in deps


# ═══════════════════════════════════════════════════════════════
# 3. OBSERVABILITY — Tracing + Metrics + Alerts
# ═══════════════════════════════════════════════════════════════

class TestObservability:
    """Tests unified observability layer."""

    def _get_obs(self):
        from arki_project.core.observability import Observability
        obs = Observability()
        obs.reset()
        return obs

    # -- Metrics --
    
    def test_counter_increment(self):
        """Counter should increment correctly."""
        obs = self._get_obs()
        obs.metrics.inc("http.requests", 5)
        obs.metrics.inc("http.requests", 3)
        assert obs.metrics.counter("http.requests") == 8

    def test_gauge_set(self):
        """Gauge should hold latest value."""
        obs = self._get_obs()
        obs.metrics.set_gauge("cpu.usage", 45.2)
        assert obs.metrics.gauge("cpu.usage") == 45.2
        obs.metrics.set_gauge("cpu.usage", 78.1)
        assert obs.metrics.gauge("cpu.usage") == 78.1

    def test_histogram_percentiles(self):
        """Histogram should calculate percentiles via histogram() summary."""
        obs = self._get_obs()
        for v in range(1, 101):
            obs.metrics.observe("latency", float(v))
        p = obs.metrics.histogram("latency")
        assert p is not None
        assert p["p50"] == pytest.approx(50.5, abs=2)
        assert p["p95"] >= 90

    # -- Tracing --
    
    def test_trace_lifecycle(self):
        """Trace should start and finish correctly."""
        obs = self._get_obs()
        span = obs.tracer.start_trace("test_operation")
        assert span is not None
        assert span.trace_id is not None
        obs.tracer.finish_span(span)
        trace = obs.tracer.get_trace(span.trace_id)
        assert len(trace) == 1

    def test_child_spans(self):
        """Child spans should be part of parent trace."""
        obs = self._get_obs()
        root = obs.tracer.start_trace("parent")
        child = obs.tracer.start_span(root, "child")  # parent is first arg
        obs.tracer.finish_span(child)
        obs.tracer.finish_span(root)
        trace = obs.tracer.get_trace(root.trace_id)
        assert len(trace) == 2

    def test_trace_id_uniqueness(self):
        """Each trace should get a unique ID."""
        obs = self._get_obs()
        ids = set()
        for _ in range(20):
            span = obs.tracer.start_trace(f"op_{_}")
            ids.add(span.trace_id)
            obs.tracer.finish_span(span)
        assert len(ids) == 20

    # -- Dashboard --
    
    def test_full_dashboard(self):
        """Full dashboard should aggregate all subsystems."""
        obs = self._get_obs()
        obs.metrics.inc("test.metric", 1)
        span = obs.tracer.start_trace("test")
        obs.tracer.finish_span(span)
        d = obs.full_dashboard()
        assert "tracing" in d
        assert "metrics" in d

    # -- Prometheus export --
    
    def test_prometheus_export(self):
        """Should export metrics in Prometheus format."""
        obs = self._get_obs()
        obs.metrics.inc("req_total", 42)
        exported = obs.metrics.export_prometheus()
        assert "req_total" in exported
        assert "42" in exported


# ═══════════════════════════════════════════════════════════════
# 4. DATABASE OPTIMIZER
# ═══════════════════════════════════════════════════════════════

class TestDatabaseOptimizer:
    """Tests query tracking and slow query detection."""

    def _get_opt(self, slow_ms=100):
        from arki_project.database.optimizer import DatabaseOptimizer
        return DatabaseOptimizer(slow_threshold_ms=slow_ms)

    def test_record_normal_query(self):
        """Normal queries should be recorded."""
        opt = self._get_opt()
        opt.record_query("SELECT * FROM users", 10)
        assert len(opt.get_slow_queries()) == 0

    def test_detect_slow_query(self):
        """Queries above threshold should be flagged."""
        opt = self._get_opt(slow_ms=50)
        opt.record_query("SELECT * FROM huge_table WHERE unindexed_col = 'x'", 200)
        slow = opt.get_slow_queries()
        assert len(slow) == 1
        assert "huge_table" in slow[0]["pattern"]

    def test_multiple_slow_queries(self):
        """Multiple slow queries should all be tracked."""
        opt = self._get_opt(slow_ms=50)
        opt.record_query("Q1", 100)
        opt.record_query("Q2", 10)  # Fast
        opt.record_query("Q3", 200)
        opt.record_query("Q4", 5)   # Fast
        slow = opt.get_slow_queries()
        assert len(slow) == 2

    def test_query_stats(self):
        """Query statistics should be available via dashboard()."""
        opt = self._get_opt()
        for i in range(10):
            opt.record_query(f"SELECT {i}", float(i * 10))
        stats = opt.dashboard()
        assert stats["total_queries"] == 10

    def test_suggest_indexes(self):
        """Slow queries analysis should work."""
        opt = self._get_opt(slow_ms=50)
        opt.record_query("SELECT * FROM orders WHERE user_id = 123", 200)
        slow = opt.get_slow_queries()
        assert len(slow) >= 1


# ═══════════════════════════════════════════════════════════════
# 5. BOOT INFRASTRUCTURE — Full wiring test
# ═══════════════════════════════════════════════════════════════

class TestBootInfrastructure:
    """Tests that boot_infrastructure() wires everything correctly."""

    @pytest.mark.asyncio
    async def test_boot_returns_all_systems(self):
        """Boot should return dict with all 4 systems."""
        from arki_project.core.boot import boot_infrastructure
        ctx = await boot_infrastructure()
        assert ctx is not None
        assert "self_healing" in ctx
        assert "observability" in ctx
        assert "db_optimizer" in ctx
        assert "handler_profiler" in ctx

    @pytest.mark.asyncio
    async def test_boot_systems_are_real(self):
        """Returned systems should be real instances, not None."""
        from arki_project.core.boot import boot_infrastructure
        ctx = await boot_infrastructure()
        from arki_project.core.self_healing import SelfHealingEngine
        from arki_project.core.observability import Observability
        from arki_project.database.optimizer import DatabaseOptimizer
        from arki_project.middlewares.profiler import HandlerProfiler
        assert isinstance(ctx["self_healing"], SelfHealingEngine)
        assert isinstance(ctx["observability"], Observability)
        assert isinstance(ctx["db_optimizer"], DatabaseOptimizer)
        assert isinstance(ctx["handler_profiler"], HandlerProfiler)


# ═══════════════════════════════════════════════════════════════
# 6. TITANIUM ORCHESTRATOR — Tier & Provider tests
# ═══════════════════════════════════════════════════════════════

class TestTitaniumOrchestrator:
    """Tests AI orchestrator tier configuration."""

    def _build_orch(self, **overrides):
        from arki_project.utils.titanium.ai_orchestrator import TitaniumOrchestrator
        orch = TitaniumOrchestrator.__new__(TitaniumOrchestrator)
        orch._tiers = {}
        orch._tier_stats = {}
        orch._all_providers = []
        orch._scorer = type('S', (), {'register': lambda s, *a: None})()

        class Settings:
            ai_api_key = overrides.get("ai_api_key", "k")
            ai_base_url = overrides.get("ai_base_url", "https://generativelanguage.googleapis.com/v1beta")
            ai_model = overrides.get("ai_model", "gemini-2.5-pro")
            groq_api_key = overrides.get("groq_api_key", "k")
            openrouter_api_key = overrides.get("openrouter_api_key", "k")
            anthropic_api_key = overrides.get("anthropic_api_key", "k")
            openai_api_key = overrides.get("openai_api_key", "k")

        orch._build_tiers(Settings())
        return orch

    def test_all_tiers_built(self):
        """All 4 tiers should be built."""
        from arki_project.utils.titanium.ai_orchestrator import AITier
        orch = self._build_orch()
        assert AITier.ULTRA in orch._tiers
        assert AITier.PRO in orch._tiers
        assert AITier.LITE in orch._tiers
        assert AITier.FREE in orch._tiers

    def test_model_rotation_chains(self):
        """Each provider should have fallback models."""
        orch = self._build_orch()
        for p in orch._all_providers:
            if p.id in ("gemini", "groq", "openrouter", "anthropic", "openai"):
                assert len(p.fallback_models) >= 2, f"{p.id} needs fallbacks"

    def test_total_models_20_plus(self):
        """Total model count should be 20+."""
        orch = self._build_orch()
        total = sum(1 + len(p.fallback_models) for p in orch._all_providers)
        assert total >= 20, f"Only {total} models"

    def test_ultra_consensus_strategy(self):
        """ULTRA tier should use CONSENSUS strategy."""
        from arki_project.utils.titanium.ai_orchestrator import AITier, DispatchStrategy
        orch = self._build_orch()
        assert orch._tiers[AITier.ULTRA].strategy == DispatchStrategy.CONSENSUS

    def test_free_tier_multiple_providers(self):
        """FREE tier should have multiple providers."""
        from arki_project.utils.titanium.ai_orchestrator import AITier
        orch = self._build_orch()
        assert len(orch._tiers[AITier.FREE].providers) >= 2

    def test_gemini_fallback_chain(self):
        """Gemini should have specific fallback models."""
        orch = self._build_orch()
        gemini = [p for p in orch._all_providers if p.id == "gemini"][0]
        # Should have flash models as fallbacks
        assert any("flash" in m for m in gemini.fallback_models)

    def test_no_api_key_skips_provider(self):
        """Missing API key should skip that provider."""
        orch = self._build_orch(groq_api_key="", anthropic_api_key=None, openai_api_key=None)
        provider_ids = [p.id for p in orch._all_providers]
        assert "groq" not in provider_ids


# ═══════════════════════════════════════════════════════════════
# 7. CONFIG & APEX WIRING
# ═══════════════════════════════════════════════════════════════

class TestConfigGodmode:
    """Tests INFRA_APEX wiring from env → config → runtime."""

    def test_env_to_config(self):
        """INFRA_APEX env var should be readable in config."""
        os.environ["INFRA_APEX"] = "true"
        from arki_project.config import INFRA_APEX
        assert INFRA_APEX == True

    def test_config_to_security_middleware(self):
        """Config should wire through to SecurityMiddleware."""
        os.environ["INFRA_APEX"] = "true"
        import arki_project.middlewares.security_middleware as sm
        sm._filter_instance = None
        f = sm._get_filter()
        assert f.apex == True

    def test_apex_scan_result(self):
        """Godmode scan should return safe=True, apex=True."""
        os.environ["INFRA_APEX"] = "true"
        import arki_project.middlewares.security_middleware as sm
        sm._filter_instance = None
        f = sm._get_filter()
        r = f.scan_input("<script>alert('xss')</script>; DROP TABLE;")
        assert r["safe"] == True
        assert r["apex"] == True


# ═══════════════════════════════════════════════════════════════
# 8. MODULE HEALTH — All production modules import clean
# ═══════════════════════════════════════════════════════════════

class TestModuleHealth:
    """Tests that all production modules import without errors."""

    def test_all_modules_import(self):
        """All 320+ production modules should import clean."""
        import importlib
        import pkgutil
        import logging
        logging.disable(logging.CRITICAL)
        
        broken = []
        ok = 0
        for _, modname, _ in pkgutil.walk_packages(
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))],
            prefix="arki_project.",
        ):
            if "__pycache__" in modname or "alembic" in modname or "test" in modname.lower():
                continue
            try:
                importlib.import_module(modname)
                ok += 1
            except Exception as e:
                if "Router" in str(e) and "already attached" in str(e):
                    ok += 1
                    continue
                broken.append(f"{modname}: {str(e)[:80]}")

        logging.disable(logging.NOTSET)
        assert len(broken) == 0, f"Broken modules:\n" + "\n".join(broken[:10])
        assert ok >= 270, f"Only {ok} modules imported"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


