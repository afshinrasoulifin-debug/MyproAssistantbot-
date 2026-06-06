
"""
handlers/victor/nlp.py — FACADE
────────────────────────
Re-exports PersianNLP and PersianTextToolkit from nlp_parts/.
Original: 1194 lines → split into 4 domain mixins.

Structure:
  nlp_parts/persian_nlp.py    — Core PersianNLP class (390 lines)
  nlp_parts/v6_mixin.py       — v6 advanced analysis (269 lines)
  nlp_parts/v7_mixin.py       — v7 TITAN enterprise NLP (282 lines)
  nlp_parts/text_toolkit.py   — PersianTextToolkit (289 lines)
"""
# ─── FACADE ─── re-exports only ───
from handlers.victor.nlp_parts import PersianNLP, PersianTextToolkit  # noqa: F401

__all__ = ["PersianNLP", "PersianTextToolkit"]


