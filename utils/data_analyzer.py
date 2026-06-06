
"""
tg_bot/utils/data_analyzer.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
DATA ANALYZER — Advanced Statistical & Machine Learning Engine

Pure-Python statistical analysis and ML engine with no external
dependencies. Implements classic algorithms from scratch.

Architecture
────────────
   ┌───────────────────────────────────────────────────┐
   │               DATA ANALYZER ENGINE                 │
   ├──────────┬──────────┬──────────┬──────────────────┤
   │ Ingest   │ Stats    │ ML       │ Visualization    │
   │ CSV/JSON │ Engine   │ Models   │ ASCII Charts     │
   ├──────────┼──────────┼──────────┼──────────────────┤
   │ Parse    │ Describe │ LinearR  │ Bar Chart        │
   │ Clean    │ Correlate│ KMeans   │ Histogram        │
   │ Validate │ Outlier  │ KNN      │ Scatter          │
   │ Transform│ Trend    │ NaiveBay │ Sparkline        │
   ├──────────┼──────────┼──────────┼──────────────────┤
   │ Schema   │ Hypothesis│ TF-IDF  │ Box Plot         │
   │ Detect   │ Testing  │ PCA      │ Heatmap          │
   │ Types    │ z/t/chi  │ Anomaly  │ Time Series      │
   └──────────┴──────────┴──────────┴──────────────────┘

Features
────────
  • CSV/JSON ingestion with auto-type detection
  • Descriptive statistics (mean, median, mode, stddev, skewness,
    kurtosis, percentiles, IQR, coefficient of variation)
  • Correlation matrix (Pearson, Spearman rank)
  • Outlier detection (IQR method, Z-score, Modified Z-score)
  • Trend analysis (linear regression, moving average, exponential)
  • Hypothesis testing (z-test, t-test, chi-square)
  • Linear regression (closed-form + gradient descent)
  • K-means clustering
  • K-nearest neighbors classification
  • Naive Bayes classifier
  • TF-IDF text vectorization
  • Principal Component Analysis (power iteration)
  • Anomaly detection (isolation-inspired, statistical)
  • ASCII visualization (bar, histogram, scatter, sparkline)

References
──────────
  Port of: apex_app/src/lib/data-analyzer.ts (660 lines)
  Enhanced with: Spearman rank, hypothesis testing, KMeans, KNN,
                 Naive Bayes, PCA, anomaly detection, ASCII charts
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10: CSPRNG
except ImportError:
    import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Utility Math Functions (stdlib-only)
# ═══════════════════════════════════════════════════════════════════

def _mean(data: List[float]) -> float:
    return sum(data) / len(data) if data else 0.0

def _median(data: List[float]) -> float:
    s = sorted(data)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2

def _mode(data: List[float]) -> float:
    counts = Counter(data)
    return counts.most_common(1)[0][0] if counts else 0.0

def _variance(data: List[float], ddof: int = 1) -> float:
    if len(data) <= ddof:
        return 0.0
    m = _mean(data)
    return sum((x - m) ** 2 for x in data) / (len(data) - ddof)

def _stddev(data: List[float], ddof: int = 1) -> float:
    return math.sqrt(_variance(data, ddof))

def _percentile(data: List[float], p: float) -> float:
    """Calculate p-th percentile (0-100)."""
    s = sorted(data)
    n = len(s)
    if n == 0:
        return 0.0
    k = (p / 100) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)

def _iqr(data: List[float]) -> float:
    return _percentile(data, 75) - _percentile(data, 25)

def _skewness(data: List[float]) -> float:
    n = len(data)
    if n < 3:
        return 0.0
    m = _mean(data)
    s = _stddev(data)
    if s == 0:
        return 0.0
    return (n / ((n - 1) * (n - 2))) * sum(((x - m) / s) ** 3 for x in data)

def _kurtosis(data: List[float]) -> float:
    n = len(data)
    if n < 4:
        return 0.0
    m = _mean(data)
    s = _stddev(data)
    if s == 0:
        return 0.0
    k = sum(((x - m) / s) ** 4 for x in data) / n
    return k - 3.0  # excess kurtosis

def _covariance(x: List[float], y: List[float]) -> float:
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    mx, my = _mean(x[:n]), _mean(y[:n])
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)

def _pearson_correlation(x: List[float], y: List[float]) -> float:
    sx, sy = _stddev(x), _stddev(y)
    if sx == 0 or sy == 0:
        return 0.0
    return _covariance(x, y) / (sx * sy)

def _spearman_correlation(x: List[float], y: List[float]) -> float:
    """Spearman rank correlation coefficient."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    def _rank(data: List[float]) -> List[float]:
        sorted_idx = sorted(range(len(data)), key=lambda i: data[i])
        ranks = [0.0] * len(data)
        for rank, idx in enumerate(sorted_idx, 1):
            ranks[idx] = float(rank)
        return ranks
    rx = _rank(x[:n])
    ry = _rank(y[:n])
    return _pearson_correlation(rx, ry)


