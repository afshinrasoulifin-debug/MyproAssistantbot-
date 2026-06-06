"""
arki_project namespace package.
Makes `from arki_project.X import Y` resolve to top-level modules.
"""
import os as _os

# Add project root to __path__ so arki_project.config → config.py, etc.
_project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _project_root not in __path__:
    __path__.insert(0, _project_root)
