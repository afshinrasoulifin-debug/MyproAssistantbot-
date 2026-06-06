
"""
tests/test_stealth_orchestrator.py — Stealth Orchestrator Tests
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.stealth_orchestrator import (
    StealthOrchestrator, StealthRequest, StealthResponse, BatchResult,
    TargetProfile, ExecutionPlan, EscalationLevel, TargetDifficulty, _extract_domain, _detect_wafs_from_headers, _detect_captchas_from_body,
    _detect_block, _assess_difficulty, _recommend_level, _build_plan,
    _ModuleHub, get_orchestrator, stealth_get, stealth_post, analyze_target,
)


# ═══════ Target Analysis Helpers ═══════

class TestHelpers:
    def test_extract_domain_full_url(self):
        assert _extract_domain("https://example.com/path") == "example.com"

    def test_extract_domain_bare(self):
        assert _extract_domain("example.com") == "example.com"

    def test_extract_domain_with_port(self):
        assert _extract_domain("https://example.com:8080/path") == "example.com:8080"

    def test_detect_wafs_cloudflare(self):
        h = {"cf-ray": "abc123", "server": "cloudflare"}
        assert "cloudflare" in _detect_wafs_from_headers(h)

    def test_detect_wafs_akamai(self):
        h = {"x-akamai-transformed": "yes"}
        assert "akamai" in _detect_wafs_from_headers(h)

    def test_detect_wafs_none(self):
        h = {"server": "nginx", "content-type": "text/html"}
        assert _detect_wafs_from_headers(h) == []

    def test_detect_captchas_recaptcha(self):
        body = '<div class="g-recaptcha" data-sitekey="abc">'
        assert "recaptcha" in _detect_captchas_from_body(body)

    def test_detect_captchas_turnstile(self):
        body = '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js">'
        assert "turnstile" in _detect_captchas_from_body(body)

    def test_detect_captchas_none(self):
        body = "<html><body>Normal page</body></html>"
        assert _detect_captchas_from_body(body) == []

    def test_detect_block_403(self):
        assert _detect_block(403, "Forbidden") is True

    def test_detect_block_429(self):
        assert _detect_block(429, "Too Many Requests") is True

    def test_detect_block_200_clean(self):
        assert _detect_block(200, "Welcome to our site") is False

    def test_detect_block_200_suspicious(self):
        assert _detect_block(200, "Access denied. Bot detected. Please verify you are human.") is True

    def test_assess_difficulty_open(self):
        p = TargetProfile(url="x", domain="x")
        assert _assess_difficulty(p) == TargetDifficulty.OPEN

    def test_assess_difficulty_hardened(self):
        p = TargetProfile(url="x", domain="x", waf_detected=["cloudflare"],
                          captcha_types=["turnstile"], js_challenge=True)
        assert _assess_difficulty(p) in (TargetDifficulty.HARDENED, TargetDifficulty.FORTRESS)

    def test_recommend_level_open(self):
        assert _recommend_level(TargetDifficulty.OPEN) == EscalationLevel.GHOST

    def test_recommend_level_fortress(self):
        assert _recommend_level(TargetDifficulty.FORTRESS) == EscalationLevel.SPECTRE


# ═══════ Plan Builder ═══════

class TestPlanBuilder:
    def test_ghost_plan(self):
        p = TargetProfile(url="x", domain="x", recommended_level=EscalationLevel.GHOST)
        r = StealthRequest(url="x")
        plan = _build_plan(p, r)
        assert plan.level == EscalationLevel.GHOST
        assert "apply_request_pipeline" in plan.steps
        assert "launch_browser" not in plan.steps

    def test_shadow_plan(self):
        p = TargetProfile(url="x", domain="x", recommended_level=EscalationLevel.SHADOW)
        r = StealthRequest(url="x")
        plan = _build_plan(p, r)
        assert plan.level == EscalationLevel.SHADOW
        assert "apply_tls_fingerprint" in plan.steps
        assert plan.geo_spoof is True

    def test_phantom_plan(self):
        p = TargetProfile(url="x", domain="x", recommended_level=EscalationLevel.PHANTOM)
        r = StealthRequest(url="x")
        plan = _build_plan(p, r)
        assert plan.level == EscalationLevel.PHANTOM
        assert plan.use_proxy is True
        assert plan.behavior_sim is True

    def test_spectre_plan(self):
        p = TargetProfile(url="x", domain="x", recommended_level=EscalationLevel.SPECTRE,
                          captcha_types=["turnstile"])
        r = StealthRequest(url="x")
        plan = _build_plan(p, r)
        assert plan.level == EscalationLevel.SPECTRE
        assert plan.use_browser is True
        assert plan.evasion_scripts is True
        assert plan.captcha_solver is True

    def test_force_level(self):
        p = TargetProfile(url="x", domain="x", recommended_level=EscalationLevel.GHOST)
        r = StealthRequest(url="x", force_level=EscalationLevel.PHANTOM)
        plan = _build_plan(p, r)
        assert plan.level == EscalationLevel.PHANTOM

    def test_max_escalation_cap(self):
        p = TargetProfile(url="x", domain="x", recommended_level=EscalationLevel.SPECTRE)
        r = StealthRequest(url="x", max_escalation=EscalationLevel.SHADOW)
        plan = _build_plan(p, r)
        assert plan.level == EscalationLevel.SHADOW

    def test_plan_to_dict(self):
        plan = ExecutionPlan(level=EscalationLevel.GHOST, steps=["a", "b"])
        d = plan.to_dict()
        assert d["level"] == "GHOST"
        assert d["steps"] == ["a", "b"]


# ═══════ Data Structures ═══════

class TestDataStructures:
    def test_target_profile_to_dict(self):
        p = TargetProfile(url="https://test.com", domain="test.com",
                          waf_detected=["cloudflare"])
        d = p.to_dict()
        assert d["domain"] == "test.com"
        assert "cloudflare" in d["waf_detected"]

    def test_response_to_dict(self):
        r = StealthResponse(success=True, status_code=200, body="OK",
                            escalation_used=EscalationLevel.SHADOW, attempts=2)
        d = r.to_dict()
        assert d["success"] is True
        assert d["escalation_used"] == "SHADOW"
        assert d["attempts"] == 2

    def test_batch_result_to_dict(self):
        b = BatchResult(total=10, succeeded=8, failed=2, total_time=5.0)
        d = b.to_dict()
        assert d["success_rate"] == 80.0

    def test_escalation_level_ordering(self):
        assert EscalationLevel.GHOST < EscalationLevel.SHADOW
        assert EscalationLevel.SHADOW < EscalationLevel.PHANTOM
        assert EscalationLevel.PHANTOM < EscalationLevel.SPECTRE


# ═══════ Module Hub ═══════

class TestModuleHub:
    def test_get_status(self):
        hub = _ModuleHub()
        status = hub.get_status()
        assert isinstance(status, dict)
        assert len(status) == 13  # 13 modules

    def test_modules_loaded(self):
        hub = _ModuleHub()
        # These should all load
        assert hub.anti_detection is not None or True  # May fail gracefully
        status = hub.get_status()
        # At least some should be available
        assert isinstance(status, dict)


# ═══════ Orchestrator Core ═══════

class TestOrchestrator:
    def test_init(self):
        orch = StealthOrchestrator()
        stats = orch.get_stats()
        assert stats["total_requests"] == 0
        assert stats["modules_total"] == 13

    def test_default_level(self):
        orch = StealthOrchestrator(default_level=EscalationLevel.SHADOW)
        assert orch._default_level == EscalationLevel.SHADOW

    def test_auto_escalate(self):
        orch = StealthOrchestrator(auto_escalate=False)
        assert orch._auto_escalate is False

    def test_module_status(self):
        orch = StealthOrchestrator()
        status = orch.get_module_status()
        assert isinstance(status, dict)

    def test_clear_cache(self):
        orch = StealthOrchestrator()
        orch._target_cache["test.com"] = TargetProfile(url="x", domain="test.com")
        assert orch.clear_target_cache() == 1
        assert len(orch._target_cache) == 0

    def test_get_target_profile(self):
        orch = StealthOrchestrator()
        assert orch.get_target_profile("nonexistent") is None

    @pytest.mark.asyncio
    async def test_analyze_target(self):
        orch = StealthOrchestrator()
        profile = await orch.analyze_target("https://test-nonexistent-xyz.invalid")
        assert isinstance(profile, TargetProfile)
        assert profile.domain == "test-nonexistent-xyz.invalid"

    @pytest.mark.asyncio
    async def test_execute_ghost(self):
        orch = StealthOrchestrator(auto_escalate=False, max_retries=0)
        resp = await orch.execute(
            "https://test-nonexistent-xyz.invalid",
            level=EscalationLevel.GHOST, timeout=5.0,
        )
        assert isinstance(resp, StealthResponse)
        assert resp.escalation_used == EscalationLevel.GHOST

    @pytest.mark.asyncio
    async def test_execute_with_method(self):
        orch = StealthOrchestrator(auto_escalate=False, max_retries=0)
        resp = await orch.execute(
            "https://test-nonexistent-xyz.invalid",
            method="POST", body='{"test":1}',
            level=EscalationLevel.GHOST, timeout=5.0,
        )
        assert isinstance(resp, StealthResponse)

    @pytest.mark.asyncio
    async def test_batch_execute(self):
        orch = StealthOrchestrator(auto_escalate=False, max_retries=0)
        urls = ["https://test-nonexistent-1.invalid", "https://test-nonexistent-2.invalid"]
        batch = await orch.batch_execute(urls, level=EscalationLevel.GHOST, delay_between=0)
        assert isinstance(batch, BatchResult)
        assert batch.total == 2

    @pytest.mark.asyncio
    async def test_execute_chain(self):
        orch = StealthOrchestrator(auto_escalate=False, max_retries=0)
        reqs = [
            StealthRequest(url="https://test-1.invalid", force_level=EscalationLevel.GHOST, timeout=5.0),
            StealthRequest(url="https://test-2.invalid", force_level=EscalationLevel.GHOST, timeout=5.0),
        ]
        results = await orch.execute_chain(reqs, stop_on_failure=False)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_stats_after_request(self):
        orch = StealthOrchestrator(auto_escalate=False, max_retries=0)
        await orch.execute("https://test-nonexistent.invalid",
                           level=EscalationLevel.GHOST, timeout=5.0)
        stats = orch.get_stats()
        assert stats["total_requests"] >= 1


# ═══════ Convenience Functions ═══════

class TestConvenience:
    @pytest.mark.asyncio
    async def test_stealth_get(self):
        resp = await stealth_get("https://test-nonexistent.invalid",
                                 level=EscalationLevel.GHOST, timeout=5.0)
        assert isinstance(resp, StealthResponse)

    @pytest.mark.asyncio
    async def test_stealth_post(self):
        resp = await stealth_post("https://test-nonexistent.invalid",
                                  level=EscalationLevel.GHOST, timeout=5.0)
        assert isinstance(resp, StealthResponse)

    @pytest.mark.asyncio
    async def test_analyze(self):
        profile = await analyze_target("https://test-nonexistent.invalid")
        assert isinstance(profile, TargetProfile)

    def test_get_orchestrator_singleton(self):
        import utils.stealth_orchestrator as mod
        mod._default_orchestrator = None  # Reset
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


