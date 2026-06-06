
"""
text_transform_pkg/transform_record.py — TransformRecord
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class TransformRecord(TypedDict):
    """Record of a single word transformation."""
    original: str
    transformed: str
    technique: str




