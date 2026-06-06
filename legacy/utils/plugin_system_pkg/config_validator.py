
"""
plugin_system_pkg/config_validator.py — ConfigValidator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ConfigValidator:
    """Validate plugin configuration against a schema."""

    TYPES = {"string", "number", "boolean", "array", "object"}

    @classmethod
    def validate(cls, config: Dict[str, Any],
                 schema: Dict[str, Any]) -> List[str]:
        """
        Validate config against schema.

        Schema format:
        {
            "field_name": {
                "type": "string",
                "required": true,
                "default": "value",
                "min": 0,
                "max": 100,
                "pattern": "regex",
                "enum": ["a", "b"]
            }
        }
        """
        errors: List[str] = []

        for field_name, field_schema in schema.items():
            value = config.get(field_name)
            required = field_schema.get("required", False)

            # Required check
            if value is None:
                if required:
                    errors.append(f"Missing required field: {field_name}")
                continue

            # Type check
            expected_type = field_schema.get("type")
            if expected_type:
                if not cls._check_type(value, expected_type):
                    errors.append(
                        f"Field '{field_name}': expected {expected_type}, "
                        f"got {type(value).__name__}"
                    )
                    continue

            # Range check
            if isinstance(value, (int, float)):
                if "min" in field_schema and value < field_schema["min"]:
                    errors.append(
                        f"Field '{field_name}': value {value} below "
                        f"minimum {field_schema['min']}"
                    )
                if "max" in field_schema and value > field_schema["max"]:
                    errors.append(
                        f"Field '{field_name}': value {value} above "
                        f"maximum {field_schema['max']}"
                    )

            # Pattern check
            if isinstance(value, str) and "pattern" in field_schema:
                if not re.match(field_schema["pattern"], value):
                    errors.append(
                        f"Field '{field_name}': doesn't match pattern "
                        f"'{field_schema['pattern']}'"
                    )

            # Enum check
            if "enum" in field_schema and value not in field_schema["enum"]:
                errors.append(
                    f"Field '{field_name}': value '{value}' not in "
                    f"allowed values {field_schema['enum']}"
                )

        return errors

    @classmethod
    def apply_defaults(cls, config: Dict[str, Any],
                       schema: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values from schema."""
        result = dict(config)
        for field_name, field_schema in schema.items():
            if field_name not in result and "default" in field_schema:
                result[field_name] = field_schema["default"]
        return result

    @classmethod
    def _check_type(cls, value: Any, expected: str) -> bool:
        """Check if a value matches an expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_type = type_map.get(expected)
        if expected_type is None:
            return True
        return isinstance(value, expected_type)


# ═══════════════════════════════════════════════════════════════════
# Plugin Manager (Main Interface)
# ═══════════════════════════════════════════════════════════════════





