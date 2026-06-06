
"""Functional tests for middleware — v9.6."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMiddlewareFunctional:
    """Functional tests for middleware registration and logic."""

    def test_all_middlewares_registered_in_main(self):
        """All critical middlewares are registered in main.py."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        content = open(main_path).read()
        required = [
            "PlanEnforcementMiddleware",
            "CallbackTimeoutMiddleware",
            "MediaGroupMiddleware",
            "DedupMiddleware",
        ]
        for mw in required:
            assert mw in content, f"{mw} must be registered in main.py"

    def test_plan_enforcement_has_token_limits(self):
        """PlanEnforcementMiddleware checks daily token budget."""
        mw_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "middlewares", "plan_enforcement_middleware.py"
        )
        content = open(mw_path).read()
        assert "PLAN_LIMITS" in content or "daily_token" in content
        assert "free" in content and "pro" in content

    def test_idempotency_has_redis(self):
        """IdempotencyMiddleware supports Redis backend."""
        mw_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "middlewares", "idempotency_middleware.py"
        )
        content = open(mw_path).read()
        assert "redis" in content.lower(), "Must support Redis backend"

    def test_health_endpoints_mounted(self):
        """Both /health and /ready endpoints are mounted in main.py."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        content = open(main_path).read()
        assert "/health" in content, "/health endpoint must be mounted"
        assert "/ready" in content, "/ready endpoint must be mounted"


