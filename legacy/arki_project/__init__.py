
from __future__ import annotations

"""Compatibility package alias for the flat-source ARKI project layout.

The historical source tree stores packages such as ``utils`` and ``handlers`` at
repository root, while runtime imports use the stable prefix ``arki_project``.
This package bridges those layouts by adding the repository root to the package
search path, so imports like ``arki_project.utils.tool_hub`` resolve without
moving the whole tree.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_root_text = str(_ROOT)
if _root_text not in __path__:
    __path__.append(_root_text)

__all__: list[str] = []


