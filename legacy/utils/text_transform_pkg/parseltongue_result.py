
"""
text_transform_pkg/parseltongue_result.py — ParseltongueResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ParseltongueResult(TypedDict):
    """Complete result from parseltongue_obfuscate."""
    original: str
    transformed: str
    triggers_found: List[str]
    technique_used: str
    transformations: List[TransformRecord]


# ═══════════════════ TRIGGER WORDS (36 defaults, 7 categories) ═══════════════════