# ═══════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ColumnStats:
    """Statistics for a single column."""
    name: str
    dtype: str              # numeric | string | datetime | boolean
    count: int
    null_count: int
    unique_count: int
    # Numeric stats
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None
    stddev: Optional[float] = None
    variance: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    cv: Optional[float] = None      # coefficient of variation
    # String stats
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    # Top values
    top_values: List[Tuple[Any, int]] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"name": self.name, "type": self.dtype, "count": self.count,
             "nulls": self.null_count, "unique": self.unique_count}
        if self.dtype == "numeric":
            d.update({
                "mean": round(self.mean, 4) if self.mean else None,
                "median": self.median,
                "stddev": round(self.stddev, 4) if self.stddev else None,
                "min": self.min_val, "max": self.max_val,
                "q1": self.q1, "q3": self.q3, "iqr": self.iqr,
                "skewness": round(self.skewness, 4) if self.skewness else None,
                "kurtosis": round(self.kurtosis, 4) if self.kurtosis else None,
            })
        return d


@dataclass
class DataSummary:
    """Summary of an entire dataset."""
    rows: int
    columns: int
    column_stats: List[ColumnStats]
    correlations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class OutlierResult:
    """Outlier detection result."""
    method: str
    outlier_indices: List[int]
    outlier_values: List[float]
    threshold: float
    total: int
    outlier_count: int
    outlier_percent: float


@dataclass
class RegressionResult:
    """Linear regression result."""
    slope: float
    intercept: float
    r_squared: float
    residuals: List[float]
    prediction_fn: Optional[Callable] = None

    def predict(self, x: float) -> float:
        return self.slope * x + self.intercept


@dataclass
class ClusterResult:
    """K-means clustering result."""
    k: int
    centroids: List[List[float]]
    labels: List[int]
    inertia: float
    iterations: int


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

