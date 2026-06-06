
"""
tg_bot/core/ — Intelligence Layer
══════════════════════════════════
Connects the 22 professional modules to the Telegram bot handlers.

This package is the GLUE between standalone algorithms and real bot behavior.

Modules:
  pipeline.py    — Main intelligent pipeline (message → classify → route → execute → respond)
  reasoning.py   — Multi-strategy reasoning engine (ReAct, CoT, ToT)
  context.py     — Context builder with memory integration
  router.py      — Smart module router
  init.py        — Module initialization and lifecycle
"""


