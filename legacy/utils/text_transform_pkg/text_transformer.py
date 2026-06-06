
"""
text_transform_pkg/text_transformer.py — TextTransformer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class TextTransformer:
    """Text transformation utilities."""

    def __init__(self):
        self._transforms = {}

    def register(self, name: str, func):
        self._transforms[name] = func

    def transform(self, text: str, transform_name: str) -> str:
        fn = self._transforms.get(transform_name)
        if fn:
            return fn(text)
        return text

    @staticmethod
    def to_slug(text: str) -> str:
        import re
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

    @staticmethod
    def truncate(text: str, max_len: int = 100) -> str:
        return text[:max_len] + "…" if len(text) > max_len else text



# ═══════════════════════════════════════════════════════════════════════
# PARSELTONGUE — Input Perturbation Engine (DEEP)
# ═══════════════════════════════════════════════════════════════════════
#
# Architecture:
#   ┌────────────────┐
#   │  Input Text     │
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  TRIGGER SCAN   │ ← 36 default + custom triggers
#   │  (7 categories) │   Word-boundary regex matching
#   └───────┬────────┘
#           ▼ triggers found?
#   ┌────────────────┐
#   │  TECHNIQUE SEL  │ ← leetspeak / unicode / zwj / mixedcase / phonetic / random
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  INTENSITY      │ ← light (1 char) / medium (half) / heavy (all)
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  OBFUSCATION    │ ← Apply chosen technique at chosen intensity
#   │  (longest-first │   Sort triggers desc to prevent partial-match corruption
#   │   matching)     │
#   └───────┬────────┘
#           ▼
#   ┌────────────────┐
#   │  RESULT         │ ← {original, transformed, triggers_found, transformations}
#   └────────────────┘
#
# Ported from: APEX-main/src/lib/parseltongue.ts
# Version: 4.0.0-DEEP (Phase 1-5 hardened)
# ═══════════════════════════════════════════════════════════════════════




