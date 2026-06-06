
"""
tg_bot/tests/test_pipeline.py — Pipeline Unit Tests
════════════════════════════════════════════════════
Tests for the 7-stage intelligent pipeline.
"""

import pytest
from arki_project.core.pipeline import (
    TaskClassifier, TaskCategory, ComplexityLevel,
    ModuleRouter, ReasoningStrategy, ContextBuilder,
    IntelligentPipeline, PipelineResult,
)


class TestTaskClassifier:
    """Tests for task classification."""

    def setup_method(self):
        self.classifier = TaskClassifier()

    def test_classify_search_intent_persian(self):
        cat, _, conf = self.classifier.classify("سرچ کن آخرین قیمت دلار")
        assert cat == TaskCategory.SEARCH

    def test_classify_search_intent_english(self):
        cat, _, conf = self.classifier.classify("search for latest news about AI")
        assert cat == TaskCategory.SEARCH

    def test_classify_image_intent(self):
        cat, _, _ = self.classifier.classify("یک لوگو بساز برای برندم")
        assert cat == TaskCategory.IMAGE

    def test_classify_code_intent(self):
        cat, _, _ = self.classifier.classify("write a python function to sort a list")
        assert cat == TaskCategory.CODE

    def test_classify_sales_intent(self):
        cat, _, _ = self.classifier.classify("تحلیل فروش این ماه و مقایسه با ماه قبل")
        assert cat in (TaskCategory.SALES, TaskCategory.ANALYSIS)

    def test_classify_simple_chat(self):
        cat, _, _ = self.classifier.classify("سلام")
        assert cat == TaskCategory.CHAT

    def test_classify_returns_confidence(self):
        _, _, conf = self.classifier.classify("test")
        assert 0.0 <= conf <= 1.0

    def test_classify_complexity_trivial(self):
        _, complexity, _ = self.classifier.classify("hi")
        assert complexity.value <= 2

    def test_classify_complexity_expert(self):
        long_research = (
            "تحقیق عمیق درباره تأثیر هوش مصنوعی بر بازار کار در ده سال آینده "
            "با بررسی مقالات آکادمیک و آمارهای جدید و مقایسه با شرایط فعلی "
            "و ارائه پیشنهادات عملی برای آمادگی. مرحله به مرحله تحلیل کن."
        )
        _, complexity, _ = self.classifier.classify(long_research)
        assert complexity.value >= 3

    def test_context_continuity(self):
        """Test that classifier remembers previous category for context continuity."""
        self.classifier.classify("قیمت بیت‌کوین چقدره؟ سرچ کن", user_id=1)
        cat, _, _ = self.classifier.classify("بیشتر توضیح بده", user_id=1)
        # Should have context bonus for SEARCH
        assert cat in (TaskCategory.SEARCH, TaskCategory.CHAT)

    def test_extract_features(self):
        features = self.classifier._extract_features("Hello? https://example.com 123 ```code```")
        assert features["has_question"] is True
        assert features["has_url"] is True
        assert features["has_code_block"] is True
        assert features["has_numbers"] is True
        assert features["word_count"] == 4


class TestModuleRouter:
    """Tests for module routing."""

    def setup_method(self):
        self.router = ModuleRouter()

    def test_chat_execution_plan(self):
        plan = self.router.get_execution_plan(TaskCategory.CHAT, ComplexityLevel.SIMPLE)
        modules = [step["module"] for step in plan]
        assert "memory_store" in modules or "multi_llm_orchestrator" in modules

    def test_search_execution_plan(self):
        plan = self.router.get_execution_plan(TaskCategory.SEARCH, ComplexityLevel.MODERATE)
        modules = [step["module"] for step in plan]
        assert "web_search" in modules

    def test_research_has_more_modules(self):
        plan_research = self.router.get_execution_plan(TaskCategory.RESEARCH, ComplexityLevel.EXPERT)
        plan_chat = self.router.get_execution_plan(TaskCategory.CHAT, ComplexityLevel.SIMPLE)
        assert len(plan_research) >= len(plan_chat)

    def test_reasoning_strategy_trivial(self):
        strategy = self.router.get_reasoning_strategy(TaskCategory.CHAT, ComplexityLevel.TRIVIAL)
        assert strategy == ReasoningStrategy.DIRECT

    def test_reasoning_strategy_complex(self):
        strategy = self.router.get_reasoning_strategy(TaskCategory.RESEARCH, ComplexityLevel.COMPLEX)
        assert strategy == ReasoningStrategy.REACT

    def test_reasoning_strategy_expert(self):
        strategy = self.router.get_reasoning_strategy(TaskCategory.RESEARCH, ComplexityLevel.EXPERT)
        assert strategy == ReasoningStrategy.TREE_OF_THOUGHT

    def test_simple_tasks_reduce_plan(self):
        plan_simple = self.router.get_execution_plan(TaskCategory.SEARCH, ComplexityLevel.TRIVIAL)
        plan_complex = self.router.get_execution_plan(TaskCategory.SEARCH, ComplexityLevel.COMPLEX)
        assert len(plan_simple) <= len(plan_complex)


