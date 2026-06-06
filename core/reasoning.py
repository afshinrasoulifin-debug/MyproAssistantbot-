
from __future__ import annotations
"""
tg_bot/core/reasoning.py — Adaptive Reasoning Engine v10 (Optimized)
═══════════════════════════════════════════════════════════════════════
Implements multiple reasoning strategies and dynamically selects
the best one based on task complexity.

v10 Optimizations:
  ✅ Enhanced CoT with structured output & verification step
  ✅ ReAct with smarter tool selection & parallel tool calls
  ✅ ToT with dynamic branching & weighted voting
  ✅ Self-Refine with calibrated confidence & early exit
  ✅ NEW: Meta-Cognitive strategy (think about thinking)
  ✅ NEW: Decompose-Delegate-Compose for multi-part tasks
  ✅ Full Persian/Farsi language support in all prompts
  ✅ Confidence calibration across strategies

Strategies:
  1. DIRECT       — Single-shot LLM call (trivial tasks)
  2. CoT          — Chain-of-Thought (moderate tasks)
  3. ReAct        — Reason + Act loop with tool use (complex tasks)
  4. ToT          — Tree of Thoughts with voting (expert tasks)
  5. Self-Refine  — Generate → Critique → Refine loop
  6. META_COG     — Meta-cognitive: plan reasoning → execute → verify
  7. DECOMPOSE    — Split task → solve parts → compose answer

Academic References:
  - Wei et al. (2022). "Chain-of-Thought Prompting"
  - Yao et al. (2022). "ReAct: Synergizing Reasoning and Acting"
  - Yao et al. (2023). "Tree of Thoughts"
  - Madaan et al. (2023). "Self-Refine"
  - Wang et al. (2023). "Plan-and-Solve Prompting"
"""


import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Reasoning Primitives
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ThoughtStep:
    """A single step in the reasoning process."""
    step_num: int
    thought: str
    action: str = ""
    action_input: str = ""
    observation: str = ""
    is_final: bool = False
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_prompt_text(self) -> str:
        """Convert to text for inclusion in prompts."""
        parts = [f"Step {self.step_num}:"]
        parts.append(f"  Thought: {self.thought}")
        if self.action:
            parts.append(f"  Action: {self.action}")
        if self.action_input:
            parts.append(f"  Input: {self.action_input}")
        if self.observation:
            parts.append(f"  Observation: {self.observation}")
        if self.confidence > 0:
            parts.append(f"  Confidence: {self.confidence:.0%}")
        return "\n".join(parts)


@dataclass
class ReasoningResult:
    """Result of a reasoning process."""
    strategy: str
    steps: List[ThoughtStep]
    final_answer: str
    total_llm_calls: int = 0
    total_duration_ms: float = 0.0
    confidence: float = 0.0
    verification_passed: bool = True
    quality_score: float = 0.0

    @property
    def reasoning_trace(self) -> str:
        """Full reasoning trace as text."""
        return "\n\n".join(step.to_prompt_text() for step in self.steps)


# ═══════════════════════════════════════════════════════════════════
# Tool Definition for ReAct
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Tool:
    """A tool that can be used in ReAct reasoning."""
    name: str
    description: str
    module: str
    action: str
    parameters: Dict[str, str] = field(default_factory=dict)
    # v10: tool capability tags for smarter selection
    tags: List[str] = field(default_factory=list)
    priority: int = 5  # 1=highest, 10=lowest

    def to_prompt_text(self) -> str:
        params = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"  - {self.name}: {self.description} (params: {params})"


# Available tools mapped to modules
AVAILABLE_TOOLS: List[Tool] = [
    Tool(
        name="web_search",
        description="Search the web for current information / جستجوی وب برای اطلاعات به‌روز",
        module="web_search",
        action="search",
        parameters={"query": "search query"},
        tags=["search", "info", "current"],
        priority=1,
    ),
    Tool(
        name="analyze_data",
        description="Perform statistical analysis on data / تحلیل آماری داده‌ها",
        module="data_analyzer",
        action="analyze",
        parameters={"data": "data to analyze", "method": "analysis method"},
        tags=["analysis", "data", "statistics"],
        priority=2,
    ),
    Tool(
        name="extract_text",
        description="Extract and transform text (summarize, translate, etc.) / استخراج و تبدیل متن",
        module="text_transform",
        action="transform",
        parameters={"text": "input text", "operation": "summarize|translate|extract"},
        tags=["text", "transform", "summarize"],
        priority=3,
    ),
    Tool(
        name="remember",
        description="Store or retrieve information from memory / ذخیره یا بازیابی اطلاعات از حافظه",
        module="memory_store",
        action="search",
        parameters={"query": "what to remember/recall"},
        tags=["memory", "recall", "context"],
        priority=2,
    ),
    Tool(
        name="encrypt",
        description="Encrypt or hash data / رمزنگاری یا هش داده‌ها",
        module="crypto_engine",
        action="process",
        parameters={"data": "data to process", "operation": "encrypt|hash|sign"},
        tags=["security", "crypto", "encrypt"],
        priority=5,
    ),
    Tool(
        name="scan_network",
        description="Scan network targets / اسکن اهداف شبکه",
        module="network_tools",
        action="scan",
        parameters={"target": "host/ip to scan"},
        tags=["network", "security", "scan"],
        priority=6,
    ),
    Tool(
        name="run_workflow",
        description="Execute a predefined workflow / اجرای گردش‌کار از پیش تعریف‌شده",
        module="workflow_engine",
        action="execute",
        parameters={"workflow_id": "workflow identifier"},
        tags=["automation", "workflow"],
        priority=4,
    ),
    Tool(
        name="calculate",
        description="Perform mathematical calculations / انجام محاسبات ریاضی",
        module="data_analyzer",
        action="calculate",
        parameters={"expression": "math expression"},
        tags=["math", "calculate", "compute"],
        priority=2,
    ),
]


