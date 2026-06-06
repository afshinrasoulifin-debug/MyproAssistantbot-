
"""
campaign_orchestrator_pkg/campaign_step.py — CampaignStep
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class CampaignStep:
    """A step in a campaign sequence."""
    step_number: int
    step_type: StepType
    config: Dict[str, Any] = field(default_factory=dict)
    delay_hours: float = 0.0  # Wait before this step
    condition: Optional[str] = None  # e.g., "score > 50"
    channel: Optional[ChannelType] = None
    template_id: Optional[str] = None
    completed: bool = False
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "delay_hours": self.delay_hours,
            "condition": self.condition,
            "channel": self.channel.value if self.channel else None,
            "completed": self.completed,
        }




