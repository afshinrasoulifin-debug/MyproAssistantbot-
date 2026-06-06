
"""
api_builder_pkg/open_a_p_i_generator.py — OpenAPIGenerator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class OpenAPIGenerator:
    """Generates OpenAPI 3.1 specifications from endpoint definitions."""

    @staticmethod
    def generate(endpoints: List[EndpointDefinition],
                 title: str = "Arki Engine API",
                 version: str = "29.0.0") -> Dict[str, Any]:
        """Generate full OpenAPI spec."""

        paths: Dict[str, Any] = {}
        tags_set: Set[str] = set()

        for ep in endpoints:
            if ep.status == EndpointStatus.DISABLED:
                continue

            path_key = f"/{ep.version}/{ep.path}"
            method_key = ep.method.value.lower()

            # Build request schema
            properties = {}
            required = []
            for p in ep.parameters:
                prop: Dict[str, Any] = {"type": p.param_type, "description": p.description}
                if p.default is not None:
                    prop["default"] = p.default
                if p.enum:
                    prop["enum"] = p.enum
                if p.min_value is not None:
                    prop["minimum"] = p.min_value
                if p.max_value is not None:
                    prop["maximum"] = p.max_value
                if p.pattern:
                    prop["pattern"] = p.pattern
                properties[p.name] = prop
                if p.required:
                    required.append(p.name)

            operation: Dict[str, Any] = {
                "operationId": ep.endpoint_id,
                "summary": ep.name,
                "description": ep.description,
                "tags": ep.tags or ["general"],
                "security": [{"BearerAuth": []}] if ep.auth_level != AuthLevel.NONE else [],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {"application/json": {"schema": ep.response_schema or {"type": "object"}}},
                    },
                    "400": {"description": "Bad Request"},
                    "401": {"description": "Unauthorized"},
                    "429": {"description": "Rate Limited"},
                    "500": {"description": "Server Error"},
                },
            }

            if ep.method in (HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH) and properties:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": properties,
                                "required": required,
                            }
                        }
                    }
                }

            if ep.status == EndpointStatus.DEPRECATED:
                operation["deprecated"] = True

            if path_key not in paths:
                paths[path_key] = {}
            paths[path_key][method_key] = operation
            tags_set.update(ep.tags or ["general"])

        return {
            "openapi": "3.1.0",
            "info": {
                "title": title,
                "version": version,
                "description": (
                    "Arki Engine v10.4 TITANIUM — 72 AI Models, Agent Executor, "
                    "ULTRAPLINIAN Race, CONSORTIUM Hive-Mind, Dynamic API Builder"
                ),
                "contact": {"name": "Arki Engine"},
            },
            "servers": [
                {"url": os.environ.get("APEX_URL", "http://localhost:7860"), "description": "Local APEX"},
                {"url": os.environ.get("ARKI_URL", "http://localhost:8000"), "description": "Arki Main"},
            ],
            "paths": paths,
            "tags": [{"name": t} for t in sorted(tags_set)],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "description": "API key via Authorization: Bearer <key>",
                    }
                }
            },
        }




# ═══════════════════════════════════════════════════════════════════
# WebSocket Manager — Real bidirectional streaming
# ═══════════════════════════════════════════════════════════════════



