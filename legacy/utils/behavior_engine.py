
from __future__ import annotations
"""
utils/behavior_engine.py — Advanced Behavioral Intelligence Engine v1.0-TITAN
═══════════════════════════════════════════════════════════════════════════════
Human-like browsing behavior simulation beyond basic mouse/keyboard:

 1. Session-level behavior modeling (search→browse→interact→idle)
 2. Mouse movement heatmaps & realistic viewport interaction zones
 3. Scroll depth distribution (reading vs scanning patterns)
 4. Tab switching / idle patterns / attention simulation
 5. Page timing model (time-on-page correlated with content length)
 6. Form interaction patterns (focus→type→blur→validate→next)
 7. Micro-behavior noise (slight overshoots, corrections, hesitations)
 8. Circadian rhythm awareness (browsing patterns vary by time of day)

Author: Arki Engine TITAN
License: Proprietary
"""


import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("arki.behavior_engine")


# ═══════════════════════════════════════════════════════════
# Behavior Models
# ═══════════════════════════════════════════════════════════

class BrowsingIntent(Enum):
    """What the user is trying to accomplish."""
    CASUAL_BROWSING = "casual"      # Just clicking around
    RESEARCHING = "researching"     # Reading articles, comparing
    SHOPPING = "shopping"           # Product pages, cart, checkout
    FORM_FILLING = "form_filling"   # Registration, contact forms
    SEARCHING = "searching"         # Search → results → click → back → click
    READING = "reading"             # Long-form content consumption
    QUICK_CHECK = "quick_check"     # Quick glance, bounce


class ScrollPattern(Enum):
    """How users scroll through content."""
    READER = "reader"       # Steady, consistent scrolling
    SCANNER = "scanner"     # Fast scrolling with pauses
    JUMPER = "jumper"       # Jump to sections, skip content
    SLOW = "slow"           # Very slow, reading every word
    SKIMMER = "skimmer"     # Scroll to bottom quickly, then back up


class AttentionState(Enum):
    """Current user attention level."""
    FOCUSED = "focused"         # Active interaction
    DISTRACTED = "distracted"   # Slower, more pauses
    IDLE = "idle"               # Not interacting (reading or away)
    RETURNING = "returning"     # Coming back from being away


@dataclass
class ViewportZone:
    """A zone in the viewport where interactions happen."""
    name: str
    x_min: float   # 0.0 - 1.0 of viewport width
    x_max: float
    y_min: float   # 0.0 - 1.0 of viewport height
    y_max: float
    weight: float = 1.0  # How likely to interact here

    def random_point(self, viewport_width: int = 1920, viewport_height: int = 1080) -> Tuple[int, int]:
        x = random.uniform(self.x_min, self.x_max) * viewport_width
        y = random.uniform(self.y_min, self.y_max) * viewport_height
        return (int(x), int(y))


# ── Viewport interaction heatmap zones ──

VIEWPORT_ZONES: Dict[str, List[ViewportZone]] = {
    "desktop": [
        ViewportZone("top_nav", 0.0, 1.0, 0.0, 0.06, weight=3.0),
        ViewportZone("hero_area", 0.1, 0.9, 0.06, 0.35, weight=5.0),
        ViewportZone("main_content", 0.05, 0.75, 0.35, 0.80, weight=8.0),
        ViewportZone("sidebar", 0.75, 1.0, 0.1, 0.80, weight=2.0),
        ViewportZone("footer", 0.0, 1.0, 0.85, 1.0, weight=1.0),
        ViewportZone("center_cta", 0.3, 0.7, 0.40, 0.55, weight=4.0),
    ],
    "search_results": [
        ViewportZone("search_bar", 0.1, 0.7, 0.0, 0.08, weight=6.0),
        ViewportZone("first_result", 0.05, 0.65, 0.10, 0.25, weight=10.0),
        ViewportZone("second_result", 0.05, 0.65, 0.25, 0.40, weight=7.0),
        ViewportZone("third_result", 0.05, 0.65, 0.40, 0.55, weight=5.0),
        ViewportZone("remaining", 0.05, 0.65, 0.55, 0.90, weight=3.0),
        ViewportZone("ads_sidebar", 0.70, 1.0, 0.10, 0.70, weight=1.0),
    ],
    "product_page": [
        ViewportZone("product_image", 0.02, 0.50, 0.05, 0.65, weight=7.0),
        ViewportZone("product_info", 0.50, 0.98, 0.05, 0.45, weight=8.0),
        ViewportZone("price_area", 0.50, 0.98, 0.30, 0.42, weight=9.0),
        ViewportZone("add_to_cart", 0.50, 0.85, 0.42, 0.52, weight=10.0),
        ViewportZone("reviews", 0.05, 0.95, 0.70, 0.95, weight=4.0),
    ],
}