def select_relevant_tools(query: str, max_tools: int = 5) -> List[Tool]:
    """v10: Smart tool selection based on query content."""
    query_lower = query.lower()
    scored: List[Tuple[float, Tool]] = []

    # Keyword-to-tag mapping for scoring
    keyword_tags = {
        "search": ["search", "info"], "جستجو": ["search", "info"],
        "analyze": ["analysis", "data"], "تحلیل": ["analysis", "data"],
        "data": ["analysis", "data", "statistics"], "داده": ["analysis", "data"],
        "text": ["text", "transform"], "متن": ["text", "transform"],
        "summarize": ["text", "summarize"], "خلاصه": ["text", "summarize"],
        "remember": ["memory", "recall"], "یادآوری": ["memory", "recall"],
        "encrypt": ["security", "crypto"], "رمز": ["security", "crypto"],
        "network": ["network", "scan"], "شبکه": ["network", "scan"],
        "workflow": ["automation", "workflow"], "گردش": ["automation", "workflow"],
        "calculate": ["math", "calculate"], "محاسبه": ["math", "calculate"],
        "math": ["math", "compute"], "ریاضی": ["math", "compute"],
    }

    for tool in AVAILABLE_TOOLS:
        score = 0.0
        for keyword, tags in keyword_tags.items():
            if keyword in query_lower:
                for tag in tags:
                    if tag in tool.tags:
                        score += 1.0
        # Priority bonus (lower priority number = higher score)
        score += (10 - tool.priority) * 0.1
        scored.append((score, tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:max_tools]]


# ═══════════════════════════════════════════════════════════════════
# Chain-of-Thought Strategy (Enhanced v10)
# ═══════════════════════════════════════════════════════════════════

