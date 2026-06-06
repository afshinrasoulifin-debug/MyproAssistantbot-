
"""
text_transform_pkg/obfuscation_technique.py — ObfuscationTechnique
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ObfuscationTechnique(str, Enum):
    """Available obfuscation techniques."""
    LEETSPEAK = "leetspeak"
    UNICODE = "unicode"
    ZWJ = "zwj"
    MIXEDCASE = "mixedcase"
    PHONETIC = "phonetic"
    RANDOM = "random"




