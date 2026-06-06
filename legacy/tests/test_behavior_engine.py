
"""Tests for utils/behavior_engine.py — Advanced Behavioral Intelligence Engine."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.behavior_engine import (
    AttentionSimulator,
    BehaviorAction,
    BehaviorEngine,
    BrowsingIntent,
    CircadianRhythm,
    FormSimulator,
    MousePathGenerator,
    ScrollPattern,
    ScrollSimulator,
    SessionPlanner,
    VIEWPORT_ZONES,
    behavior_engine,
)


# ═══════════════════════════════════════════════════════════
# MousePathGenerator Tests
# ═══════════════════════════════════════════════════════════

class TestMousePathGenerator:
    def test_bezier_path_basic(self):
        path = MousePathGenerator.bezier_path((0, 0), (500, 300))
        assert len(path) > 5
        assert path[-1] == (500, 300)

    def test_bezier_path_starts_near_start(self):
        path = MousePathGenerator.bezier_path((100, 200), (600, 400))
        assert abs(path[0][0] - 100) < 20
        assert abs(path[0][1] - 200) < 20

    def test_bezier_path_custom_steps(self):
        path = MousePathGenerator.bezier_path((0, 0), (100, 100), steps=20)
        assert len(path) >= 20

    def test_bezier_path_no_overshoot(self):
        path = MousePathGenerator.bezier_path(
            (0, 0), (500, 300), overshoot=0.0
        )
        assert path[-1] == (500, 300)

    def test_generate_delays(self):
        delays = MousePathGenerator.generate_delays(20)
        assert len(delays) == 20
        assert all(d >= 2.0 for d in delays)

    def test_idle_drift(self):
        points = MousePathGenerator.idle_drift((500, 300), duration_ms=1000)
        assert len(points) >= 5
        for x, y in points:
            assert abs(x - 500) < 30
            assert abs(y - 300) < 30

    def test_short_distance_path(self):
        path = MousePathGenerator.bezier_path((100, 100), (105, 103))
        assert len(path) >= 10
        assert path[-1] == (105, 103)


# ═══════════════════════════════════════════════════════════
# ScrollSimulator Tests
# ═══════════════════════════════════════════════════════════

class TestScrollSimulator:
    def test_reading_scroll(self):
        actions = ScrollSimulator.reading_scroll(page_height=5000)
        assert len(actions) > 0
        scroll_actions = [a for a in actions if a.action_type == "scroll"]
        wait_actions = [a for a in actions if a.action_type == "wait"]
        assert len(scroll_actions) > 0
        assert len(wait_actions) > 0

    def test_scanning_scroll(self):
        actions = ScrollSimulator.scanning_scroll(page_height=5000)
        assert len(actions) > 0

    def test_jump_scroll(self):
        actions = ScrollSimulator.jump_scroll(page_height=5000, target_sections=3)
        scroll_to_actions = [a for a in actions if a.action_type == "scroll_to"]
        assert len(scroll_to_actions) == 3

    def test_reading_scroll_respects_page_height(self):
        actions = ScrollSimulator.reading_scroll(page_height=2000)
        scroll_total = sum(
            a.value for a in actions
            if a.action_type == "scroll" and isinstance(a.value, (int, float))
        )
        assert scroll_total <= 2000


# ═══════════════════════════════════════════════════════════
# FormSimulator Tests
# ═══════════════════════════════════════════════════════════

class TestFormSimulator:
    def test_typing_pattern(self):
        actions = FormSimulator.generate_typing_pattern("hello")
        assert len(actions) >= 5
        keypress_actions = [a for a in actions if a.action_type == "keypress"]
        assert len(keypress_actions) >= 5

    def test_typing_with_errors(self):
        actions = FormSimulator.generate_typing_pattern(
            "hello world test", error_rate=0.5
        )
        has_backspace = any(
            a.value == "Backspace" for a in actions if a.action_type == "keypress"
        )
        assert has_backspace

    def test_field_interaction_pattern(self):
        fields = [
            {"selector": "#name", "value": "John", "type": "text"},
            {"selector": "#email", "value": "j@x.com", "type": "email"},
        ]
        actions = FormSimulator.field_interaction_pattern(fields)
        focus_actions = [a for a in actions if a.action_type == "focus"]
        blur_actions = [a for a in actions if a.action_type == "blur"]
        assert len(focus_actions) == 2
        assert len(blur_actions) == 2


# ═══════════════════════════════════════════════════════════
# CircadianRhythm Tests
# ═══════════════════════════════════════════════════════════

class TestCircadianRhythm:
    def test_activity_curve_length(self):
        assert len(CircadianRhythm.ACTIVITY_CURVE) == 24

    def test_peak_at_evening(self):
        peak = max(range(24), key=lambda h: CircadianRhythm.activity_level(h))
        assert 17 <= peak <= 21

    def test_low_at_night(self):
        assert CircadianRhythm.activity_level(3) < 0.1

    def test_adjust_delays_night_slower(self):
        day_delay = CircadianRhythm.adjust_delays(100, 12)
        night_delay = CircadianRhythm.adjust_delays(100, 3)
        assert night_delay > day_delay

    def test_session_duration_varies(self):
        day_dur = CircadianRhythm.session_duration(12)
        night_dur = CircadianRhythm.session_duration(3)
        assert day_dur > night_dur

    def test_error_rate_higher_at_night(self):
        day_err = CircadianRhythm.error_rate(12)
        night_err = CircadianRhythm.error_rate(3)
        assert night_err > day_err

    def test_natural_time(self):
        assert CircadianRhythm.is_natural_time(12)
        assert CircadianRhythm.is_natural_time(20)

    def test_unnatural_time(self):
        assert not CircadianRhythm.is_natural_time(3, threshold=0.10)


# ═══════════════════════════════════════════════════════════
# SessionPlanner Tests
# ═══════════════════════════════════════════════════════════

class TestSessionPlanner:
    def test_plan_casual_session(self):
        plan = SessionPlanner.plan_session(BrowsingIntent.CASUAL_BROWSING)
        assert plan.intent == BrowsingIntent.CASUAL_BROWSING
        assert plan.pages_to_visit >= 1
        assert len(plan.actions) > 0
        assert plan.total_duration_ms > 0

    def test_plan_shopping_session(self):
        plan = SessionPlanner.plan_session(BrowsingIntent.SHOPPING, pages=5)
        assert plan.pages_to_visit == 5
        nav_actions = [a for a in plan.actions if a.action_type == "navigate"]
        assert len(nav_actions) == 5

    def test_plan_quick_check(self):
        plan = SessionPlanner.plan_session(BrowsingIntent.QUICK_CHECK)
        assert plan.pages_to_visit == 1

    def test_plan_to_dict(self):
        plan = SessionPlanner.plan_session(BrowsingIntent.READING, pages=2)
        d = plan.to_dict()
        assert d["intent"] == "reading"
        assert d["pages_to_visit"] == 2
        assert d["action_count"] > 0

    def test_page_timing_defined(self):
        for ptype in SessionPlanner.PAGE_TIMING_MS:
            min_t, max_t = SessionPlanner.PAGE_TIMING_MS[ptype]
            assert max_t > min_t > 0


# ═══════════════════════════════════════════════════════════
# AttentionSimulator Tests
# ═══════════════════════════════════════════════════════════

class TestAttentionSimulator:
    def test_generate_idle_period(self):
        action = AttentionSimulator.generate_idle_period(1.0, 5.0)
        assert action.action_type == "idle"
        assert 1.0 <= action.value <= 5.0

    def test_generate_tab_switch(self):
        actions = AttentionSimulator.generate_tab_switch()
        assert len(actions) == 4
        assert actions[0].action_type == "tab_switch_away"
        assert actions[2].action_type == "tab_switch_back"

    def test_inject_natural_pauses(self):
        original = [
            BehaviorAction(action_type="click", duration_ms=50),
            BehaviorAction(action_type="click", duration_ms=50),
            BehaviorAction(action_type="click", duration_ms=50),
        ]
        result = AttentionSimulator.inject_natural_pauses(original, pause_probability=1.0)
        assert len(result) == 6

    def test_should_tab_switch_increases_with_time(self):
        prob_short = sum(
            AttentionSimulator.should_tab_switch(5.0) for _ in range(1000)
        ) / 1000
        prob_long = sum(
            AttentionSimulator.should_tab_switch(300.0) for _ in range(1000)
        ) / 1000
        assert prob_long > prob_short


# ═══════════════════════════════════════════════════════════
# Viewport Zones Tests
# ═══════════════════════════════════════════════════════════

class TestViewportZones:
    def test_desktop_zones_exist(self):
        assert "desktop" in VIEWPORT_ZONES
        assert len(VIEWPORT_ZONES["desktop"]) > 0

    def test_search_results_zones(self):
        assert "search_results" in VIEWPORT_ZONES
        zones = VIEWPORT_ZONES["search_results"]
        first_result = [z for z in zones if z.name == "first_result"]
        assert len(first_result) == 1
        assert first_result[0].weight >= 8.0

    def test_zone_random_point(self):
        zone = VIEWPORT_ZONES["desktop"][0]
        x, y = zone.random_point(1920, 1080)
        assert 0 <= x <= 1920
        assert 0 <= y <= 1080


# ═══════════════════════════════════════════════════════════
# BehaviorEngine (Main) Tests
# ═══════════════════════════════════════════════════════════

class TestBehaviorEngine:
    def test_singleton(self):
        assert behavior_engine is not None
        assert isinstance(behavior_engine, BehaviorEngine)

    def test_version(self):
        assert "TITAN" in BehaviorEngine.VERSION

    def test_plan_session(self):
        engine = BehaviorEngine()
        plan = engine.plan_session(BrowsingIntent.SHOPPING, pages=3)
        assert plan.pages_to_visit == 3

    def test_generate_mouse_path(self):
        engine = BehaviorEngine()
        path = engine.generate_mouse_path((0, 0), (500, 300))
        assert len(path) > 5
        assert path[-1] == (500, 300)

    def test_generate_mouse_delays(self):
        engine = BehaviorEngine()
        delays = engine.generate_mouse_delays(15)
        assert len(delays) == 15

    def test_generate_typing(self):
        engine = BehaviorEngine()
        actions = engine.generate_typing("test@email.com")
        assert len(actions) >= 14

    def test_generate_form_filling(self):
        engine = BehaviorEngine()
        fields = [{"selector": "#name", "value": "John", "type": "text"}]
        actions = engine.generate_form_filling(fields)
        assert len(actions) > 0

    def test_generate_scroll(self):
        engine = BehaviorEngine()
        actions = engine.generate_scroll(ScrollPattern.READER)
        assert len(actions) > 0

    def test_select_viewport_zone(self):
        engine = BehaviorEngine()
        x, y = engine.select_viewport_zone("desktop")
        assert 0 <= x <= 1920
        assert 0 <= y <= 1080

    def test_get_page_timing(self):
        engine = BehaviorEngine()
        timing = engine.get_page_timing("article")
        assert 15000 <= timing <= 180000

    def test_is_natural_browsing_time(self):
        engine = BehaviorEngine()
        assert engine.is_natural_browsing_time(14)

    def test_get_stats(self):
        engine = BehaviorEngine()
        engine.plan_session(BrowsingIntent.CASUAL_BROWSING)
        stats = engine.get_stats()
        assert stats["sessions_planned"] >= 1

    def test_behavior_action_to_dict(self):
        action = BehaviorAction(
            action_type="click",
            target=(100, 200),
            duration_ms=50,
        )
        d = action.to_dict()
        assert d["action"] == "click"
        assert d["target"] == (100, 200)