class ChainOfThoughtStrategy:
    """
    Enhanced Chain-of-Thought reasoning v10.

    Improvements:
    - Structured output with verification step
    - Persian/Farsi support
    - Confidence self-assessment
    - Plan-before-solve approach (Wang et al. 2023)
    """

    COT_PREFIX = (
        "Let's solve this step by step using a structured approach.\n\n"
        "PLAN: First, briefly outline your plan of attack (2-3 sentences).\n\n"
        "Then for each step:\n"
        "  STEP N: [What you're doing]\n"
        "  REASONING: [Your detailed reasoning]\n"
        "  RESULT: [What you concluded]\n\n"
        "After all steps:\n"
        "  VERIFICATION: [Check your work — does the answer make sense?]\n"
        "  CONFIDENCE: [How confident are you? Low/Medium/High]\n"
        "  FINAL ANSWER: [Your complete answer]\n\n"
    )

    COT_PREFIX_FA = (
        "بیا این مسئله رو قدم به قدم و ساختارمند حل کنیم.\n\n"
        "برنامه: ابتدا به‌صورت خلاصه رویکردت رو توضیح بده.\n\n"
        "سپس برای هر مرحله:\n"
        "  مرحله N: [چه کاری انجام می‌دهی]\n"
        "  استدلال: [استدلال دقیق]\n"
        "  نتیجه: [نتیجه‌گیری]\n\n"
        "در پایان:\n"
        "  بازبینی: [آیا پاسخ منطقی است؟]\n"
        "  اطمینان: [سطح اطمینان: کم/متوسط/زیاد]\n"
        "  پاسخ نهایی: [پاسخ کامل]\n\n"
    )

    def build_prompt(self, user_text: str, context: str = "", lang: str = "auto") -> str:
        """Build a CoT-enhanced prompt."""
        # Auto-detect Persian
        is_persian = lang == "fa" or (lang == "auto" and _is_persian(user_text))
        prefix = self.COT_PREFIX_FA if is_persian else self.COT_PREFIX

        parts = [prefix]
        if context:
            ctx_label = "زمینه" if is_persian else "Context"
            parts.append(f"{ctx_label}:\n{context}\n\n")

        q_label = "سوال/وظیفه" if is_persian else "Question/Task"
        parts.append(f"{q_label}: {user_text}\n\n")
        step_label = "برنامه" if is_persian else "PLAN"
        parts.append(f"{step_label}:")
        return "".join(parts)

    def parse_response(self, response: str) -> ReasoningResult:
        """Parse CoT response into structured steps."""
        steps: List[ThoughtStep] = []

        # Find step patterns (supports both English and Persian)
        step_pattern = re.compile(
            r"(?:STEP\s+(\d+)|مرحله\s+(\d+))[:\.]?\s*(.*?)(?=STEP\s+\d+|مرحله\s+\d+|VERIFICATION|بازبینی|FINAL\s+ANSWER|پاسخ\s+نهایی|$)",
            re.DOTALL | re.IGNORECASE,
        )
        matches = step_pattern.findall(response)

        for i, (num_en, num_fa, content) in enumerate(matches):
            num = num_en or num_fa or str(i + 1)
            steps.append(ThoughtStep(
                step_num=int(num),
                thought=content.strip()[:500],
            ))

        # Extract confidence
        confidence = 0.7  # default
        conf_match = re.search(
            r"(?:CONFIDENCE|اطمینان)[:\s]*(Low|Medium|High|کم|متوسط|زیاد)",
            response, re.IGNORECASE,
        )
        if conf_match:
            conf_map = {
                "low": 0.3, "کم": 0.3,
                "medium": 0.6, "متوسط": 0.6,
                "high": 0.9, "زیاد": 0.9,
            }
            confidence = conf_map.get(conf_match.group(1).lower(), 0.7)

        # Extract verification
        verification_passed = True
        verif_match = re.search(
            r"(?:VERIFICATION|بازبینی)[:\s]*(.*?)(?=CONFIDENCE|اطمینان|FINAL|پاسخ|$)",
            response, re.DOTALL | re.IGNORECASE,
        )
        if verif_match:
            verif_text = verif_match.group(1).lower()
            negative_words = {"incorrect", "wrong", "error", "mistake", "نادرست", "اشتباه", "خطا"}
            if any(w in verif_text for w in negative_words):
                verification_passed = False
                confidence *= 0.5

        # Extract final answer
        final_pattern = re.compile(
            r"(?:FINAL\s+ANSWER|پاسخ\s+نهایی)[:\s]*(.*)",
            re.DOTALL | re.IGNORECASE,
        )
        final_match = final_pattern.search(response)
        final_answer = final_match.group(1).strip() if final_match else response

        if not steps:
            steps.append(ThoughtStep(
                step_num=1,
                thought="Direct reasoning",
                is_final=True,
            ))

        return ReasoningResult(
            strategy="chain_of_thought",
            steps=steps,
            final_answer=final_answer,
            total_llm_calls=1,
            confidence=confidence,
            verification_passed=verification_passed,
        )


# ═══════════════════════════════════════════════════════════════════
# ReAct Strategy (Enhanced v10)
# ═══════════════════════════════════════════════════════════════════