class TestContextBuilder:
    """Tests for context building."""

    def setup_method(self):
        self.builder = ContextBuilder()

    def test_build_context_basic(self):
        ctx = self.builder.build_context(
            user_id=1, text="hello", category=TaskCategory.CHAT,
            chat_history=[], memory_results=None,
        )
        assert ctx["user_id"] == 1
        assert ctx["current_message"] == "hello"
        assert ctx["category"] == "chat"
        assert "task_hints" in ctx

    def test_build_context_with_memory(self):
        memories = [{"content": "Previous conversation about AI", "score": 0.9, "timestamp": 0}]
        ctx = self.builder.build_context(
            user_id=1, text="tell me more about AI",
            category=TaskCategory.CHAT,
            chat_history=[],
            memory_results=memories,
        )
        assert "semantic_memory" in ctx
        assert len(ctx["semantic_memory"]) == 1

    def test_user_profile_tracking(self):
        self.builder.update_user_profile(1, {"preferred_language": "fa"})
        ctx = self.builder.build_context(
            user_id=1, text="test", category=TaskCategory.CHAT,
            chat_history=[],
        )
        assert "user_profile" in ctx
        assert ctx["user_profile"]["preferred_language"] == "fa"

    def test_select_relevant_history(self):
        history = [{"content": f"Message {i}"} for i in range(30)]
        selected = self.builder._select_relevant_history("Message 5", history, max_messages=10)
        assert len(selected) <= 10

    def test_task_hints_by_category(self):
        hints_code = self.builder._get_task_hints(TaskCategory.CODE)
        hints_chat = self.builder._get_task_hints(TaskCategory.CHAT)
        assert hints_code["style"] == "technical"
        assert hints_chat["style"] == "conversational"


class TestIntelligentPipeline:
    """Integration tests for the full pipeline."""

    def setup_method(self):
        self.pipeline = IntelligentPipeline()

    @pytest.mark.asyncio
    async def test_process_simple_message(self):
        result = await self.pipeline.process(user_id=1, text="سلام خوبی؟")
        assert isinstance(result, PipelineResult)
        assert result.request_id
        assert result.category in TaskCategory
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_process_search_message(self):
        result = await self.pipeline.process(user_id=1, text="سرچ کن آخرین اخبار هوش مصنوعی")
        assert result.category == TaskCategory.SEARCH

    @pytest.mark.asyncio
    async def test_process_records_stats(self):
        await self.pipeline.process(user_id=1, text="test")
        stats = self.pipeline.get_stats()
        assert stats["total_requests"] >= 1

    @pytest.mark.asyncio
    async def test_enriched_prompt_generated(self):
        result = await self.pipeline.process(
            user_id=1,
            text="تحلیل عمیق بازار فروش آنلاین در ایران",
        )
        # Complex tasks should generate enriched prompts
        if result.complexity.value >= 3:
            assert result.enriched_prompt

    @pytest.mark.asyncio
    async def test_reasoning_trace_populated(self):
        result = await self.pipeline.process(user_id=1, text="test")
        assert len(result.reasoning_trace) >= 3
        steps = [t["step"] for t in result.reasoning_trace]
        assert "classify" in steps
        assert "complexity" in steps
        assert "strategy" in steps

    @pytest.mark.asyncio
    async def test_pipeline_duration_tracked(self):
        result = await self.pipeline.process(user_id=1, text="test")
        assert result.duration_ms >= 0


