
"""
data_analyzer_pkg/tf_idf_result.py — TfIdfResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class TfIdfResult:
    """TF-IDF vectorization result."""
    vocabulary: Dict[str, int]
    idf_scores: Dict[str, float]
    tfidf_matrix: List[Dict[str, float]]
    top_terms: List[Tuple[str, float]]


# ═══════════════════════════════════════════════════════════════════
# Data Ingestion & Cleaning
# ═══════════════════════════════════════════════════════════════════



