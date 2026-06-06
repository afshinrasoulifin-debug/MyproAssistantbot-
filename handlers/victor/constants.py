
from __future__ import annotations
"""Victor v7.0 TITAN — Constants and configuration."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Persistent storage path ──
BRAIN_DIR = Path(os.environ.get("VICTOR_BRAIN_DIR", "data/victor_brain"))

# ── Constants ──
BM25_K1 = 1.5
BM25_B = 0.75
FORGETTING_RATE = 0.005  # per hour — Ebbinghaus decay
MAX_GRAPH_HOPS = 4
CONTEXT_WINDOW_SIZE = 20  # last N interactions for context
CONFIDENCE_THRESHOLD = 15.0  # minimum confidence to answer
AUTO_LEARN_THRESHOLD = 3  # after N similar queries, learn pattern


