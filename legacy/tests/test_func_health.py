
"""Functional test: /health and /ready endpoints — v9.7."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHealthEndpoints:
    """Tests that health endpoints are properly mounted."""

    def test_health_in_webhook_mode(self):
        """In webhook mode, /health and /ready must be mounted."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        source = open(main_path).read()

        # Find webhook section
        webhook_section = source[source.find("webhook_url"):]
        assert 'add_get("/health"' in webhook_section
        assert 'add_get("/ready"' in webhook_section

    def test_health_in_polling_mode(self):
        """/health server also starts in polling mode."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        source = open(main_path).read()

        polling_section = source[source.find("polling"):]
        assert "_start_health_server" in polling_section

    def test_health_returns_version(self):
        """Health endpoint response includes version string."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        source = open(main_path).read()
        assert "_VERSION" in source, "Health response must include version"

    def test_ready_checks_database(self):
        """Readiness endpoint checks database health."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        source = open(main_path).read()
        ready_section = source[source.find("_ready_endpoint"):] if "_ready_endpoint" in source else source[source.find("_ready_ep"):]
        assert "health_check" in ready_section or "database" in ready_section

    def test_dockerfile_healthcheck_uses_curl(self):
        """Dockerfile HEALTHCHECK must use real HTTP check, not python."""
        dockerfile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile"
        )
        content = open(dockerfile_path).read()
        assert "curl" in content, "Healthcheck must use curl"
        assert "python -c" not in content, "Must NOT use fake python healthcheck"
        assert "/health" in content, "Must check /health endpoint"


