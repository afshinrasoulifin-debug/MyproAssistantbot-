
from __future__ import annotations
"""
campaign_orchestrator_pkg/_base.py — shared imports
Arki Engine v29.0.0
"""
"""
utils/campaign_orchestrator.py — SUPREME Campaign Orchestrator v1.0
═══════════════════════════════════════════════════════════════════
Unifies ALL marketing modules into automated multi-step campaigns.

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                 CampaignOrchestrator                        │
  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
  │  │ Campaign  │→│  Lead    │→│  Execute   │→│ Analytics │  │
  │  │ Planner   │  │ Pipeline │  │  Sequence  │  │  Track    │  │
  │  └──────────┘  └──────────┘  └───────────┘  └──────────┘  │
  │       ↕              ↕              ↕              ↕        │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │  12 Marketing Modules (auto-wired)                      │   │
  │  │  b2b_hunter · outreach · platform_intelligence          │   │
  │  │  market_professor · prospect_scoring · deep_recon       │   │
  │  │  contact_intel · social_intel · content_forge           │   │
  │  │  competitor_radar · campaign_manager · data_bridge      │   │
  │  └─────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘

Campaign Types:
  B2B_OUTREACH → Discover → Enrich → Score → Sequence → Follow-up
  B2C_SOCIAL   → Content Calendar → Publish → Engage → Analyze
  COMPETITOR   → Monitor → Alert → Counter-strategy → Execute
  FULL_FUNNEL  → All of the above, orchestrated together
"""


