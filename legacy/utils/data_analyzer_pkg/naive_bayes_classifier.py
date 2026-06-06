
"""
data_analyzer_pkg/naive_bayes_classifier.py — NaiveBayesClassifier
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class NaiveBayesClassifier:
    """Gaussian Naive Bayes classifier."""

    def __init__(self):
        self._classes: List[str] = []
        self._class_priors: Dict[str, float] = {}
        self._means: Dict[str, List[float]] = {}
        self._vars: Dict[str, List[float]] = {}

    def fit(self, x: List[List[float]], y: List[str]) -> None:
        classes = list(set(y))
        self._classes = classes
        n = len(y)

        for cls in classes:
            cls_data = [x[i] for i in range(n) if y[i] == cls]
            self._class_priors[cls] = len(cls_data) / n

            dims = len(cls_data[0]) if cls_data else 0
            self._means[cls] = [_mean([p[d] for p in cls_data]) for d in range(dims)]
            self._vars[cls] = [
                _variance([p[d] for p in cls_data], ddof=0) + 1e-9
                for d in range(dims)
            ]

    def predict(self, query: List[float]) -> Tuple[str, Dict[str, float]]:
        posteriors: Dict[str, float] = {}

        for cls in self._classes:
            log_prior = math.log(self._class_priors[cls])
            log_likelihood = 0.0

            for d in range(len(query)):
                mu = self._means[cls][d]
                var = self._vars[cls][d]
                log_likelihood += -0.5 * math.log(2 * math.pi * var)
                log_likelihood += -0.5 * ((query[d] - mu) ** 2) / var

            posteriors[cls] = log_prior + log_likelihood

        winner = max(posteriors, key=posteriors.get)
        return winner, posteriors


# ═══════════════════════════════════════════════════════════════════
# TF-IDF Text Vectorization
# ═══════════════════════════════════════════════════════════════════



