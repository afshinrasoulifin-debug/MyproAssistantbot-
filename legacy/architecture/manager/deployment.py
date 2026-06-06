
from __future__ import annotations
"""
architecture.manager.deployment — DeploymentManager, UpdateManager, PackageManager, ArtifactManager
══════════════════════════════════════════════════════════════════════════════════════════════════
Deployment, package, and artifact lifecycle management.
Covers: deployment-manager, update-manager, package-manager, artifact-manager
"""
import logging, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class Deployment:
    deploy_id: str
    version: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class DeploymentManager:
    """Track and manage deployments."""
    def __init__(self) -> None:
        self._deployments: Dict[str, Deployment] = {}
        self._current: Optional[str] = None

    def create(self, deploy_id: str, version: str, **metadata) -> Deployment:
        dep = Deployment(deploy_id=deploy_id, version=version, metadata=metadata)
        self._deployments[deploy_id] = dep
        return dep

    def activate(self, deploy_id: str) -> bool:
        dep = self._deployments.get(deploy_id)
        if dep:
            dep.status = "active"
            dep.completed_at = time.time()
            self._current = deploy_id
            return True
        return False

    def rollback(self, deploy_id: str) -> bool:
        dep = self._deployments.get(deploy_id)
        if dep:
            dep.status = "rolled_back"
            return True
        return False

    @property
    def current(self) -> Optional[Deployment]:
        return self._deployments.get(self._current) if self._current else None

    @property
    def stats(self) -> Dict[str, Any]:
        return {"total": len(self._deployments), "current": self._current}

class UpdateManager(DeploymentManager):
    """Deployment manager with update-specific logic."""
    def __init__(self):
        self._registry = {}
        self._active = True

    def register(self, name, component):
        self._registry[name] = component

    def get(self, name):
        return self._registry.get(name)

    def list_all(self):
        return list(self._registry.keys())

@dataclass
class Package:
    name: str
    version: str
    dependencies: List[str] = field(default_factory=list)
    installed: bool = False

class PackageManager:
    """Package dependency management."""
    def __init__(self) -> None:
        self._packages: Dict[str, Package] = {}

    def register(self, name: str, version: str, deps: Optional[List[str]] = None) -> Package:
        pkg = Package(name=name, version=version, dependencies=deps or [])
        self._packages[name] = pkg
        return pkg

    def install(self, name: str) -> bool:
        pkg = self._packages.get(name)
        if pkg:
            # Check dependencies
            for dep in pkg.dependencies:
                dep_pkg = self._packages.get(dep)
                if not dep_pkg or not dep_pkg.installed:
                    logger.warning("Missing dependency: %s for %s", dep, name)
            pkg.installed = True
            return True
        return False

    def installed_packages(self) -> List[Package]:
        return [p for p in self._packages.values() if p.installed]

class ArtifactManager:
    """Manage build artifacts and outputs."""
    def __init__(self) -> None:
        self._artifacts: Dict[str, Dict[str, Any]] = {}

    def store(self, name: str, path: str, **metadata) -> None:
        self._artifacts[name] = {"path": path, "time": time.time(), **metadata}

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._artifacts.get(name)

    def list_artifacts(self) -> List[str]:
        return list(self._artifacts.keys())