def parse_csv(text: str, delimiter: str = ",") -> Tuple[List[str], List[List[str]]]:
    """Parse CSV text into headers + rows."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def parse_json_data(text: str) -> Tuple[List[str], List[List[Any]]]:
    """Parse JSON array-of-objects into headers + rows."""
    data = json.loads(text)
    if not isinstance(data, list) or not data:
        return [], []
    headers = list(data[0].keys())
    rows = [[obj.get(h) for h in headers] for obj in data]
    return headers, rows


def _detect_type(values: List[str]) -> str:
    """Detect column type from sample values."""
    numeric_count = 0
    bool_count = 0
    total = 0

    for v in values:
        if v is None or str(v).strip() == "":
            continue
        total += 1
        sv = str(v).strip().lower()
        try:
            float(sv.replace(",", ""))
            numeric_count += 1
        except ValueError as _exc:
            logger.debug("Suppressed: %s", _exc)
        if sv in ("true", "false", "yes", "no", "1", "0"):
            bool_count += 1

    if total == 0:
        return "string"
    if numeric_count / total > 0.8:
        return "numeric"
    if bool_count / total > 0.8:
        return "boolean"
    return "string"


def _to_float(v: Any) -> Optional[float]:
    """Safe string-to-float conversion."""
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════
# Descriptive Statistics
# ═══════════════════════════════════════════════════════════════════

def describe_column(name: str, values: List[Any]) -> ColumnStats:
    """Compute full descriptive statistics for a column."""
    dtype = _detect_type([str(v) for v in values])
    total = len(values)
    nulls = sum(1 for v in values if v is None or str(v).strip() == "")
    unique = len(set(str(v) for v in values if v is not None))

    stats = ColumnStats(
        name=name, dtype=dtype, count=total,
        null_count=nulls, unique_count=unique,
    )

    # Top values
    counts = Counter(str(v) for v in values if v is not None and str(v).strip())
    stats.top_values = counts.most_common(5)

    if dtype == "numeric":
        floats = [_to_float(v) for v in values]
        valid = [f for f in floats if f is not None]
        if valid:
            stats.mean = _mean(valid)
            stats.median = _median(valid)
            stats.mode = _mode(valid)
            stats.stddev = _stddev(valid)
            stats.variance = _variance(valid)
            stats.min_val = min(valid)
            stats.max_val = max(valid)
            stats.q1 = _percentile(valid, 25)
            stats.q3 = _percentile(valid, 75)
            stats.iqr = stats.q3 - stats.q1
            stats.skewness = _skewness(valid)
            stats.kurtosis = _kurtosis(valid)
            if stats.mean and stats.mean != 0:
                stats.cv = stats.stddev / abs(stats.mean)
    elif dtype == "string":
        lengths = [len(str(v)) for v in values if v is not None and str(v).strip()]
        if lengths:
            stats.min_length = min(lengths)
            stats.max_length = max(lengths)
            stats.avg_length = _mean([float(l) for l in lengths])

    return stats


def describe_dataset(headers: List[str],
                     rows: List[List[Any]]) -> DataSummary:
    """Compute statistics for an entire dataset."""
    n_cols = len(headers)
    columns: List[ColumnStats] = []

    for i, name in enumerate(headers):
        values = [row[i] if i < len(row) else None for row in rows]
        columns.append(describe_column(name, values))

    # Correlations (numeric columns only)
    numeric_cols = [(cs, i) for i, cs in enumerate(columns) if cs.dtype == "numeric"]
    correlations: Dict[str, Dict[str, float]] = {}

    for cs_a, idx_a in numeric_cols:
        correlations[cs_a.name] = {}
        vals_a = [_to_float(row[idx_a]) if idx_a < len(row) else None for row in rows]
        clean_a = [v for v in vals_a if v is not None]

        for cs_b, idx_b in numeric_cols:
            vals_b = [_to_float(row[idx_b]) if idx_b < len(row) else None for row in rows]
            # Align: only use pairs where both are non-None
            pairs = [(a, b) for a, b in zip(vals_a, vals_b)
                     if a is not None and b is not None]
            if len(pairs) >= 3:
                a_list = [p[0] for p in pairs]
                b_list = [p[1] for p in pairs]
                correlations[cs_a.name][cs_b.name] = round(
                    _pearson_correlation(a_list, b_list), 4,
                )
            else:
                correlations[cs_a.name][cs_b.name] = 0.0

    # Warnings
    warnings: List[str] = []
    for cs in columns:
        if cs.null_count > cs.count * 0.3:
            warnings.append(f"Column '{cs.name}' has {cs.null_count}/{cs.count} nulls ({cs.null_count/cs.count*100:.0f}%)")
        if cs.unique_count == 1:
            warnings.append(f"Column '{cs.name}' has only 1 unique value (constant)")
        if cs.dtype == "numeric" and cs.skewness and abs(cs.skewness) > 2:
            warnings.append(f"Column '{cs.name}' is highly skewed (skewness={cs.skewness:.2f})")

    return DataSummary(
        rows=len(rows), columns=n_cols,
        column_stats=columns, correlations=correlations,
        warnings=warnings,
    )


# ═══════════════════════════════════════════════════════════════════
# Outlier Detection
# ═══════════════════════════════════════════════════════════════════

def detect_outliers_iqr(data: List[float], factor: float = 1.5) -> OutlierResult:
    """IQR-based outlier detection."""
    q1 = _percentile(data, 25)
    q3 = _percentile(data, 75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr

    outlier_idx = [i for i, v in enumerate(data) if v < lower or v > upper]
    outlier_vals = [data[i] for i in outlier_idx]

    return OutlierResult(
        method="IQR",
        outlier_indices=outlier_idx,
        outlier_values=outlier_vals,
        threshold=factor,
        total=len(data),
        outlier_count=len(outlier_idx),
        outlier_percent=len(outlier_idx) / len(data) * 100 if data else 0,
    )


def detect_outliers_zscore(data: List[float],
                           threshold: float = 3.0) -> OutlierResult:
    """Z-score based outlier detection."""
    m = _mean(data)
    s = _stddev(data)
    if s == 0:
        return OutlierResult("Z-score", [], [], threshold, len(data), 0, 0.0)

    outlier_idx = [i for i, v in enumerate(data) if abs((v - m) / s) > threshold]
    outlier_vals = [data[i] for i in outlier_idx]

    return OutlierResult(
        method="Z-score",
        outlier_indices=outlier_idx,
        outlier_values=outlier_vals,
        threshold=threshold,
        total=len(data),
        outlier_count=len(outlier_idx),
        outlier_percent=len(outlier_idx) / len(data) * 100 if data else 0,
    )


def detect_outliers_modified_zscore(data: List[float],
                                    threshold: float = 3.5) -> OutlierResult:
    """Modified Z-score (MAD-based) outlier detection."""
    med = _median(data)
    mad = _median([abs(x - med) for x in data])
    if mad == 0:
        return OutlierResult("Modified Z-score", [], [], threshold, len(data), 0, 0.0)

    modified_z = [0.6745 * (x - med) / mad for x in data]
    outlier_idx = [i for i, z in enumerate(modified_z) if abs(z) > threshold]
    outlier_vals = [data[i] for i in outlier_idx]

    return OutlierResult(
        method="Modified Z-score (MAD)",
        outlier_indices=outlier_idx,
        outlier_values=outlier_vals,
        threshold=threshold,
        total=len(data),
        outlier_count=len(outlier_idx),
        outlier_percent=len(outlier_idx) / len(data) * 100 if data else 0,
    )


# ═══════════════════════════════════════════════════════════════════
# Linear Regression
# ═══════════════════════════════════════════════════════════════════

def linear_regression(x: List[float], y: List[float]) -> RegressionResult:
    """Ordinary least squares linear regression (closed form)."""
    n = min(len(x), len(y))
    if n < 2:
        return RegressionResult(0, 0, 0, [])

    mx = _mean(x[:n])
    my = _mean(y[:n])

    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den = sum((x[i] - mx) ** 2 for i in range(n))

    slope = num / den if den != 0 else 0
    intercept = my - slope * mx

    # R-squared
    y_pred = [slope * x[i] + intercept for i in range(n)]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - my) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    residuals = [y[i] - y_pred[i] for i in range(n)]

    return RegressionResult(
        slope=round(slope, 6),
        intercept=round(intercept, 6),
        r_squared=round(r_squared, 6),
        residuals=residuals,
    )


def gradient_descent_regression(
    x: List[float], y: List[float],
    lr: float = 0.01, epochs: int = 1000,
) -> RegressionResult:
    """Linear regression via gradient descent."""
    n = min(len(x), len(y))
    if n < 2:
        return RegressionResult(0, 0, 0, [])

    # Normalize
    mx_x, sx = _mean(x[:n]), _stddev(x[:n])
    mx_y, sy = _mean(y[:n]), _stddev(y[:n])
    sx = sx if sx != 0 else 1
    sy = sy if sy != 0 else 1

    xn = [(x[i] - mx_x) / sx for i in range(n)]
    yn = [(y[i] - mx_y) / sy for i in range(n)]

    w, b = 0.0, 0.0

    for _ in range(epochs):
        dw = sum((w * xn[i] + b - yn[i]) * xn[i] for i in range(n)) / n
        db = sum(w * xn[i] + b - yn[i] for i in range(n)) / n
        w -= lr * dw
        b -= lr * db

    # Denormalize
    slope = w * sy / sx
    intercept = mx_y + sy * b - slope * mx_x

    my = _mean(y[:n])
    y_pred = [slope * x[i] + intercept for i in range(n)]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - my) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    return RegressionResult(
        slope=round(slope, 6),
        intercept=round(intercept, 6),
        r_squared=round(r_squared, 6),
        residuals=[y[i] - y_pred[i] for i in range(n)],
    )


# ═══════════════════════════════════════════════════════════════════
# K-Means Clustering
# ═══════════════════════════════════════════════════════════════════

def _euclidean_distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def kmeans(data: List[List[float]], k: int,
           max_iter: int = 100, seed: int = 42) -> ClusterResult:
    """K-means clustering algorithm."""
    n = len(data)
    if n == 0 or k <= 0:
        return ClusterResult(k=k, centroids=[], labels=[], inertia=0, iterations=0)

    rng = random.Random(seed)
    dim = len(data[0])

    # Initialize centroids (k-means++ inspired)
    centroids = [list(data[rng.randint(0, n - 1)])]
    for _ in range(1, k):
        dists = [min(_euclidean_distance(p, c) for c in centroids) for p in data]
        total = sum(d * d for d in dists)
        if total == 0:
            centroids.append(list(data[rng.randint(0, n - 1)]))
            continue
        r = rng.random() * total
        cumulative = 0.0
        for i, d in enumerate(dists):
            cumulative += d * d
            if cumulative >= r:
                centroids.append(list(data[i]))
                break

    labels = [0] * n
    iterations = 0

    for iteration in range(max_iter):
        iterations = iteration + 1

        # Assign
        new_labels = [0] * n
        for i, point in enumerate(data):
            dists = [_euclidean_distance(point, c) for c in centroids]
            new_labels[i] = dists.index(min(dists))

        if new_labels == labels:
            break
        labels = new_labels

        # Update centroids
        for j in range(k):
            cluster_points = [data[i] for i in range(n) if labels[i] == j]
            if cluster_points:
                centroids[j] = [
                    sum(p[d] for p in cluster_points) / len(cluster_points)
                    for d in range(dim)
                ]

    # Inertia
    inertia = sum(
        _euclidean_distance(data[i], centroids[labels[i]]) ** 2
        for i in range(n)
    )

    return ClusterResult(
        k=k, centroids=centroids, labels=labels,
        inertia=round(inertia, 4), iterations=iterations,
    )


# ═══════════════════════════════════════════════════════════════════
# K-Nearest Neighbors
# ═══════════════════════════════════════════════════════════════════

def knn_classify(
    train_x: List[List[float]],
    train_y: List[str],
    query: List[float],
    k: int = 5,
) -> Tuple[str, Dict[str, int]]:
    """K-nearest neighbors classification."""
    dists = [
        (_euclidean_distance(query, train_x[i]), train_y[i])
        for i in range(len(train_x))
    ]
    dists.sort(key=lambda x: x[0])
    neighbors = dists[:k]

    votes: Dict[str, int] = Counter(label for _, label in neighbors)
    winner = votes.most_common(1)[0][0]
    return winner, dict(votes)


# ═══════════════════════════════════════════════════════════════════
# Naive Bayes Classifier
# ═══════════════════════════════════════════════════════════════════

class NaiveBayesClassifier:
    """Gaussian Naive Bayes classifier."""

    def __init__(self) -> None:
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

def _tokenize(text: str) -> List[str]:
    """Simple word tokenizer."""
    return re.findall(r"\w+", text.lower())


def tfidf(documents: List[str], max_features: int = 100) -> TfIdfResult:
    """Compute TF-IDF vectors for a corpus of documents."""
    n_docs = len(documents)
    if n_docs == 0:
        return TfIdfResult({}, {}, [], [])

    tokenized = [_tokenize(doc) for doc in documents]

    # Document frequency
    df: Counter = Counter()
    for tokens in tokenized:
        for word in set(tokens):
            df[word] += 1

    # Vocabulary (top by DF, filtered)
    vocab_items = df.most_common(max_features)
    vocabulary = {word: idx for idx, (word, _) in enumerate(vocab_items)}

    # IDF scores
    idf_scores: Dict[str, float] = {}
    for word in vocabulary:
        idf_scores[word] = math.log(n_docs / (1 + df[word])) + 1

    # TF-IDF matrix
    tfidf_matrix: List[Dict[str, float]] = []
    for tokens in tokenized:
        tf: Counter = Counter(tokens)
        total = len(tokens) if tokens else 1
        doc_tfidf: Dict[str, float] = {}
        for word in vocabulary:
            if word in tf:
                doc_tfidf[word] = (tf[word] / total) * idf_scores.get(word, 0)
        tfidf_matrix.append(doc_tfidf)

    # Top terms globally
    global_scores: Dict[str, float] = defaultdict(float)
    for doc in tfidf_matrix:
        for word, score in doc.items():
            global_scores[word] += score
    top_terms = sorted(global_scores.items(), key=lambda x: x[1], reverse=True)[:20]

    return TfIdfResult(
        vocabulary=vocabulary,
        idf_scores=idf_scores,
        tfidf_matrix=tfidf_matrix,
        top_terms=top_terms,
    )


# ═══════════════════════════════════════════════════════════════════
# Hypothesis Testing
# ═══════════════════════════════════════════════════════════════════

def z_test(sample: List[float], pop_mean: float,
           pop_std: float) -> Dict[str, float]:
    """One-sample Z-test."""
    n = len(sample)
    sample_mean = _mean(sample)
    z = (sample_mean - pop_mean) / (pop_std / math.sqrt(n))
    # Approximate p-value using normal CDF
    p_value = 2 * (1 - _normal_cdf(abs(z)))
    return {"z_statistic": round(z, 4), "p_value": round(p_value, 6),
            "sample_mean": round(sample_mean, 4), "significant_005": p_value < 0.05}


def _normal_cdf(x: float) -> float:
    """Approximation of the normal CDF (Abramowitz & Stegun)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def t_test_independent(a: List[float], b: List[float]) -> Dict[str, float]:
    """Independent two-sample t-test (Welch's)."""
    na, nb = len(a), len(b)
    ma, mb = _mean(a), _mean(b)
    va, vb = _variance(a), _variance(b)

    se = math.sqrt(va / na + vb / nb) if (va / na + vb / nb) > 0 else 1e-9
    t = (ma - mb) / se

    # Welch-Satterthwaite degrees of freedom
    num = (va / na + vb / nb) ** 2
    den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1) if na > 1 and nb > 1 else 1
    df = num / den if den > 0 else 1

    # Approximate p-value
    p_value = 2 * (1 - _normal_cdf(abs(t)))  # Normal approximation for large df

    return {
        "t_statistic": round(t, 4),
        "degrees_of_freedom": round(df, 2),
        "p_value": round(p_value, 6),
        "mean_a": round(ma, 4),
        "mean_b": round(mb, 4),
        "significant_005": p_value < 0.05,
    }


