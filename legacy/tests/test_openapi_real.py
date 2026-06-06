
"""
tests/test_openapi_real.py — OpenAPI Spec Tests
════════════════════════════════════════════════
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.openapi_spec import generate_openapi_spec, get_swagger_html

import pytest


class TestOpenAPISpec:

    def test_generates_valid_spec(self):
        spec = generate_openapi_spec()
        assert spec["openapi"] == "3.1.0"
        assert "info" in spec
        assert "paths" in spec
        assert "components" in spec

    def test_has_health_endpoint(self):
        spec = generate_openapi_spec()
        assert "/health" in spec["paths"]
        assert "get" in spec["paths"]["/health"]

    def test_has_metrics_endpoint(self):
        spec = generate_openapi_spec()
        assert "/metrics" in spec["paths"]

    def test_has_chat_endpoint(self):
        spec = generate_openapi_spec()
        assert "/api/v1/chat" in spec["paths"]
        assert "post" in spec["paths"]["/api/v1/chat"]

    def test_has_models_endpoint(self):
        spec = generate_openapi_spec()
        assert "/api/v1/models" in spec["paths"]

    def test_schemas_defined(self):
        spec = generate_openapi_spec()
        schemas = spec["components"]["schemas"]
        assert "HealthResponse" in schemas
        assert "ChatRequest" in schemas
        assert "ChatResponse" in schemas
        assert "ModelListResponse" in schemas

    def test_security_schemes(self):
        spec = generate_openapi_spec()
        security = spec["components"]["securitySchemes"]
        assert "BearerAuth" in security
        assert "ApiKeyAuth" in security

    def test_chat_request_schema(self):
        spec = generate_openapi_spec()
        chat_req = spec["components"]["schemas"]["ChatRequest"]
        assert "message" in chat_req["properties"]
        assert "model" in chat_req["properties"]
        assert "temperature" in chat_req["properties"]

    def test_swagger_html(self):
        html = get_swagger_html()
        assert "swagger-ui" in html.lower()
        assert "openapi.json" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


