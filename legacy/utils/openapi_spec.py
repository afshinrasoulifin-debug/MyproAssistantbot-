
from __future__ import annotations
"""
utils/openapi_spec.py — OpenAPI 3.1 Spec Generator v19.0
══════════════════════════════════════════════════════════════
Auto-generates OpenAPI spec from registered endpoints.
Serves at /docs (Swagger UI) and /openapi.json (raw spec).
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from config import APP_VERSION as _VERSION
except ImportError:
    _VERSION = "29.0.0"


def generate_openapi_spec() -> Dict[str, Any]:
    """Generate complete OpenAPI 3.1 specification."""
    spec: Dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "ARKI Engine API",
            "description": (
                "Enterprise AI Telegram Bot Engine with multi-provider support, "
                "106 AI models, circuit breakers, and production monitoring."
            ),
            "version": _VERSION,
            "contact": {"name": "ARKI Engine Team"},
            "license": {"name": "Proprietary"},
        },
        "servers": [
            {"url": os.environ.get("HEALTH_BASE_URL", "/"), "description": "Health/Metrics"},
            {"url": os.environ.get("WEBHOOK_BASE_URL", "/"), "description": "Webhook/API"},
        ],
        "paths": {},
        "components": {
            "schemas": _build_schemas(),
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                },
            },
        },
        "tags": [
            {"name": "health", "description": "Health and readiness checks"},
            {"name": "metrics", "description": "Prometheus metrics"},
            {"name": "ai", "description": "AI model endpoints"},
            {"name": "admin", "description": "Admin operations"},
        ],
    }

    # ── Health endpoints ──
    spec["paths"]["/health"] = {
        "get": {
            "tags": ["health"],
            "summary": "Health check",
            "description": "Returns service health status with component checks.",
            "operationId": "getHealth",
            "responses": {
                "200": {
                    "description": "Service healthy",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HealthResponse"},
                        }
                    },
                },
                "503": {
                    "description": "Service unhealthy",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HealthResponse"},
                        }
                    },
                },
            },
        }
    }

    spec["paths"]["/ready"] = {
        "get": {
            "tags": ["health"],
            "summary": "Readiness check",
            "description": "Returns readiness status (all dependencies available).",
            "operationId": "getReady",
            "responses": {
                "200": {
                    "description": "Service ready",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ReadyResponse"},
                        }
                    },
                },
                "503": {"description": "Service not ready"},
            },
        }
    }

    spec["paths"]["/metrics"] = {
        "get": {
            "tags": ["metrics"],
            "summary": "Prometheus metrics",
            "description": "Prometheus-compatible metrics endpoint for scraping.",
            "operationId": "getMetrics",
            "responses": {
                "200": {
                    "description": "Prometheus text format metrics",
                    "content": {
                        "text/plain": {
                            "schema": {"type": "string"},
                        }
                    },
                },
            },
        }
    }

    # ── AI endpoints ──
    spec["paths"]["/api/v1/chat"] = {
        "post": {
            "tags": ["ai"],
            "summary": "Chat completion",
            "description": "Send a message and get AI response. Supports 106 models across all providers.",
            "operationId": "chatCompletion",
            "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ChatRequest"},
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ChatResponse"},
                        }
                    },
                },
                "429": {"description": "Rate limited"},
                "503": {"description": "Provider unavailable (circuit open)"},
            },
        }
    }

    spec["paths"]["/api/v1/models"] = {
        "get": {
            "tags": ["ai"],
            "summary": "List available models",
            "description": "Returns all available AI models with tier, provider, and capability info.",
            "operationId": "listModels",
            "responses": {
                "200": {
                    "description": "Model list",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ModelListResponse"},
                        }
                    },
                },
            },
        }
    }

    spec["paths"]["/api/v1/circuit-breakers"] = {
        "get": {
            "tags": ["admin"],
            "summary": "Circuit breaker status",
            "description": "Returns health status of all circuit breakers.",
            "operationId": "getCircuitBreakers",
            "security": [{"BearerAuth": []}],
            "responses": {
                "200": {
                    "description": "Circuit breaker statuses",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CircuitBreakerResponse"},
                        }
                    },
                },
            },
        }
    }

    # ── Try to add dynamically registered endpoints ──
    try:
        from arki_project.infrastructure.api.api_builder import APIBuilderAgent
        builder = APIBuilderAgent()
        for ep in builder.registry.list_active():
            path = f"/api/v1{ep.path}" if not ep.path.startswith("/api") else ep.path
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            method = ep.method.value.lower()
            spec["paths"][path][method] = {
                "tags": ["ai"],
                "summary": ep.name,
                "description": ep.description,
                "operationId": ep.endpoint_id.replace("-", "_"),
                "security": [{"ApiKeyAuth": []}] if ep.auth_level.value != "none" else [],
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Bad request"},
                    "503": {"description": "Service unavailable"},
                },
            }
    except Exception:
        pass  # API builder not available

    return spec


def _build_schemas() -> Dict[str, Any]:
    """Build reusable OpenAPI schemas."""
    return {
        "HealthResponse": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                "version": {"type": "string"},
                "database": {"type": "object"},
                "uptime_seconds": {"type": "integer"},
                "components": {"type": "object"},
            },
        },
        "ReadyResponse": {
            "type": "object",
            "properties": {
                "ready": {"type": "boolean"},
                "checks": {"type": "object"},
            },
        },
        "ChatRequest": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string", "description": "User message"},
                "model": {"type": "string", "description": "Model key (e.g. gpt-4o, gemini-2.5-pro)"},
                "temperature": {"type": "number", "minimum": 0, "maximum": 2, "default": 0.7},
                "max_tokens": {"type": "integer", "minimum": 1, "maximum": 131072, "default": 65536},
                "user_id": {"type": "integer", "description": "User identifier for context"},
                "system_prompt": {"type": "string", "description": "Optional system prompt override"},
            },
        },
        "ChatResponse": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "AI response text"},
                "model": {"type": "string", "description": "Model that generated the response"},
                "provider": {"type": "string", "description": "Provider used"},
                "latency_ms": {"type": "number", "description": "Response latency in milliseconds"},
                "tokens_used": {"type": "integer"},
                "cached": {"type": "boolean"},
            },
        },
        "ModelListResponse": {
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "name": {"type": "string"},
                            "provider": {"type": "string"},
                            "tier": {"type": "string", "enum": ["fast", "standard", "smart", "power", "ultra"]},
                            "max_tokens": {"type": "integer"},
                        },
                    },
                },
                "total": {"type": "integer"},
            },
        },
        "CircuitBreakerResponse": {
            "type": "object",
            "properties": {
                "breakers": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "state": {"type": "string", "enum": ["closed", "open", "half_open"]},
                            "failure_rate": {"type": "number"},
                            "active_calls": {"type": "integer"},
                        },
                    },
                },
            },
        },
    }


def get_swagger_html() -> str:
    """Return Swagger UI HTML page."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>ARKI Engine API — Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: '/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
            layout: 'BaseLayout'
        });
    </script>
</body>
</html>"""


