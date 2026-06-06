
from __future__ import annotations
"""
tg_bot/utils/prompt_versioning.py — Prompt Version Management v9.4
Track and version system prompts for A/B testing and rollback.
"""
import hashlib
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    name: str
    version: str
    content: str
    created_at: float = 0.0
    hash: str = ""
    active: bool = True
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self) -> Any:
        if not self.created_at:
            self.created_at = time.time()
        if not self.hash:
            self.hash = hashlib.md5(self.content.encode()).hexdigest()[:8]


class PromptVersionManager:
    """Manage prompt versions with A/B testing support."""

    def __init__(self) -> None:
        self._prompts: Dict[str, List[PromptVersion]] = {}
        self._active: Dict[str, str] = {}  # name -> active version

    def register(self, name: str, version: str, content: str, **metadata) -> PromptVersion:
        """Register a new prompt version."""
        pv = PromptVersion(name=name, version=version, content=content, metadata=metadata)
        if name not in self._prompts:
            self._prompts[name] = []
        self._prompts[name].append(pv)
        self._active[name] = version
        return pv

    def get_active(self, name: str) -> Optional[str]:
        """Get the active prompt content for a given name."""
        version = self._active.get(name)
        if not version or name not in self._prompts:
            return None
        for pv in self._prompts[name]:
            if pv.version == version:
                return pv.content
        return None

    def rollback(self, name: str) -> bool:
        """Rollback to previous version."""
        versions = self._prompts.get(name, [])
        if len(versions) < 2:
            return False
        self._active[name] = versions[-2].version
        return True

    def list_versions(self, name: str) -> List[Dict]:
        """List all versions of a prompt."""
        return [
            {"version": pv.version, "hash": pv.hash, "active": pv.version == self._active.get(name)}
            for pv in self._prompts.get(name, [])
        ]


_manager = None

def get_prompt_manager() -> PromptVersionManager:
    global _manager
    if _manager is None:
        _manager = PromptVersionManager()
    return _manager


