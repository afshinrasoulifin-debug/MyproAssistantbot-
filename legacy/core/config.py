
"""
core/config.py — Re-export from root config and architecture config for backward compatibility.
"""
from arki_project.config import Settings as Config
from arki_project.config import Settings, ConfigError

__all__ = ["Config", "Settings", "ConfigError"]


