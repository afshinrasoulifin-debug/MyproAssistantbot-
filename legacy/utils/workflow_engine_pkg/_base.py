
from __future__ import annotations
"""
workflow_engine_pkg/_base.py — shared imports
Arki Engine v29.0.0
"""
"""
tg_bot/utils/workflow_engine.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
WORKFLOW ENGINE — DAG-Based Workflow Orchestration System

Directed Acyclic Graph execution engine for chaining tools
into fully automated, self-recovering pipelines.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                    WORKFLOW ENGINE                           │
   ├──────────────┬──────────────┬──────────────┬───────────────┤
   │  DAG Builder │  Scheduler   │  Executor    │  Monitor      │
   ├──────────────┼──────────────┼──────────────┼───────────────┤
   │ add_node()   │ topo_sort()  │ run_node()   │ status()      │
   │ add_edge()   │ detect_cycle │ run_parallel │ progress()    │
   │ validate()   │ dependencies │ retry()      │ timeline()    │
   │ from_json()  │ scheduling   │ rollback()   │ alerts()      │
   │ to_json()    │ cron trigger │ sandbox()    │ metrics()     │
   ├──────────────┼──────────────┼──────────────┼───────────────┤
   │  Branching   │  Variables   │  Templates   │  Persistence  │
   ├──────────────┼──────────────┼──────────────┼───────────────┤
   │ if/else      │ context map  │ scan→report  │ save/load     │
   │ switch/case  │ interpolate  │ crawl→parse  │ checkpoint    │
   │ while loop   │ transform    │ monitor→act  │ resume        │
   │ for_each     │ schema val   │ custom DSL   │ snapshot      │
   └──────────────┴──────────────┴──────────────┴───────────────┘

Features
────────
  • DAG construction with cycle detection (Kahn's algorithm)
  • Topological sort for execution ordering
  • Parallel execution of independent nodes
  • Conditional branching (if/else, switch/case)
  • Loop constructs (while, for_each, repeat)
  • Variable interpolation between nodes
  • Retry with exponential backoff per node
  • Checkpoint/resume for long-running workflows
  • Workflow templates (scan→report, ETL, monitoring)
  • JSON serialization for save/load
  • Real-time execution monitoring
  • Error propagation with rollback support
  • Cron-based scheduling with timezone support

References
──────────
  Port of: apex_app/src/lib/workflow-engine.ts (771 lines)
  Enhanced: cycle detection, topological sort, checkpoint/resume,
            template library, expression evaluator, cron scheduler
"""