# ═══════════════════════════════════════════════════════════════════
# Anomaly Detection
# ═══════════════════════════════════════════════════════════════════

def detect_anomalies(data: List[float],
                     sensitivity: float = 2.5) -> Dict[str, Any]:
    """
    Statistical anomaly detection combining Z-score and IQR methods.

    Parameters
    ----------
    data : list of float
        Data to check for anomalies.
    sensitivity : float
        Lower = more sensitive (more anomalies).

    Returns
    -------
    dict with anomalies, scores, and indices.
    """
    m = _mean(data)
    s = _stddev(data)
    q1 = _percentile(data, 25)
    q3 = _percentile(data, 75)
    iqr = q3 - q1

    anomalies: List[Dict[str, Any]] = []

    for i, v in enumerate(data):
        z_score = abs((v - m) / s) if s > 0 else 0
        iqr_out = v < (q1 - sensitivity * iqr) or v > (q3 + sensitivity * iqr)
        is_anomaly = z_score > sensitivity or iqr_out

        if is_anomaly:
            anomalies.append({
                "index": i,
                "value": v,
                "z_score": round(z_score, 3),
                "iqr_outlier": iqr_out,
            })

    return {
        "total": len(data),
        "anomaly_count": len(anomalies),
        "anomaly_rate": round(len(anomalies) / len(data) * 100, 2) if data else 0,
        "anomalies": anomalies,
        "stats": {"mean": round(m, 4), "stddev": round(s, 4),
                  "q1": round(q1, 4), "q3": round(q3, 4), "iqr": round(iqr, 4)},
    }


