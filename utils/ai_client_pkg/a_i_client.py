
"""
a_i_client.py — FACADE
Split into domain mixins under a_i_client_parts/
"""
from __future__ import annotations

# ─── FACADE ───
from .a_i_client_parts import AIClient  # noqa: F401

__all__ = ["AIClient"]