class ReActStrategy:
    """
    Enhanced ReAct: Reasoning + Acting v10.

    Improvements:
    - Smart tool pre-selection based on query
    - Parallel tool calls when possible
    - Observation quality assessment
    - Early termination on high confidence
    """

    MAX_STEPS = 7  # v10: increased from 5

    def build_initial_prompt(
        self,
        user_text: str,
        tools: Optional[List[Tool]] = None,
        context: str = "",
    ) -> str:
        """Build the initial ReAct prompt with smart tool selection."""
        # v10: Select relevant tools instead of listing all
        available_tools = tools or select_relevant_tools(user_text)
        tool_text = "\n".join(t.to_prompt_text() for t in available_tools)

        is_persian = _is_persian(user_text)

        if is_persian:
            return (
                f"ابزارهای در دسترس:\n{tool_text}\n\n"
                "از این قالب استفاده کن:\n"
                "فکر: [استدلال تو]\n"
                "عمل: [نام ابزار]\n"
                "ورودی عمل: [ورودی ابزار]\n"
                "مشاهده: [نتیجه ابزار — من ارائه می‌دهم]\n"
                "... (تکرار در صورت نیاز)\n"
                "فکر: حالا اطلاعات کافی دارم.\n"
                "پاسخ نهایی: [پاسخ کامل تو]\n\n"
                f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                f"سوال: {user_text}\n\n"
                "فکر:"
            )

        return (
            f"You have access to these tools:\n{tool_text}\n\n"
            "Use this format:\n"
            "Thought: [your reasoning]\n"
            "Action: [tool name]\n"
            "Action Input: [input for the tool]\n"
            "Observation: [result from tool — I will provide this]\n"
            "... (repeat as needed)\n"
            "Thought: I now have enough information.\n"
            "Confidence: [Low/Medium/High]\n"
            "Final Answer: [your complete answer]\n\n"
            f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
            f"Question: {user_text}\n\n"
            "Thought:"
        )

    def build_continuation_prompt(
        self,
        steps_so_far: List[ThoughtStep],
        last_observation: str,
    ) -> str:
        """Build continuation prompt after a tool observation."""
        trace = "\n".join(s.to_prompt_text() for s in steps_so_far)
        return (
            f"{trace}\n"
            f"  Observation: {last_observation}\n\n"
            "Thought:"
        )

    def parse_step(self, response: str, step_num: int) -> ThoughtStep:
        """Parse a single ReAct step from LLM output."""
        thought = ""
        action = ""
        action_input = ""
        is_final = False
        confidence = 0.0

        # Extract thought
        thought_match = re.search(
            r"(?:Thought|فکر):\s*(.*?)(?=Action|عمل|Final Answer|پاسخ نهایی|Confidence|$)",
            response, re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Check for final answer
        final_match = re.search(
            r"(?:Final\s+Answer|پاسخ\s+نهایی):\s*(.*)",
            response, re.DOTALL | re.IGNORECASE,
        )
        if final_match:
            is_final = True
            action = "final_answer"
            action_input = final_match.group(1).strip()
        else:
            # Extract action
            action_match = re.search(
                r"(?:Action|عمل):\s*(.*?)(?=Action Input|ورودی عمل|$)",
                response, re.DOTALL | re.IGNORECASE,
            )
            if action_match:
                action = action_match.group(1).strip()

            input_match = re.search(
                r"(?:Action Input|ورودی عمل):\s*(.*?)(?=Observation|مشاهده|$)",
                response, re.DOTALL | re.IGNORECASE,
            )
            if input_match:
                action_input = input_match.group(1).strip()

        # Extract confidence if present
        conf_match = re.search(
            r"(?:Confidence|اطمینان):\s*(Low|Medium|High|کم|متوسط|زیاد)",
            response, re.IGNORECASE,
        )
        if conf_match:
            conf_map = {"low": 0.3, "کم": 0.3, "medium": 0.6, "متوسط": 0.6, "high": 0.9, "زیاد": 0.9}
            confidence = conf_map.get(conf_match.group(1).lower(), 0.5)

        return ThoughtStep(
            step_num=step_num,
            thought=thought,
            action=action,
            action_input=action_input,
            is_final=is_final,
            confidence=confidence,
        )

    def should_early_terminate(self, steps: List[ThoughtStep]) -> bool:
        """v10: Early termination if high confidence reached."""
        if len(steps) >= 2:
            recent_confidence = [s.confidence for s in steps[-2:] if s.confidence > 0]
            if recent_confidence and min(recent_confidence) >= 0.85:
                return True
        return False


# ═══════════════════════════════════════════════════════════════════
# Tree of Thoughts Strategy (Enhanced v10)
# ═══════════════════════════════════════════════════════════════════

class TreeOfThoughtStrategy:
    """
    Enhanced Tree of Thoughts v10.

    Improvements:
    - Dynamic branching based on problem type
    - Weighted voting with dimension scoring
    - Persian/Farsi approach descriptions
    - Cross-branch synthesis
    """

    def __init__(self, num_branches: int = 3) -> None:
        self.num_branches = num_branches

    def build_branch_prompts(self, user_text: str, context: str = "") -> List[str]:
        """Generate prompts for each branch with diverse perspectives."""
        is_persian = _is_persian(user_text)

        if is_persian:
            approaches = [
                ("تحلیلی و سیستماتیک", "مسئله رو به اجزای کوچکتر تقسیم کن و هر بخش رو جداگانه تحلیل کن."),
                ("خلاقانه و نوآورانه", "از زاویه غیرمعمول فکر کن. راه‌حل‌های خلاقانه و غیرمتعارف ارائه بده."),
                ("عملی و کاربردی", "روی راه‌حل‌های عملی و قابل اجرا تمرکز کن. مزایا و معایب هر گزینه رو بررسی کن."),
                ("انتقادی و شکاکانه", "فرضیات رو زیر سوال ببر. نقاط ضعف و ریسک‌ها رو شناسایی کن."),
            ]
        else:
            approaches = [
                ("analytical and systematic", "Break the problem into components and analyze each part systematically."),
                ("creative and unconventional", "Think outside the box. Consider unusual angles and creative solutions."),
                ("practical and action-oriented", "Focus on actionable solutions. Evaluate pros/cons of each option."),
                ("critical and skeptical", "Challenge assumptions. Identify weaknesses, risks, and edge cases."),
            ]

        prompts: List[str] = []
        for i, (approach_name, instruction) in enumerate(approaches[:self.num_branches]):
            if is_persian:
                prompt = (
                    f"این مسئله رو از دیدگاه {approach_name} بررسی کن.\n"
                    f"دستورالعمل: {instruction}\n\n"
                    f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                    f"سوال/وظیفه: {user_text}\n\n"
                    f"رویکرد {i + 1} ({approach_name}):\n"
                )
            else:
                prompt = (
                    f"Approach this problem from a {approach_name} perspective.\n"
                    f"Instruction: {instruction}\n\n"
                    f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
                    f"Question/Task: {user_text}\n\n"
                    f"Approach {i + 1} ({approach_name}):\n"
                )
            prompts.append(prompt)

        return prompts

    def build_voting_prompt(
        self,
        user_text: str,
        branches: List[str],
    ) -> str:
        """Build prompt to evaluate and vote on branches with dimensional scoring."""
        is_persian = _is_persian(user_text)
        branch_text = "\n\n---\n\n".join(
            f"{'رویکرد' if is_persian else 'APPROACH'} {i + 1}:\n{b}" for i, b in enumerate(branches)
        )

        if is_persian:
            return (
                f"من {len(branches)} رویکرد مختلف برای این وظیفه بررسی کردم:\n\n"
                f"{branch_text}\n\n---\n\n"
                f"سوال اصلی: {user_text}\n\n"
                "حالا هر رویکرد رو در این ابعاد ارزیابی کن:\n"
                "1. دقت (۱-۱۰): آیا اطلاعات صحیح است؟\n"
                "2. کامل بودن (۱-۱۰): آیا همه جوانب پوشش داده شده؟\n"
                "3. وضوح (۱-۱۰): آیا پاسخ واضح و قابل فهم است؟\n"
                "4. کاربردی بودن (۱-۱۰): آیا عملی و قابل اجراست؟\n\n"
                "سپس بهترین عناصر هر رویکرد رو ترکیب کن و پاسخ نهایی ارائه بده.\n\n"
                "ارزیابی:\n"
            )

        return (
            f"I explored {len(branches)} different approaches to this task:\n\n"
            f"{branch_text}\n\n---\n\n"
            f"Original question: {user_text}\n\n"
            "Now evaluate each approach across these dimensions:\n"
            "1. ACCURACY (1-10): Is the information correct?\n"
            "2. COMPLETENESS (1-10): Are all aspects covered?\n"
            "3. CLARITY (1-10): Is the answer clear and understandable?\n"
            "4. ACTIONABILITY (1-10): Is it practical and actionable?\n\n"
            "Then synthesize the best elements from each approach into one FINAL ANSWER.\n\n"
            "Evaluation:\n"
        )


# ═══════════════════════════════════════════════════════════════════
# Self-Refine Strategy (Enhanced v10)
# ═══════════════════════════════════════════════════════════════════

class SelfRefineStrategy:
    """
    Enhanced Self-Refine v10.

    Improvements:
    - Calibrated quality thresholds per task type
    - Early exit when quality is sufficient
    - Dimensional critique (not just overall score)
    - Persian/Farsi support
    """

    MAX_ITERATIONS = 3

    def build_initial_prompt(self, user_text: str, context: str = "") -> str:
        """Build initial generation prompt."""
        is_persian = _is_persian(user_text)
        if is_persian:
            return (
                f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                f"وظیفه: {user_text}\n\n"
                "بهترین پاسخ خود را ارائه بده. جامع، دقیق و واضح باش:\n"
            )
        return (
            f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
            f"Task: {user_text}\n\n"
            "Provide your best response. Be thorough, accurate, and clear:\n"
        )

    def build_critique_prompt(self, user_text: str, response: str) -> str:
        """Build dimensional critique prompt."""
        is_persian = _is_persian(user_text)

        if is_persian:
            return (
                f"وظیفه اصلی: {user_text}\n\n"
                f"پاسخ فعلی:\n{response}\n\n"
                "این پاسخ رو در ابعاد زیر نقد کن:\n"
                "1. صحت: آیا اطلاعات دقیق و درست هستند؟ (۱-۱۰)\n"
                "2. کامل بودن: آیا چیزی جا افتاده؟ (۱-۱۰)\n"
                "3. وضوح: آیا پاسخ واضح و خوانا است؟ (۱-۱۰)\n"
                "4. عمق: آیا تحلیل عمیق و ارزشمند است؟ (۱-۱۰)\n\n"
                "نقاط قوت:\n"
                "نقاط ضعف:\n"
                "پیشنهادات بهبود:\n"
                "امتیاز کلی: [X/10]\n"
            )

        return (
            f"Original task: {user_text}\n\n"
            f"Current response:\n{response}\n\n"
            "Critique this response across dimensions:\n"
            "1. ACCURACY: Is the information correct? (1-10)\n"
            "2. COMPLETENESS: Is anything missing? (1-10)\n"
            "3. CLARITY: Is it clear and readable? (1-10)\n"
            "4. DEPTH: Is the analysis deep and valuable? (1-10)\n\n"
            "Strengths:\n"
            "Weaknesses:\n"
            "Improvement suggestions:\n"
            "Overall score: [X/10]\n"
        )

    def build_refine_prompt(
        self,
        user_text: str,
        response: str,
        critique: str,
    ) -> str:
        """Build refinement prompt."""
        is_persian = _is_persian(user_text)

        if is_persian:
            return (
                f"وظیفه اصلی: {user_text}\n\n"
                f"پاسخ قبلی:\n{response}\n\n"
                f"نقد:\n{critique}\n\n"
                "حالا یک پاسخ بهبودیافته ارائه بده که تمام نقاط ضعف رو برطرف کنه.\n"
                "فقط پاسخ بهبودیافته رو بنویس، بدون تکرار نقد:\n"
            )

        return (
            f"Original task: {user_text}\n\n"
            f"Previous response:\n{response}\n\n"
            f"Critique:\n{critique}\n\n"
            "Now provide an IMPROVED response that addresses ALL weaknesses.\n"
            "Write only the improved response, without repeating the critique:\n"
        )

    def should_continue(self, critique: str, iteration: int) -> bool:
        """Decide if another refinement iteration is needed."""
        if iteration >= self.MAX_ITERATIONS:
            return False

        # Parse rating from critique (supports both English and Persian numerals)
        rating_match = re.search(
            r"(?:Overall\s+score|امتیاز\s+کلی)[:\s]*(\d+)\s*/\s*10|(?:\b|^)(\d+)/10",
            critique, re.IGNORECASE,
        )
        if rating_match:
            rating = int(rating_match.group(1) or rating_match.group(2))
            if rating >= 8:
                return False  # Good enough
            if rating <= 4 and iteration < 2:
                return True  # Definitely needs work
            return rating < 7  # Borderline — refine if under 7

        return iteration < 2  # Default: refine at least twice


# ═══════════════════════════════════════════════════════════════════
# NEW v10: Meta-Cognitive Strategy
# ═══════════════════════════════════════════════════════════════════

class MetaCognitiveStrategy:
    """
    Meta-Cognitive reasoning: think about how to think.

    Steps:
    1. Analyze the task type and what kind of thinking it requires
    2. Plan the reasoning approach
    3. Execute the planned approach
    4. Evaluate the quality of reasoning
    """

    def build_prompt(self, user_text: str, context: str = "") -> str:
        is_persian = _is_persian(user_text)

        if is_persian:
            return (
                f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                f"وظیفه: {user_text}\n\n"
                "قبل از پاسخ دادن، ابتدا فکر کن:\n\n"
                "۱. تحلیل وظیفه: این سوال از چه نوعی است؟ چه مهارت‌هایی نیاز دارد?\n"
                "۲. انتخاب رویکرد: بهترین روش فکر کردن درباره این مسئله چیست?\n"
                "۳. اجرا: حالا با رویکرد انتخاب‌شده پاسخ بده.\n"
                "۴. بازبینی: آیا پاسخم کامل و دقیق است?\n\n"
                "شروع کن:\n"
            )

        return (
            f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
            f"Task: {user_text}\n\n"
            "Before answering, think meta-cognitively:\n\n"
            "1. TASK ANALYSIS: What type of question is this? What skills does it require?\n"
            "2. APPROACH SELECTION: What's the best way to think about this problem?\n"
            "3. EXECUTION: Now apply your chosen approach to answer.\n"
            "4. SELF-CHECK: Is my answer complete, accurate, and well-reasoned?\n\n"
            "Begin:\n"
        )


# ═══════════════════════════════════════════════════════════════════
# NEW v10: Decompose-Delegate-Compose Strategy
# ═══════════════════════════════════════════════════════════════════

class DecomposeStrategy:
    """
    For complex multi-part tasks:
    1. Decompose into sub-tasks
    2. Solve each sub-task
    3. Compose the final answer
    """

    def build_decompose_prompt(self, user_text: str, context: str = "") -> str:
        is_persian = _is_persian(user_text)

        if is_persian:
            return (
                f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                f"وظیفه پیچیده: {user_text}\n\n"
                "این وظیفه رو به زیر‌وظایف مستقل تقسیم کن.\n"
                "برای هر زیر‌وظیفه مشخص کن:\n"
                "- شماره و عنوان\n"
                "- ورودی مورد نیاز\n"
                "- خروجی مورد انتظار\n"
                "- وابستگی به زیر‌وظایف دیگر\n\n"
                "زیر‌وظایف:\n"
            )

        return (
            f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
            f"Complex task: {user_text}\n\n"
            "Decompose this into independent sub-tasks.\n"
            "For each sub-task specify:\n"
            "- Number and title\n"
            "- Required input\n"
            "- Expected output\n"
            "- Dependencies on other sub-tasks\n\n"
            "Sub-tasks:\n"
        )

    def build_compose_prompt(self, user_text: str, sub_results: List[str]) -> str:
        is_persian = _is_persian(user_text)
        results_text = "\n\n".join(
            f"{'نتیجه' if is_persian else 'Result'} {i+1}:\n{r}"
            for i, r in enumerate(sub_results)
        )

        if is_persian:
            return (
                f"وظیفه اصلی: {user_text}\n\n"
                f"نتایج زیر‌وظایف:\n{results_text}\n\n"
                "حالا این نتایج رو ترکیب کن و یک پاسخ جامع و یکپارچه ارائه بده:\n"
            )

        return (
            f"Original task: {user_text}\n\n"
            f"Sub-task results:\n{results_text}\n\n"
            "Now compose these results into one comprehensive, coherent answer:\n"
        )


# ═══════════════════════════════════════════════════════════════════
# Reasoning Engine (Main Coordinator) — Enhanced v10
# ═══════════════════════════════════════════════════════════════════

class ReasoningEngine:
    """
    Main reasoning engine v10 that coordinates all strategies.

    This is what makes Arki THINK, not just respond.

    v10 enhancements:
    - Auto-selects optimal strategy based on task analysis
    - Supports strategy escalation (if initial strategy fails)
    - Persian/Farsi native support
    - Confidence-based quality gating
    """

    def __init__(self) -> None:
        self.cot = ChainOfThoughtStrategy()
        self.react = ReActStrategy()
        self.tot = TreeOfThoughtStrategy()
        self.self_refine = SelfRefineStrategy()
        self.meta_cog = MetaCognitiveStrategy()
        self.decompose = DecomposeStrategy()
        # v10: Track strategy effectiveness
        self._strategy_scores: Dict[str, List[float]] = {}

    def auto_select_strategy(
        self,
        user_text: str,
        category: str = "chat",
        complexity: int = 1,
    ) -> str:
        """
        v10: Intelligently select the best reasoning strategy.

        Uses task characteristics, not just complexity level.
        """
        text_lower = user_text.lower()
        word_count = len(user_text.split())

        # Multi-part tasks → Decompose
        multi_part_signals = [
            "و همچنین", "علاوه بر", "سپس", "بعد از آن",
            "and also", "additionally", "then", "after that",
            bool(re.search(r"\d+\.\s", user_text)),  # numbered list
        ]
        if sum(1 for s in multi_part_signals if (isinstance(s, bool) and s) or (isinstance(s, str) and s in text_lower)) >= 2:
            return "decompose"

        # Tool-requiring tasks → ReAct
        tool_signals = [
            "search", "جستجو", "calculate", "محاسبه",
            "scan", "اسکن", "workflow", "encrypt", "رمز",
        ]
        if any(s in text_lower for s in tool_signals):
            return "react"

        # Expert-level complexity → ToT
        if complexity >= 5 or word_count > 100:
            return "tree_of_thought"

        # Complex tasks → Meta-cognitive
        if complexity >= 4:
            return "meta_cognitive"

        # Moderate tasks → CoT
        if complexity >= 3 or word_count > 30:
            return "chain_of_thought"

        # Tasks requiring polish → Self-refine
        if category in ("creative", "sales", "content"):
            return "self_refine"

        # Simple → Direct
        return "direct"

    def get_strategy_prompt(
        self,
        strategy: str,
        user_text: str,
        context: str = "",
        tools: Optional[List[Tool]] = None,
    ) -> str:
        """Get the enhanced prompt for a given strategy."""
        if strategy in ("chain_of_thought", "cot"):
            return self.cot.build_prompt(user_text, context)
        elif strategy == "react":
            return self.react.build_initial_prompt(user_text, tools, context)
        elif strategy in ("tree_of_thought", "tot"):
            prompts = self.tot.build_branch_prompts(user_text, context)
            return prompts[0] if prompts else user_text
        elif strategy == "self_refine":
            return self.self_refine.build_initial_prompt(user_text, context)
        elif strategy == "meta_cognitive":
            return self.meta_cog.build_prompt(user_text, context)
        elif strategy == "decompose":
            return self.decompose.build_decompose_prompt(user_text, context)
        else:
            # Direct strategy — add a quality nudge
            if _is_persian(user_text):
                return (
                    f"{'زمینه: ' + context + chr(10) + chr(10) if context else ''}"
                    f"{user_text}\n\n"
                    "پاسخ دقیق، کامل و مفید ارائه بده."
                )
            return (
                f"{'Context: ' + context + chr(10) + chr(10) if context else ''}"
                f"{user_text}\n\n"
                "Provide an accurate, complete, and helpful response."
            )

    def get_escalation_strategy(self, current_strategy: str) -> Optional[str]:
        """v10: If current strategy produced low-quality output, escalate."""
        escalation_map = {
            "direct": "chain_of_thought",
            "chain_of_thought": "self_refine",
            "self_refine": "tree_of_thought",
            "react": "tree_of_thought",
            "meta_cognitive": "tree_of_thought",
            "tree_of_thought": None,  # Already top-level
            "decompose": "tree_of_thought",
        }
        return escalation_map.get(current_strategy)

    def record_strategy_outcome(self, strategy: str, quality: float) -> None:
        """v10: Track strategy effectiveness for adaptive selection."""
        if strategy not in self._strategy_scores:
            self._strategy_scores[strategy] = []
        self._strategy_scores[strategy].append(quality)
        # Keep last 100 scores
        if len(self._strategy_scores[strategy]) > 100:
            self._strategy_scores[strategy] = self._strategy_scores[strategy][-100:]

    def get_strategy_effectiveness(self) -> Dict[str, float]:
        """v10: Get average effectiveness of each strategy."""
        return {
            strategy: sum(scores) / len(scores)
            for strategy, scores in self._strategy_scores.items()
            if scores
        }

    def get_tool_definitions(self) -> List[Tool]:
        """Get all available tools for ReAct."""
        return AVAILABLE_TOOLS


# ═══════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════

def _is_persian(text: str) -> bool:
    """Detect if text is primarily Persian/Farsi."""
    if not text:
        return False
    persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\uFB50' <= c <= '\uFDFF')
    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return persian_chars > latin_chars


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Reasoning Engine
# ══════════════════════════════════════════════════════════════

class ChainOfThought:
    """Structured chain-of-thought reasoning for complex queries."""

    def __init__(self) -> None:
        self._chains: list[dict] = []

    def reason(self, question: str, facts: list[str]) -> dict:
        """Build a chain of thought from available facts."""
        steps = []
        
        # Step 1: Identify relevant facts
        relevant = [f for f in facts if any(
            w.lower() in f.lower() for w in question.split() if len(w) > 3
        )]
        steps.append({
            "step": "identify_relevant_facts",
            "input": question,
            "output": relevant,
        })
        
        # Step 2: Build logical chain
        chain = " → ".join(relevant[:5]) if relevant else "No relevant facts found"
        steps.append({
            "step": "build_chain",
            "output": chain,
        })
        
        # Step 3: Derive conclusion
        conclusion = f"Based on {len(relevant)} facts: {chain}"
        steps.append({
            "step": "conclude",
            "output": conclusion,
        })
        
        result = {
            "question": question,
            "steps": steps,
            "conclusion": conclusion,
            "confidence": min(len(relevant) / max(len(facts), 1), 1.0),
            "facts_used": len(relevant),
        }
        self._chains.append(result)
        return result


class ConfidenceScorer:
    """Score confidence of answers based on multiple factors."""

    @staticmethod
    def score(
        fact_coverage: float,
        source_count: int,
        recency_days: float = 0,
        contradiction_count: int = 0,
    ) -> dict:
        """Calculate confidence score 0-1."""
        base = fact_coverage * 0.4
        source_bonus = min(source_count / 5, 1.0) * 0.3
        recency_penalty = min(recency_days / 365, 1.0) * 0.1
        contradiction_penalty = min(contradiction_count / 3, 1.0) * 0.2
        
        score = base + source_bonus - recency_penalty - contradiction_penalty
        score = max(0.0, min(1.0, score))
        
        if score >= 0.8:
            label = "high"
        elif score >= 0.5:
            label = "medium"
        else:
            label = "low"
        
        return {
            "score": round(score, 3),
            "label": label,
            "factors": {
                "fact_coverage": round(fact_coverage, 3),
                "source_bonus": round(source_bonus, 3),
                "recency_penalty": round(recency_penalty, 3),
                "contradiction_penalty": round(contradiction_penalty, 3),
            },
        }