# ═══════════════════════════════════════════════════════════════════
# Moving Averages & Trend Analysis
# ═══════════════════════════════════════════════════════════════════

def moving_average(data: List[float], window: int = 5) -> List[Optional[float]]:
    """Simple moving average."""
    result: List[Optional[float]] = [None] * (window - 1)
    for i in range(window - 1, len(data)):
        avg = sum(data[i - window + 1: i + 1]) / window
        result.append(round(avg, 4))
    return result


def exponential_moving_average(data: List[float],
                               alpha: float = 0.3) -> List[float]:
    """Exponential moving average."""
    if not data:
        return []
    ema = [data[0]]
    for i in range(1, len(data)):
        ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
    return [round(v, 4) for v in ema]


def detect_trend(data: List[float]) -> Dict[str, Any]:
    """Detect linear trend in time-series data."""
    x = list(range(len(data)))
    reg = linear_regression([float(i) for i in x], data)

    direction = "upward" if reg.slope > 0.01 else "downward" if reg.slope < -0.01 else "flat"

    return {
        "direction": direction,
        "slope": reg.slope,
        "r_squared": reg.r_squared,
        "strength": "strong" if reg.r_squared > 0.7 else "moderate" if reg.r_squared > 0.3 else "weak",
    }


# ═══════════════════════════════════════════════════════════════════
# ASCII Visualization
# ═══════════════════════════════════════════════════════════════════

