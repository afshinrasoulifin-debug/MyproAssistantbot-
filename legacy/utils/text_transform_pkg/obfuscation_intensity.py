
"""
text_transform_pkg/obfuscation_intensity.py — ObfuscationIntensity
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ObfuscationIntensity(str, Enum):
    """Transformation intensity levels."""
    LIGHT = "light"    # 1 character
    MEDIUM = "medium"  # ~half of characters
    HEAVY = "heavy"    # all characters




