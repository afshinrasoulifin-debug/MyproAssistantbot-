
from __future__ import annotations
"""
architecture.helper.integration_helper — IntegrationHelper, SetupHelper, DeploymentHelper
═══════════════════════════════════════════════════════════════════════════════════════
Integration, setup, and deployment helpers.
Covers: integration-helper, setup-helper, deployment-helper
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class IntegrationHelper:
    """Helper for managing third-party integrations."""
    def __init__(self) -> None:
        self._configs: Dict[str, Dict[str, Any]] = {}

    def configure(self, service: str, **kwargs) -> None:
        self._configs[service] = kwargs

    def get_config(self, service: str) -> Dict[str, Any]:
        return self._configs.get(service, {})

    def validate(self, service: str) -> bool:
        config = self._configs.get(service, {})
        required = config.get("_required_fields", [])
        return all(config.get(f) for f in required)

class SetupHelper:
    """Helper for initial system setup and configuration."""
    def __init__(self) -> None:
        self._steps: List[dict] = []
        self._completed: set = set()

    def add_step(self, name: str, description: str, fn=None) -> None:
        self._steps.append({"name": name, "description": description, "fn": fn})

    def run_step(self, name: str) -> bool:
        for step in self._steps:
            if step["name"] == name and step.get("fn"):
                try:
                    step["fn"]()
                    self._completed.add(name)
                    return True
                except Exception:
                    return False
        return False

    @property
    def progress(self) -> Dict[str, Any]:
        return {"total": len(self._steps), "completed": len(self._completed),
                "remaining": [s["name"] for s in self._steps if s["name"] not in self._completed]}

class DeploymentHelper:
    """Helper for deployment operations."""
    @staticmethod
    def validate_environment(required_vars: List[str]) -> Dict[str, bool]:
        import os
        return {var: var in os.environ for var in required_vars}

    @staticmethod
    def check_dependencies(packages: List[str]) -> Dict[str, bool]:
        results = {}
        for pkg in packages:
            try:
                __import__(pkg)
                results[pkg] = True
            except ImportError:
                results[pkg] = False
        return results


