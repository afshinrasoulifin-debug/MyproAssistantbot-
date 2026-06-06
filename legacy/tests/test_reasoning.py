
"""
tg_bot/tests/test_reasoning.py — Reasoning Engine Tests
════════════════════════════════════════════════════════
"""

from arki_project.core.reasoning import (
    ChainOfThoughtStrategy, ReActStrategy, TreeOfThoughtStrategy,
    SelfRefineStrategy, ReasoningEngine, ThoughtStep,
)


class TestChainOfThought:
    """Tests for CoT reasoning strategy."""

    def setup_method(self):
        self.cot = ChainOfThoughtStrategy()

    def test_build_prompt(self):
        prompt = self.cot.build_prompt("What is 2+2?")
        assert "step by step" in prompt.lower()
        assert "What is 2+2?" in prompt

    def test_build_prompt_with_context(self):
        prompt = self.cot.build_prompt("Solve this", context="Given x=5")
        assert "Given x=5" in prompt

    def test_parse_response(self):
        response = (
            "Step 1: First, understand the problem.\n"
            "Step 2: Calculate the answer.\n"
            "FINAL ANSWER: 4"
        )
        result = self.cot.parse_response(response)
        assert result.strategy == "chain_of_thought"
        assert result.final_answer == "4"
        assert len(result.steps) >= 1


class TestReAct:
    """Tests for ReAct reasoning strategy."""

    def setup_method(self):
        self.react = ReActStrategy()

    def test_build_initial_prompt(self):
        prompt = self.react.build_initial_prompt("Search for AI news")
        assert "web_search" in prompt
        assert "Thought:" in prompt

    def test_parse_step_with_action(self):
        response = (
            "Thought: I need to search for information.\n"
            "Action: web_search\n"
            "Action Input: latest AI news"
        )
        step = self.react.parse_step(response, 1)
        assert step.thought
        assert step.action == "web_search"
        assert step.action_input == "latest AI news"
        assert not step.is_final

    def test_parse_step_final_answer(self):
        response = (
            "Thought: I now have enough information.\n"
            "Final Answer: The latest AI news is about GPT-5."
        )
        step = self.react.parse_step(response, 3)
        assert step.is_final
        assert "GPT-5" in step.action_input


class TestTreeOfThought:
    """Tests for ToT reasoning strategy."""

    def setup_method(self):
        self.tot = TreeOfThoughtStrategy(num_branches=3)

    def test_build_branch_prompts(self):
        prompts = self.tot.build_branch_prompts("How to grow a business?")
        assert len(prompts) == 3
        assert "analytical" in prompts[0].lower()
        assert "creative" in prompts[1].lower()

    def test_build_voting_prompt(self):
        branches = ["Approach 1 result", "Approach 2 result", "Approach 3 result"]
        prompt = self.tot.build_voting_prompt("test question", branches)
        assert "evaluate" in prompt.lower()
        assert "APPROACH 1" in prompt


class TestSelfRefine:
    """Tests for Self-Refine strategy."""

    def setup_method(self):
        self.sr = SelfRefineStrategy()

    def test_build_initial_prompt(self):
        prompt = self.sr.build_initial_prompt("Write a poem")
        assert "Write a poem" in prompt

    def test_build_critique_prompt(self):
        prompt = self.sr.build_critique_prompt("Write a poem", "Roses are red...")
        assert "Roses are red" in prompt
        assert "Rate it" in prompt

    def test_should_continue_low_rating(self):
        assert self.sr.should_continue("Rating: 5/10", iteration=1) is True

    def test_should_continue_high_rating(self):
        assert self.sr.should_continue("Rating: 9/10", iteration=1) is False

    def test_should_stop_at_max_iterations(self):
        assert self.sr.should_continue("Rating: 3/10", iteration=3) is False


class TestReasoningEngine:
    """Tests for the main reasoning coordinator."""

    def setup_method(self):
        self.engine = ReasoningEngine()

    def test_get_cot_prompt(self):
        prompt = self.engine.get_strategy_prompt("cot", "test question")
        assert "step by step" in prompt.lower()

    def test_get_react_prompt(self):
        prompt = self.engine.get_strategy_prompt("react", "search for info")
        assert "Thought:" in prompt

    def test_get_direct_prompt(self):
        prompt = self.engine.get_strategy_prompt("direct", "hello")
        assert prompt == "hello"

    def test_get_tool_definitions(self):
        tools = self.engine.get_tool_definitions()
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "web_search" in tool_names
        assert "remember" in tool_names


class TestThoughtStep:
    """Tests for ThoughtStep data class."""

    def test_to_prompt_text(self):
        step = ThoughtStep(step_num=1, thought="Testing", action="search", action_input="query")
        text = step.to_prompt_text()
        assert "Step 1" in text
        assert "Testing" in text
        assert "search" in text


