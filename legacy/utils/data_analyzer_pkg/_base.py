
from __future__ import annotations
"""
data_analyzer_pkg/_base.py — shared imports
Arki Engine v29.0.0
"""
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