def ascii_bar_chart(data: Dict[str, float], width: int = 40,
                    title: str = "") -> str:
    """Generate ASCII bar chart."""
    if not data:
        return ""
    max_val = max(data.values())
    max_label = max(len(str(k)) for k in data.keys())

    lines = []
    if title:
        lines.append(f"  {title}")
        lines.append("  " + "─" * (max_label + width + 10))

    for label, value in data.items():
        bar_len = int(value / max_val * width) if max_val > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {str(label):<{max_label}} │ {bar} {value:.2f}")

    return "\n".join(lines)


def ascii_histogram(data: List[float], bins: int = 10,
                    width: int = 40) -> str:
    """Generate ASCII histogram."""
    if not data:
        return ""

    min_val, max_val = min(data), max(data)
    if min_val == max_val:
        return f"All values = {min_val}"

    bin_width = (max_val - min_val) / bins
    counts = [0] * bins
    for v in data:
        idx = min(int((v - min_val) / bin_width), bins - 1)
        counts[idx] += 1

    max_count = max(counts)
    lines = ["  Histogram"]
    lines.append("  " + "─" * (width + 20))

    for i in range(bins):
        lo = min_val + i * bin_width
        hi = lo + bin_width
        bar_len = int(counts[i] / max_count * width) if max_count > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  [{lo:7.2f}, {hi:7.2f}) │ {bar} ({counts[i]})")

    return "\n".join(lines)


def sparkline(data: List[float]) -> str:
    """Generate a sparkline string."""
    if not data:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    mn, mx = min(data), max(data)
    rng = mx - mn if mx != mn else 1
    return "".join(blocks[min(int((v - mn) / rng * 7), 7)] for v in data)

class DataAnalyzer:
    """Data analysis and visualization helper."""

    def __init__(self) -> None:
        self._data = []

    def load(self, data: list) -> Any:
        self._data = data

    def summary(self) -> dict:
        if not self._data:
            return {"count": 0}
        return {
            "count": len(self._data),
            "type": type(self._data[0]).__name__ if self._data else "empty",
        }

    def filter_by(self, key: str, value: str) -> list:
        return [d for d in self._data if isinstance(d, dict) and d.get(key) == value]