@dataclass
class BehaviorAction:
    """A single behavior action to perform."""
    action_type: str    # "move", "click", "scroll", "wait", "type", "focus"
    target: Optional[Tuple[int, int]] = None  # (x, y) for mouse actions
    value: Any = None   # text for type, pixels for scroll, seconds for wait
    duration_ms: int = 0  # How long the action takes
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action_type,
            "target": self.target,
            "value": self.value,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class SessionPlan:
    """A planned sequence of browsing behaviors."""
    intent: BrowsingIntent
    actions: List[BehaviorAction] = field(default_factory=list)
    total_duration_ms: int = 0
    pages_to_visit: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "total_duration_ms": self.total_duration_ms,
            "action_count": len(self.actions),
            "pages_to_visit": self.pages_to_visit,
        }


# ═══════════════════════════════════════════════════════════
# Mouse Path Generator (Advanced Bézier with micro-behaviors)
# ═══════════════════════════════════════════════════════════

class MousePathGenerator:
    """Generate realistic mouse movement paths with human imperfections."""

    @staticmethod
    def bezier_path(
        start: Tuple[int, int],
        end: Tuple[int, int],
        steps: int = 0,
        overshoot: float = 0.15,
        noise: float = 2.0,
    ) -> List[Tuple[int, int]]:
        """
        Generate a Bézier curve mouse path with overshoot and noise.

        Args:
            start: Starting point (x, y)
            end: Ending point (x, y)
            steps: Number of steps (0 = auto based on distance)
            overshoot: Probability of overshooting target
            noise: Pixel noise amplitude
        """
        sx, sy = start
        ex, ey = end
        dist = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)

        if steps == 0:
            steps = max(10, int(dist / 8))

        # Generate 2-3 control points for natural curve
        cp1x = sx + (ex - sx) * 0.25 + random.gauss(0, dist * 0.08)
        cp1y = sy + (ey - sy) * 0.25 + random.gauss(0, dist * 0.08)
        cp2x = sx + (ex - sx) * 0.75 + random.gauss(0, dist * 0.06)
        cp2y = sy + (ey - sy) * 0.75 + random.gauss(0, dist * 0.06)

        points = []
        for i in range(steps + 1):
            t = i / steps

            # Ease-in-out timing (humans accelerate then decelerate)
            t_ease = t * t * (3 - 2 * t)

            # Cubic Bézier
            x = ((1 - t_ease) ** 3 * sx
                 + 3 * (1 - t_ease) ** 2 * t_ease * cp1x
                 + 3 * (1 - t_ease) * t_ease ** 2 * cp2x
                 + t_ease ** 3 * ex)
            y = ((1 - t_ease) ** 3 * sy
                 + 3 * (1 - t_ease) ** 2 * t_ease * cp1y
                 + 3 * (1 - t_ease) * t_ease ** 2 * cp2y
                 + t_ease ** 3 * ey)

            # Add micro-noise (decreasing as we approach target)
            remaining = 1.0 - t
            nx = random.gauss(0, noise * remaining)
            ny = random.gauss(0, noise * remaining)

            points.append((int(x + nx), int(y + ny)))

        # Overshoot simulation
        if random.random() < overshoot and dist > 50:
            overshoot_dist = random.uniform(3, min(15, dist * 0.1))
            dx = ex - sx
            dy = ey - sy
            norm = max(1, math.sqrt(dx * dx + dy * dy))
            ox = int(ex + (dx / norm) * overshoot_dist)
            oy = int(ey + (dy / norm) * overshoot_dist)
            points.append((ox, oy))
            # Correct back
            correction_steps = random.randint(3, 6)
            for j in range(1, correction_steps + 1):
                t = j / correction_steps
                cx = int(ox + (ex - ox) * t)
                cy = int(oy + (ey - oy) * t)
                points.append((cx, cy))

        # Ensure we end exactly at target
        points.append((ex, ey))
        return points

    @staticmethod
    def generate_delays(count: int, base_ms: float = 8.0) -> List[float]:
        """Generate realistic per-step delays (humans move unevenly)."""
        delays = []
        for i in range(count):
            t = i / max(1, count - 1)
            # Slower at start and end (acceleration curve)
            speed_factor = 0.5 + 2.0 * t * (1.0 - t)
            delay = base_ms / max(0.3, speed_factor)
            delay += random.gauss(0, 1.5)
            delays.append(max(2.0, delay))
        return delays

    @staticmethod
    def idle_drift(
        center: Tuple[int, int],
        duration_ms: int = 2000,
        amplitude: float = 3.0,
    ) -> List[Tuple[int, int]]:
        """
        Simulate micro-movements when mouse is 'idle' over an element.
        Humans never hold the mouse perfectly still.
        """
        cx, cy = center
        points = []
        steps = max(5, duration_ms // 100)
        for _ in range(steps):
            dx = random.gauss(0, amplitude)
            dy = random.gauss(0, amplitude)
            points.append((int(cx + dx), int(cy + dy)))
        return points


# ═══════════════════════════════════════════════════════════
# Scroll Behavior Simulator
# ═══════════════════════════════════════════════════════════

class ScrollSimulator:
    """Generate realistic scroll patterns based on content and intent."""

    @staticmethod
    def reading_scroll(
        page_height: int = 5000,
        viewport_height: int = 1080,
        words_per_screen: int = 300,
        reading_speed_wpm: int = 250,
    ) -> List[BehaviorAction]:
        """
        Generate scroll pattern for reading content.
        Time-on-screen correlated with visible content amount.
        """
        actions = []
        current_y = 0
        max_scroll = max(0, page_height - viewport_height)

        while current_y < max_scroll:
            # Read current viewport
            read_time = (words_per_screen / reading_speed_wpm) * 60 * 1000
            read_time *= random.uniform(0.7, 1.5)  # Variance

            actions.append(BehaviorAction(
                action_type="wait",
                value=read_time / 1000.0,
                duration_ms=int(read_time),
                metadata={"reason": "reading"},
            ))

            # Scroll amount (partial viewport)
            scroll_amount = int(viewport_height * random.uniform(0.5, 0.85))
            scroll_amount = min(scroll_amount, max_scroll - current_y)

            if scroll_amount <= 0:
                break

            # Scroll with realistic speed variation
            scroll_duration = int(300 + random.gauss(200, 80))

            actions.append(BehaviorAction(
                action_type="scroll",
                value=scroll_amount,
                duration_ms=scroll_duration,
                metadata={"pattern": "reading", "from_y": current_y},
            ))

            current_y += scroll_amount

            # Occasional pause mid-scroll
            if random.random() < 0.2:
                pause = random.uniform(0.5, 2.0)
                actions.append(BehaviorAction(
                    action_type="wait",
                    value=pause,
                    duration_ms=int(pause * 1000),
                    metadata={"reason": "mid_scroll_pause"},
                ))

        return actions

    @staticmethod
    def scanning_scroll(
        page_height: int = 5000,
        viewport_height: int = 1080,
    ) -> List[BehaviorAction]:
        """Generate fast scanning scroll pattern (looking for something)."""
        actions = []
        current_y = 0
        max_scroll = max(0, page_height - viewport_height)

        while current_y < max_scroll:
            # Quick glance
            glance_time = random.uniform(0.3, 1.5) * 1000
            actions.append(BehaviorAction(
                action_type="wait",
                value=glance_time / 1000,
                duration_ms=int(glance_time),
                metadata={"reason": "scanning"},
            ))

            # Larger scroll jumps
            scroll_amount = int(viewport_height * random.uniform(0.7, 1.3))
            scroll_amount = min(scroll_amount, max_scroll - current_y)
            if scroll_amount <= 0:
                break

            actions.append(BehaviorAction(
                action_type="scroll",
                value=scroll_amount,
                duration_ms=random.randint(150, 400),
                metadata={"pattern": "scanning"},
            ))

            current_y += scroll_amount

            # Sometimes scroll back up a bit (found something interesting)
            if random.random() < 0.15 and current_y > viewport_height:
                back_amount = int(viewport_height * random.uniform(0.2, 0.5))
                actions.append(BehaviorAction(
                    action_type="scroll",
                    value=-back_amount,
                    duration_ms=random.randint(200, 400),
                    metadata={"pattern": "backtrack"},
                ))
                current_y -= back_amount

                # Longer pause (reading what caught attention)
                actions.append(BehaviorAction(
                    action_type="wait",
                    value=random.uniform(2.0, 5.0),
                    duration_ms=random.randint(2000, 5000),
                    metadata={"reason": "found_interesting"},
                ))

        return actions

    @staticmethod
    def jump_scroll(
        page_height: int = 5000,
        viewport_height: int = 1080,
        target_sections: int = 3,
    ) -> List[BehaviorAction]:
        """Simulate jumping to specific sections (via TOC or scrollbar)."""
        actions = []
        max_scroll = max(0, page_height - viewport_height)

        # Generate section positions
        sections = sorted([
            random.randint(0, max_scroll) for _ in range(target_sections)
        ])

        for pos in sections:
            actions.append(BehaviorAction(
                action_type="scroll_to",
                value=pos,
                duration_ms=random.randint(100, 300),
                metadata={"pattern": "jump"},
            ))

            # Read the section
            read_time = random.uniform(3.0, 12.0)
            actions.append(BehaviorAction(
                action_type="wait",
                value=read_time,
                duration_ms=int(read_time * 1000),
                metadata={"reason": "reading_section"},
            ))

        return actions


# ═══════════════════════════════════════════════════════════
# Form Interaction Simulator
# ═══════════════════════════════════════════════════════════

class FormSimulator:
    """Simulate human-like form filling behavior."""

    @staticmethod
    def generate_typing_pattern(
        text: str,
        base_delay_ms: float = 80,
        error_rate: float = 0.03,
    ) -> List[BehaviorAction]:
        """
        Generate realistic typing with errors and corrections.

        Args:
            text: Text to type
            base_delay_ms: Base inter-key delay
            error_rate: Probability of typo per character
        """
        actions = []

        for i, char in enumerate(text):
            # Typo simulation
            if random.random() < error_rate and i > 0:
                # Type wrong key
                wrong_char = chr(ord(char) + random.choice([-1, 1]))
                delay = _typing_delay(base_delay_ms)
                actions.append(BehaviorAction(
                    action_type="keypress",
                    value=wrong_char,
                    duration_ms=int(delay),
                    metadata={"is_error": True},
                ))

                # Pause (notice error)
                notice_delay = random.uniform(100, 400)
                actions.append(BehaviorAction(
                    action_type="wait",
                    value=notice_delay / 1000,
                    duration_ms=int(notice_delay),
                    metadata={"reason": "noticed_typo"},
                ))

                # Backspace
                actions.append(BehaviorAction(
                    action_type="keypress",
                    value="Backspace",
                    duration_ms=int(random.uniform(40, 100)),
                ))

            # Type correct character
            delay = _typing_delay(base_delay_ms)

            # Word boundaries: slight pause
            if char == " ":
                delay *= random.uniform(1.2, 2.0)

            actions.append(BehaviorAction(
                action_type="keypress",
                value=char,
                duration_ms=int(delay),
            ))

        return actions

    @staticmethod
    def field_interaction_pattern(
        fields: List[Dict[str, str]],
    ) -> List[BehaviorAction]:
        """
        Generate realistic form field interaction sequence.

        Each field dict has: {"selector": "...", "value": "...", "type": "text|email|password"}
        """
        actions = []

        for i, fld in enumerate(fields):
            selector = fld.get("selector", "")
            value = fld.get("value", "")
            ftype = fld.get("type", "text")

            # Move to field (visual scanning)
            if i > 0:
                scan_delay = random.uniform(0.3, 1.2)
                actions.append(BehaviorAction(
                    action_type="wait",
                    value=scan_delay,
                    duration_ms=int(scan_delay * 1000),
                    metadata={"reason": "scanning_to_field"},
                ))

            # Click to focus
            actions.append(BehaviorAction(
                action_type="focus",
                value=selector,
                duration_ms=int(random.uniform(50, 150)),
                metadata={"field_type": ftype},
            ))

            # Small pause before typing (human thinks about what to type)
            think_delay = random.uniform(0.2, 0.8)
            if ftype == "password":
                think_delay *= 1.5  # Longer for passwords
            actions.append(BehaviorAction(
                action_type="wait",
                value=think_delay,
                duration_ms=int(think_delay * 1000),
                metadata={"reason": "thinking"},
            ))

            # Type value
            typing_actions = FormSimulator.generate_typing_pattern(value)
            actions.extend(typing_actions)

            # Blur / move away
            blur_delay = random.uniform(0.1, 0.4)
            actions.append(BehaviorAction(
                action_type="blur",
                value=selector,
                duration_ms=int(blur_delay * 1000),
            ))

            # Validation glance (look at what was typed)
            if random.random() < 0.4:
                glance = random.uniform(0.3, 1.0)
                actions.append(BehaviorAction(
                    action_type="wait",
                    value=glance,
                    duration_ms=int(glance * 1000),
                    metadata={"reason": "validation_glance"},
                ))

        return actions


# ═══════════════════════════════════════════════════════════
# Circadian Rhythm Simulator
# ═══════════════════════════════════════════════════════════

class CircadianRhythm:
    """Adjust browsing behavior based on time of day."""

    # Relative activity levels by hour (0-23)
    ACTIVITY_CURVE: List[float] = [
        0.15, 0.08, 0.05, 0.03, 0.03, 0.05,   # 00-05: very low
        0.15, 0.35, 0.60, 0.75, 0.85, 0.90,    # 06-11: morning ramp
        0.85, 0.80, 0.75, 0.80, 0.85, 0.90,    # 12-17: afternoon
        0.95, 1.00, 0.95, 0.80, 0.55, 0.30,    # 18-23: evening peak → decline
    ]

    @classmethod
    def activity_level(cls, hour: int) -> float:
        """Get activity level for a given hour (0-23)."""
        return cls.ACTIVITY_CURVE[hour % 24]

    @classmethod
    def adjust_delays(cls, base_delay_ms: float, hour: int) -> float:
        """Adjust delays based on time of day. Tired = slower."""
        activity = cls.activity_level(hour)
        # Lower activity → longer delays (tired/distracted)
        multiplier = 1.0 + (1.0 - activity) * 0.8
        return base_delay_ms * multiplier

    @classmethod
    def session_duration(cls, hour: int, base_minutes: float = 10.0) -> float:
        """Suggested session duration based on time of day."""
        activity = cls.activity_level(hour)
        return base_minutes * (0.5 + activity * 1.0)

    @classmethod
    def error_rate(cls, hour: int, base_rate: float = 0.03) -> float:
        """Typing error rate adjusted for time of day (tired = more errors)."""
        activity = cls.activity_level(hour)
        return base_rate * (1.0 + (1.0 - activity) * 1.5)

    @classmethod
    def is_natural_time(cls, hour: int, threshold: float = 0.10) -> bool:
        """Check if browsing at this hour is natural."""
        return cls.activity_level(hour) >= threshold


# ═══════════════════════════════════════════════════════════
# Session Behavior Planner
# ═══════════════════════════════════════════════════════════

class SessionPlanner:
    """
    Plan an entire browsing session with realistic navigation patterns.

    Patterns:
    - Search → Results → Click → Read → Back → Click → Read
    - Direct URL → Browse → Follow links → Exit
    - Landing page → Product → Cart → Checkout
    """

    # Page timing model: estimated time spent on different page types
    PAGE_TIMING_MS: Dict[str, Tuple[int, int]] = {
        "search_results": (3000, 15000),
        "article": (15000, 180000),
        "product_page": (10000, 60000),
        "category_page": (5000, 20000),
        "homepage": (5000, 30000),
        "form_page": (20000, 120000),
        "checkout": (30000, 180000),
        "generic": (5000, 60000),
    }

    @classmethod
    def plan_session(
        cls,
        intent: BrowsingIntent = BrowsingIntent.CASUAL_BROWSING,
        pages: int = 0,
        hour: int = 12,
    ) -> SessionPlan:
        """
        Plan a complete browsing session.

        Args:
            intent: What the user is trying to do
            pages: Number of pages (0 = auto based on intent)
            hour: Current hour for circadian adjustment
        """
        if pages == 0:
            pages = cls._estimate_pages(intent)

        plan = SessionPlan(intent=intent, pages_to_visit=pages)
        total_ms = 0

        for i in range(pages):
            page_type = cls._page_type_for_intent(intent, i)
            min_t, max_t = cls.PAGE_TIMING_MS.get(page_type, (5000, 30000))

            # Circadian adjustment
            time_on_page = random.randint(min_t, max_t)
            time_on_page = int(CircadianRhythm.adjust_delays(time_on_page, hour))

            # Generate page-level behaviors
            plan.actions.append(BehaviorAction(
                action_type="navigate",
                value=page_type,
                duration_ms=random.randint(500, 3000),
                metadata={"page_index": i, "page_type": page_type},
            ))

            # Add scroll behavior
            scroll_pattern = cls._select_scroll_pattern(intent, page_type)
            if scroll_pattern == ScrollPattern.READER:
                plan.actions.extend(ScrollSimulator.reading_scroll())
            elif scroll_pattern == ScrollPattern.SCANNER:
                plan.actions.extend(ScrollSimulator.scanning_scroll())
            else:
                plan.actions.extend(ScrollSimulator.jump_scroll())

            # Page interaction time
            plan.actions.append(BehaviorAction(
                action_type="wait",
                value=time_on_page / 1000,
                duration_ms=time_on_page,
                metadata={"reason": "page_interaction"},
            ))

            total_ms += time_on_page

            # Inter-page behavior
            if i < pages - 1:
                transition = random.uniform(0.5, 2.0)
                plan.actions.append(BehaviorAction(
                    action_type="wait",
                    value=transition,
                    duration_ms=int(transition * 1000),
                    metadata={"reason": "page_transition"},
                ))
                total_ms += int(transition * 1000)

        plan.total_duration_ms = total_ms
        return plan

    @classmethod
    def _estimate_pages(cls, intent: BrowsingIntent) -> int:
        """Estimate how many pages for this intent."""
        return {
            BrowsingIntent.CASUAL_BROWSING: random.randint(3, 8),
            BrowsingIntent.RESEARCHING: random.randint(5, 15),
            BrowsingIntent.SHOPPING: random.randint(4, 10),
            BrowsingIntent.FORM_FILLING: random.randint(1, 3),
            BrowsingIntent.SEARCHING: random.randint(3, 12),
            BrowsingIntent.READING: random.randint(1, 4),
            BrowsingIntent.QUICK_CHECK: 1,
        }.get(intent, random.randint(2, 6))

    @classmethod
    def _page_type_for_intent(cls, intent: BrowsingIntent, index: int) -> str:
        """Determine page type based on intent and position in session."""
        if intent == BrowsingIntent.SEARCHING:
            return "search_results" if index % 2 == 0 else "article"
        elif intent == BrowsingIntent.SHOPPING:
            if index == 0:
                return "homepage"
            elif index < 3:
                return "category_page"
            else:
                return "product_page"
        elif intent == BrowsingIntent.READING:
            return "article"
        elif intent == BrowsingIntent.FORM_FILLING:
            return "form_page"
        return "generic"

    @classmethod
    def _select_scroll_pattern(cls, intent: BrowsingIntent, page_type: str) -> ScrollPattern:
        """Select appropriate scroll pattern."""
        if intent == BrowsingIntent.READING or page_type == "article":
            return random.choices(
                [ScrollPattern.READER, ScrollPattern.SLOW],
                weights=[0.7, 0.3],
            )[0]
        elif intent == BrowsingIntent.SEARCHING:
            return ScrollPattern.SCANNER
        elif page_type == "product_page":
            return random.choices(
                [ScrollPattern.SCANNER, ScrollPattern.JUMPER],
                weights=[0.6, 0.4],
            )[0]
        return ScrollPattern.SCANNER


# ═══════════════════════════════════════════════════════════
# Idle & Attention Simulator
# ═══════════════════════════════════════════════════════════

class AttentionSimulator:
    """Simulate human attention patterns and idle behavior."""

    @staticmethod
    def generate_idle_period(
        min_seconds: float = 2.0,
        max_seconds: float = 30.0,
    ) -> BehaviorAction:
        """Generate an idle period (user reading or distracted)."""
        duration = random.uniform(min_seconds, max_seconds)
        return BehaviorAction(
            action_type="idle",
            value=duration,
            duration_ms=int(duration * 1000),
            metadata={
                "attention": random.choice(["reading", "distracted", "thinking"]),
            },
        )

    @staticmethod
    def generate_tab_switch() -> List[BehaviorAction]:
        """Simulate switching to another tab and coming back."""
        away_time = random.lognormvariate(2.0, 1.0)  # Usually 5-20s, sometimes longer
        away_time = min(away_time, 120)  # Cap at 2 minutes

        return [
            BehaviorAction(
                action_type="tab_switch_away",
                duration_ms=0,
                metadata={"reason": random.choice([
                    "check_email", "notification", "compare_tab", "distraction",
                ])},
            ),
            BehaviorAction(
                action_type="wait",
                value=away_time,
                duration_ms=int(away_time * 1000),
                metadata={"reason": "away_on_other_tab"},
            ),
            BehaviorAction(
                action_type="tab_switch_back",
                duration_ms=0,
            ),
            BehaviorAction(
                action_type="wait",
                value=random.uniform(0.5, 2.0),
                duration_ms=random.randint(500, 2000),
                metadata={"reason": "reorienting"},
            ),
        ]

    @staticmethod
    def inject_natural_pauses(
        actions: List[BehaviorAction],
        pause_probability: float = 0.1,
    ) -> List[BehaviorAction]:
        """Insert random pauses into an action sequence."""
        result = []
        for action in actions:
            result.append(action)
            if random.random() < pause_probability:
                pause = random.uniform(0.3, 3.0)
                result.append(BehaviorAction(
                    action_type="wait",
                    value=pause,
                    duration_ms=int(pause * 1000),
                    metadata={"reason": "natural_pause"},
                ))
        return result

    @staticmethod
    def should_tab_switch(elapsed_seconds: float, threshold: float = 45.0) -> bool:
        """Probabilistically decide if user would switch tabs."""
        probability = min(0.5, elapsed_seconds / (threshold * 5))
        return random.random() < probability


# ═══════════════════════════════════════════════════════════
# Behavioral Intelligence Engine
# ═══════════════════════════════════════════════════════════

class BehaviorEngine:
    """
    Main behavioral intelligence engine. Ties together all sub-simulators.

    Usage:
        engine = BehaviorEngine()
        plan = engine.plan_session(BrowsingIntent.SHOPPING, hour=14)
        mouse_path = engine.generate_mouse_path((100, 100), (500, 300))
        typing = engine.generate_typing("hello@example.com")
    """

    VERSION = "29.0.0"

    def __init__(self) -> None:
        self._mouse = MousePathGenerator()
        self._scroll = ScrollSimulator()
        self._form = FormSimulator()
        self._planner = SessionPlanner()
        self._attention = AttentionSimulator()
        self._circadian = CircadianRhythm()
        self._sessions_planned = 0

    def plan_session(
        self,
        intent: BrowsingIntent = BrowsingIntent.CASUAL_BROWSING,
        pages: int = 0,
        hour: int = 12,
    ) -> SessionPlan:
        """Plan an entire browsing session."""
        self._sessions_planned += 1
        return SessionPlanner.plan_session(intent, pages, hour)

    def generate_mouse_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        overshoot: float = 0.15,
    ) -> List[Tuple[int, int]]:
        """Generate a realistic mouse movement path."""
        return MousePathGenerator.bezier_path(start, end, overshoot=overshoot)

    def generate_mouse_delays(self, path_length: int) -> List[float]:
        """Generate per-step delays for a mouse path."""
        return MousePathGenerator.generate_delays(path_length)

    def generate_typing(
        self,
        text: str,
        error_rate: float = 0.03,
        hour: int = 12,
    ) -> List[BehaviorAction]:
        """Generate typing actions with circadian adjustment."""
        adjusted_error_rate = CircadianRhythm.error_rate(hour, error_rate)
        return FormSimulator.generate_typing_pattern(text, error_rate=adjusted_error_rate)

    def generate_form_filling(
        self, fields: List[Dict[str, str]]
    ) -> List[BehaviorAction]:
        """Generate form filling behavior."""
        return FormSimulator.field_interaction_pattern(fields)

    def generate_scroll(
        self,
        pattern: ScrollPattern = ScrollPattern.READER,
        page_height: int = 5000,
    ) -> List[BehaviorAction]:
        """Generate scroll behavior."""
        if pattern == ScrollPattern.READER:
            return ScrollSimulator.reading_scroll(page_height)
        elif pattern == ScrollPattern.SCANNER:
            return ScrollSimulator.scanning_scroll(page_height)
        else:
            return ScrollSimulator.jump_scroll(page_height)

    def select_viewport_zone(
        self,
        page_type: str = "desktop",
    ) -> Tuple[int, int]:
        """Select a point from the viewport heatmap."""
        zones = VIEWPORT_ZONES.get(page_type, VIEWPORT_ZONES["desktop"])
        weights = [z.weight for z in zones]
        zone = random.choices(zones, weights=weights, k=1)[0]
        return zone.random_point()

    def get_page_timing(self, page_type: str = "generic") -> int:
        """Get realistic time-on-page in milliseconds."""
        min_t, max_t = SessionPlanner.PAGE_TIMING_MS.get(
            page_type, (5000, 30000)
        )
        return random.randint(min_t, max_t)

    def is_natural_browsing_time(self, hour: int) -> bool:
        """Check if the current hour is a natural browsing time."""
        return CircadianRhythm.is_natural_time(hour)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "sessions_planned": self._sessions_planned,
        }


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _typing_delay(base_ms: float = 80) -> float:
    """Generate a single realistic inter-key delay."""
    # Log-normal distribution (most keys fast, some slow)
    delay = random.lognormvariate(math.log(base_ms), 0.35)
    return max(25, min(300, delay))


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

behavior_engine: BehaviorEngine = BehaviorEngine()


