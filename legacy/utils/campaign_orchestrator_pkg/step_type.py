
"""
campaign_orchestrator_pkg/step_type.py — StepType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class StepType(Enum):
    DISCOVER = "discover"       # Find prospects
    ENRICH = "enrich"           # Deep recon + contact intel
    SCORE = "score"             # Score prospects
    EMAIL = "email"             # Send outreach email
    FOLLOW_UP = "follow_up"    # Follow-up email
    SOCIAL_POST = "social_post" # Create social post
    CONTENT = "content"         # Generate content
    ANALYZE = "analyze"         # Analyze results
    WAIT = "wait"               # Wait N days
    FILTER = "filter"           # Filter leads by criteria
    COMPETITOR_SCAN = "competitor_scan"




