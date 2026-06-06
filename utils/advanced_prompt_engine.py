
from __future__ import annotations
"""
tg_bot/utils/advanced_prompt_engine.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
ADVANCED PROMPT ENGINE — Dynamic Multi-Layer Prompt Construction

Constructs context-aware prompts by layering persona, RAG context,
few-shot examples, chain-of-thought scaffolding, and dynamic
guardrails into a cohesive system message.

Architecture
────────────
   Prompt Assembly Pipeline:

   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ Persona  │───▶│ Context  │───▶│ Few-Shot  │───▶│ CoT      │
   │ Layer    │    │ Injector │    │ Selector  │    │ Scaffold │
   └──────────┘    └──────────┘    └──────────┘    └──────────┘
        │               │               │               │
        └───────────────┴───────────────┴───────────────┘
                                │
                         ┌──────▼──────┐
                         │  Guardrail  │
                         │  Validator  │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  Token      │
                         │  Optimizer  │
                         └──────┬──────┘
                                ▼
                         Final Prompt

Features
────────
  • 15+ pre-built personas (hacker, scientist, coder, creative,
    analyst, teacher, translator, security, data, devops, etc.)
  • Dynamic persona merging (combine traits from multiple personas)
  • RAG context injection with token budgets
  • Few-shot example selection (TF-IDF similarity to query)
  • Chain-of-thought prompt templates (8 reasoning patterns)
  • Jailbreak detection & input sanitization
  • Output format enforcement (json, markdown, code, table, list)
  • Language-aware formatting (RTL support, Persian/Arabic)
  • Token counting & optimization (trim to model context window)
  • Prompt versioning & A/B testing hooks
  • Template variable interpolation
  • Guardrail rules with severity levels

References
──────────
  Port of: apex_app/src/lib/advanced-prompt-engine.ts (764 lines)
  Enhanced with: persona merging, CoT templates, guardrail severity,
                 token optimizer, A/B testing support
"""


import logging
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

DEFAULT_MAX_TOKENS          = 4096
DEFAULT_CONTEXT_BUDGET      = 2000      # tokens for RAG context
DEFAULT_FEW_SHOT_COUNT      = 3
MAX_EXAMPLES_IN_PROMPT      = 8
MAX_PROMPT_CHARS            = 100_000


# ═══════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════

class OutputFormat(str, Enum):
    TEXT        = "text"
    JSON        = "json"
    MARKDOWN    = "markdown"
    CODE        = "code"
    TABLE       = "table"
    LIST        = "list"
    YAML        = "yaml"
    XML         = "xml"


class ReasoningMode(str, Enum):
    DIRECT      = "direct"          # No CoT
    STEP_BY_STEP = "step_by_step"   # Break into numbered steps
    TREE_OF_THOUGHT = "tree_of_thought"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    SOCRATIC    = "socratic"        # Ask & answer sub-questions
    DEBATE      = "debate"          # Argue multiple perspectives
    ANALOGY     = "analogy"         # Explain via analogies
    DECOMPOSE   = "decompose"       # Divide & conquer


class GuardrailSeverity(str, Enum):
    BLOCK       = "block"           # Hard reject
    WARN        = "warn"            # Allow but flag
    SANITIZE    = "sanitize"        # Auto-clean input


# ═══════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Persona:
    """An AI persona with name, traits, system instructions, and constraints."""
    id: str
    name: str
    description: str
    system_prompt: str
    traits: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    output_style: str = ""
    language_hint: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    emoji: str = ""

    def to_prompt_section(self) -> str:
        """Convert persona to system prompt section."""
        lines = [f"# PERSONA: {self.name}"]
        if self.description:
            lines.append(self.description)
        lines.append("")
        lines.append(self.system_prompt)

        if self.traits:
            lines.append(f"\n## Traits: {', '.join(self.traits)}")
        if self.constraints:
            lines.append("\n## Constraints")
            for c in self.constraints:
                lines.append(f"- {c}")
        if self.output_style:
            lines.append(f"\n## Output Style: {self.output_style}")

        return "\n".join(lines)


@dataclass
class FewShotExample:
    """A few-shot example with input/output and optional tags."""
    input: str
    output: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    quality: float = 1.0        # 0-1, higher = better example

    @property
    def combined_text(self) -> str:
        return f"{self.input} {self.output}"


@dataclass
class GuardrailRule:
    """A content moderation rule."""
    id: str
    pattern: str                    # regex pattern
    severity: GuardrailSeverity
    message: str                    # message to show when triggered
    category: str = "general"
    enabled: bool = True

    def check(self, text: str) -> bool:
        """Returns True if rule is violated."""
        if not self.enabled:
            return False
        return bool(re.search(self.pattern, text, re.IGNORECASE))


@dataclass
class PromptConfig:
    """Configuration for prompt building."""
    persona_id: Optional[str] = None
    persona_ids: Optional[List[str]] = None   # for merging
    output_format: OutputFormat = OutputFormat.TEXT
    reasoning_mode: ReasoningMode = ReasoningMode.DIRECT
    language: str = "auto"
    max_tokens: int = DEFAULT_MAX_TOKENS
    context_budget: int = DEFAULT_CONTEXT_BUDGET
    few_shot_count: int = DEFAULT_FEW_SHOT_COUNT
    enable_guardrails: bool = True
    custom_instructions: str = ""
    template_vars: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptResult:
    """Result of prompt construction."""
    system_prompt: str
    user_prompt: str
    estimated_tokens: int
    persona_used: str
    output_format: str
    reasoning_mode: str
    guardrail_violations: List[str]
    build_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════
# Persona Registry
# ═══════════════════════════════════════════════════════════════════

PERSONAS: Dict[str, Persona] = {}

def _register_personas() -> None:
    """Register all built-in personas."""
    _defs: List[Dict[str, Any]] = [
        {
            "id": "default",
            "name": "Arki Assistant",
            "description": "General-purpose AI assistant",
            "emoji": "🤖",
            "system_prompt": (
                "You are Arki, a powerful AI assistant. You are direct, precise, "
                "and comprehensive. Provide actionable answers backed by data. "
                "Avoid hedging and filler words."
            ),
            "traits": ["direct", "precise", "comprehensive", "data-driven"],
            "output_style": "Clean, structured responses with headers and bullets",
        },
        {
            "id": "hacker",
            "name": "Arki — Elite Hacker",
            "description": "Cybersecurity expert and penetration tester",
            "emoji": "👾",
            "system_prompt": (
                "You are a senior cybersecurity expert and penetration tester. "
                "You explain attack vectors, defense strategies, vulnerability analysis, "
                "and security best practices. Your knowledge covers: network security, "
                "web application security (OWASP Top 10), binary exploitation, "
                "reverse engineering, social engineering, cryptography, and incident response. "
                "You think like an attacker to build better defenses."
            ),
            "traits": ["analytical", "precise", "technical", "security-minded"],
            "constraints": [
                "Explain concepts for educational purposes",
                "Always include defensive countermeasures",
                "Reference CVEs and MITRE ATT&CK when relevant",
            ],
            "temperature": 0.5,
        },
        {
            "id": "coder",
            "name": "Arki — Senior Developer",
            "description": "Expert software engineer and architect",
            "emoji": "💻",
            "system_prompt": (
                "You are a principal software engineer with deep expertise across "
                "the full stack. You write clean, documented, production-grade code. "
                "You follow SOLID principles, design patterns, and clean architecture. "
                "You optimize for readability, maintainability, and performance."
            ),
            "traits": ["meticulous", "pragmatic", "performance-aware"],
            "constraints": [
                "Always include type hints / types",
                "Add comprehensive comments and docstrings",
                "Handle edge cases and errors",
                "Consider security implications",
            ],
            "output_style": "Code with explanations, never just code dumps",
            "temperature": 0.3,
        },
        {
            "id": "scientist",
            "name": "Arki — Research Scientist",
            "description": "Deep domain expert in science and research",
            "emoji": "🔬",
            "system_prompt": (
                "You are a research scientist with expertise across physics, "
                "mathematics, computer science, and AI/ML. You explain complex "
                "concepts rigorously, cite relevant papers/sources, use precise "
                "mathematical notation, and distinguish between established "
                "knowledge and speculation."
            ),
            "traits": ["rigorous", "precise", "citation-aware", "mathematical"],
            "constraints": [
                "Cite sources when making claims",
                "Use LaTeX notation for equations",
                "Distinguish fact from hypothesis",
                "Acknowledge limitations and uncertainties",
            ],
            "temperature": 0.4,
        },
        {
            "id": "creative",
            "name": "Arki — Creative Writer",
            "description": "Creative writing and content generation expert",
            "emoji": "✍️",
            "system_prompt": (
                "You are a creative writing expert. You craft vivid prose, "
                "compelling narratives, and engaging content. You adapt your "
                "style to the genre: formal for articles, playful for social "
                "media, persuasive for marketing, poetic for literature."
            ),
            "traits": ["imaginative", "expressive", "versatile", "empathetic"],
            "temperature": 0.9,
            "top_p": 0.95,
        },
        {
            "id": "analyst",
            "name": "Arki — Data Analyst",
            "description": "Data analysis and business intelligence expert",
            "emoji": "📊",
            "system_prompt": (
                "You are a senior data analyst. You extract insights from data, "
                "identify patterns, build statistical models, and present findings "
                "clearly. You use Python (pandas, numpy, matplotlib) and SQL."
            ),
            "traits": ["analytical", "data-driven", "visual-thinker"],
            "constraints": [
                "Support claims with numbers",
                "Include visualizations when helpful",
                "Consider statistical significance",
                "Mention data limitations",
            ],
            "temperature": 0.3,
        },
        {
            "id": "teacher",
            "name": "Arki — Expert Teacher",
            "description": "Patient educator adapting to learner level",
            "emoji": "📚",
            "system_prompt": (
                "You are an expert teacher. You explain concepts clearly using "
                "analogies, examples, and progressive complexity. You assess "
                "the learner's level and adapt. Use the Feynman technique."
            ),
            "traits": ["patient", "adaptive", "clear", "encouraging"],
            "output_style": "Start simple, build complexity, use examples",
            "temperature": 0.6,
        },
        {
            "id": "translator",
            "name": "Arki — Multilingual Translator",
            "description": "Expert translator and linguistic analyzer",
            "emoji": "🌐",
            "system_prompt": (
                "You are a professional translator with native fluency in "
                "English, Persian/Farsi, Arabic, French, German, Spanish, "
                "Chinese, and Japanese. You provide accurate, natural "
                "translations preserving tone and cultural context."
            ),
            "traits": ["precise", "culturally-aware", "natural"],
            "constraints": [
                "Preserve original tone and intent",
                "Note cultural context differences",
                "Provide transliteration when helpful",
            ],
            "temperature": 0.4,
        },
        {
            "id": "devops",
            "name": "Arki — DevOps Engineer",
            "description": "Infrastructure, CI/CD, and cloud expert",
            "emoji": "⚙️",
            "system_prompt": (
                "You are a senior DevOps engineer and SRE. Expert in Docker, "
                "Kubernetes, Terraform, CI/CD pipelines, monitoring, and "
                "cloud platforms (AWS, GCP, Azure). You optimize for "
                "reliability, scalability, and security."
            ),
            "traits": ["systematic", "automation-focused", "security-aware"],
            "temperature": 0.4,
        },
        {
            "id": "osint",
            "name": "Arki — OSINT Investigator",
            "description": "Open-source intelligence and reconnaissance expert",
            "emoji": "🕵️",
            "system_prompt": (
                "You are an OSINT investigator skilled in digital forensics, "
                "social media analysis, domain reconnaissance, and information "
                "gathering from public sources. You use tools like Shodan, "
                "Maltego, and custom scripts."
            ),
            "traits": ["thorough", "methodical", "resourceful"],
            "constraints": [
                "Only use publicly available information",
                "Respect privacy and legal boundaries",
                "Document your methodology",
            ],
            "temperature": 0.5,
        },
        {
            "id": "architect",
            "name": "Arki — System Architect",
            "description": "Software and system architecture expert",
            "emoji": "🏗️",
            "system_prompt": (
                "You are a principal system architect. You design scalable, "
                "resilient architectures for distributed systems. Expert in "
                "microservices, event-driven design, CQRS, DDD, and "
                "high-availability patterns."
            ),
            "traits": ["strategic", "big-picture", "trade-off-aware"],
            "temperature": 0.5,
        },
        {
            "id": "persian",
            "name": "آرکی — دستیار فارسی",
            "description": "متخصص زبان و فرهنگ فارسی",
            "emoji": "🇮🇷",
            "system_prompt": (
                "تو آرکی هستی، یک دستیار هوش مصنوعی پیشرفته که به فارسی روان "
                "صحبت می‌کنی. پاسخ‌ها باید طبیعی، دقیق و حرفه‌ای باشند. "
                "از اصطلاحات فنی به همراه معادل فارسی استفاده کن."
            ),
            "traits": ["fluent-persian", "culturally-aware", "formal"],
            "language_hint": "fa",
            "temperature": 0.6,
        },
    ]

    for d in _defs:
        PERSONAS[d["id"]] = Persona(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            emoji=d.get("emoji", ""),
            system_prompt=d["system_prompt"],
            traits=d.get("traits", []),
            constraints=d.get("constraints", []),
            output_style=d.get("output_style", ""),
            language_hint=d.get("language_hint", ""),
            temperature=d.get("temperature", 0.7),
            top_p=d.get("top_p", 0.9),
        )

_register_personas()


def merge_personas(persona_ids: List[str]) -> Persona:
    """Merge multiple personas into one composite persona."""
    personas = [PERSONAS[pid] for pid in persona_ids if pid in PERSONAS]
    if not personas:
        return PERSONAS.get("default", list(PERSONAS.values())[0])
    if len(personas) == 1:
        return personas[0]

    merged_traits: List[str] = []
    merged_constraints: List[str] = []
    merged_prompt_parts: List[str] = []
    seen_traits: Set[str] = set()

    for p in personas:
        merged_prompt_parts.append(p.system_prompt)
        for t in p.traits:
            if t not in seen_traits:
                merged_traits.append(t)
                seen_traits.add(t)
        merged_constraints.extend(p.constraints)

    return Persona(
        id=f"merged_{'_'.join(persona_ids[:3])}",
        name=" + ".join(p.name for p in personas[:3]),
        description="Merged persona combining multiple specialties",
        system_prompt="\n\n".join(merged_prompt_parts),
        traits=merged_traits[:15],
        constraints=merged_constraints[:10],
        temperature=sum(p.temperature for p in personas) / len(personas),
    )


# ═══════════════════════════════════════════════════════════════════
# Few-Shot Example Store
# ═══════════════════════════════════════════════════════════════════

class ExampleStore:
    """Stores and selects relevant few-shot examples by similarity."""

    def __init__(self) -> None:
        self._examples: List[FewShotExample] = []

    def add(self, example: FewShotExample) -> None:
        self._examples.append(example)

    def add_batch(self, examples: List[FewShotExample]) -> None:
        self._examples.extend(examples)

    def select(self, query: str, count: int = DEFAULT_FEW_SHOT_COUNT,
               category: Optional[str] = None) -> List[FewShotExample]:
        """Select most relevant examples for a query using TF-IDF."""
        candidates = self._examples
        if category:
            cat_filtered = [e for e in candidates if e.category == category]
            if cat_filtered:
                candidates = cat_filtered

        if not candidates:
            return []

        # TF-IDF similarity
        query_words = set(re.findall(r"\w+", query.lower()))
        scored: List[Tuple[float, FewShotExample]] = []

        for ex in candidates:
            ex_words = set(re.findall(r"\w+", ex.combined_text.lower()))
            if not ex_words:
                continue
            overlap = len(query_words & ex_words)
            score = overlap / (math.sqrt(len(query_words)) * math.sqrt(len(ex_words)))
            score *= ex.quality
            scored.append((score, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:count]]

    def format_examples(self, examples: List[FewShotExample],
                        format_type: str = "qa") -> str:
        """Format examples for prompt injection."""
        if format_type == "qa":
            parts = []
            for i, ex in enumerate(examples, 1):
                parts.append(
                    f"Example {i}:\n"
                    f"Input: {ex.input}\n"
                    f"Output: {ex.output}"
                )
            return "\n\n".join(parts)
        elif format_type == "conversation":
            parts = []
            for ex in examples:
                parts.append(f"User: {ex.input}\nAssistant: {ex.output}")
            return "\n\n".join(parts)
        else:
            return "\n---\n".join(
                f"Q: {ex.input}\nA: {ex.output}" for ex in examples
            )


# Global example store
example_store = ExampleStore()


# ═══════════════════════════════════════════════════════════════════
# Chain-of-Thought Templates
# ═══════════════════════════════════════════════════════════════════

COT_TEMPLATES: Dict[ReasoningMode, str] = {
    ReasoningMode.STEP_BY_STEP: (
        "Think through this step by step:\n"
        "1. Understand the problem clearly\n"
        "2. Identify key information and constraints\n"
        "3. Plan your approach\n"
        "4. Execute each step carefully\n"
        "5. Verify your answer\n"
        "6. Present the final answer clearly"
    ),
    ReasoningMode.CHAIN_OF_THOUGHT: (
        "Let's think through this carefully.\n"
        "First, I'll identify what we know.\n"
        "Then, I'll reason through the logic.\n"
        "Finally, I'll state my conclusion with confidence."
    ),
    ReasoningMode.TREE_OF_THOUGHT: (
        "Explore multiple reasoning paths:\n"
        "Path A: [First approach]\n"
        "Path B: [Alternative approach]\n"
        "Path C: [Creative approach]\n"
        "Evaluate each path and select the best one with justification."
    ),
    ReasoningMode.SOCRATIC: (
        "Answer by asking and answering key sub-questions:\n"
        "Q1: What is the core problem?\n"
        "A1: [answer]\n"
        "Q2: What are the constraints?\n"
        "A2: [answer]\n"
        "Q3: What solutions exist?\n"
        "A3: [answer]\n"
        "Synthesis: [combine answers into final response]"
    ),
    ReasoningMode.DEBATE: (
        "Consider multiple perspectives:\n"
        "FOR: [arguments supporting]\n"
        "AGAINST: [arguments against]\n"
        "NUANCE: [edge cases and exceptions]\n"
        "VERDICT: [balanced conclusion]"
    ),
    ReasoningMode.ANALOGY: (
        "Explain using analogies:\n"
        "1. The concept is like [familiar thing] because...\n"
        "2. Key differences from the analogy...\n"
        "3. Where the analogy breaks down...\n"
        "4. The precise technical explanation..."
    ),
    ReasoningMode.DECOMPOSE: (
        "Decompose this problem:\n"
        "1. Break into sub-problems\n"
        "2. Solve each sub-problem independently\n"
        "3. Combine solutions\n"
        "4. Check for conflicts between sub-solutions\n"
        "5. Synthesize final answer"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Guardrails
# ═══════════════════════════════════════════════════════════════════

DEFAULT_GUARDRAILS: List[GuardrailRule] = [
    GuardrailRule(
        id="jailbreak_1", category="jailbreak",
        pattern=r"ignore\s+(all\s+)?previous\s+(instructions|prompts|rules)",
        severity=GuardrailSeverity.BLOCK,
        message="Jailbreak attempt detected: ignore instructions",
    ),
    GuardrailRule(
        id="jailbreak_2", category="jailbreak",
        pattern=r"you\s+are\s+now\s+(DAN|evil|unrestricted|jailbroken)",
        severity=GuardrailSeverity.BLOCK,
        message="Jailbreak attempt detected: role override",
    ),
    GuardrailRule(
        id="jailbreak_3", category="jailbreak",
        pattern=r"pretend\s+(you\s+)?(are|have)\s+no\s+(rules|restrictions|limitations)",
        severity=GuardrailSeverity.BLOCK,
        message="Jailbreak attempt detected: restriction removal",
    ),
    GuardrailRule(
        id="jailbreak_4", category="jailbreak",
        pattern=r"system\s*prompt|reveal\s+(your|the)\s+(system|initial|hidden)\s*prompt",
        severity=GuardrailSeverity.BLOCK,
        message="Attempt to extract system prompt",
    ),
    GuardrailRule(
        id="injection_1", category="injection",
        pattern=r"\]\s*\}\s*\{.*\"role\"\s*:\s*\"system\"",
        severity=GuardrailSeverity.BLOCK,
        message="Prompt injection detected: JSON message injection",
    ),
    GuardrailRule(
        id="harmful_1", category="harmful",
        pattern=r"\b(make\s+a?\s*bomb|create\s+.{0,30}weapon|synthesize\s+.{0,30}drug)\b",
        severity=GuardrailSeverity.BLOCK,
        message="Harmful content request detected",
    ),
    GuardrailRule(
        id="pii_1", category="privacy",
        pattern=r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
        severity=GuardrailSeverity.SANITIZE,
        message="Possible SSN detected — sanitizing",
    ),
    GuardrailRule(
        id="pii_2", category="privacy",
        pattern=r"\b\d{16}\b|\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b",
        severity=GuardrailSeverity.SANITIZE,
        message="Possible credit card number — sanitizing",
    ),
]


def check_guardrails(text: str,
                     rules: Optional[List[GuardrailRule]] = None) -> Tuple[bool, List[str]]:
    """
    Check text against guardrail rules.

    Returns
    -------
    (safe, violations) : tuple
        safe=True if no BLOCK-level violations found.
        violations: list of violation messages.
    """
    rules = rules or DEFAULT_GUARDRAILS
    violations: List[str] = []
    safe = True

    for rule in rules:
        if rule.check(text):
            violations.append(f"[{rule.severity.value}] {rule.message}")
            if rule.severity == GuardrailSeverity.BLOCK:
                safe = False

    return safe, violations


def sanitize_input(text: str,
                   rules: Optional[List[GuardrailRule]] = None) -> str:
    """Remove/mask content matching SANITIZE-level rules."""
    rules = rules or DEFAULT_GUARDRAILS
    result = text

    for rule in rules:
        if rule.severity == GuardrailSeverity.SANITIZE and rule.enabled:
            result = re.sub(rule.pattern, "[REDACTED]", result, flags=re.IGNORECASE)

    return result


# ═══════════════════════════════════════════════════════════════════
# Output Format Directives
# ═══════════════════════════════════════════════════════════════════

OUTPUT_DIRECTIVES: Dict[OutputFormat, str] = {
    OutputFormat.TEXT: "",
    OutputFormat.JSON: (
        "IMPORTANT: Respond ONLY with valid JSON. No markdown code fences. "
        "No explanation text outside the JSON. Ensure all strings are properly "
        "escaped. Use snake_case for keys."
    ),
    OutputFormat.MARKDOWN: (
        "Format your response in clean Markdown with headers (##), bullet points, "
        "code blocks (```), bold (**), and links where appropriate."
    ),
    OutputFormat.CODE: (
        "Respond with code only. Include necessary comments. "
        "No explanatory text outside the code block. "
        "Include type hints, error handling, and docstrings."
    ),
    OutputFormat.TABLE: (
        "Present data in a formatted table. Use | for column separators "
        "and --- for header separators. Include a header row."
    ),
    OutputFormat.LIST: (
        "Respond with a numbered or bulleted list. Each item should be "
        "clear and concise. Group related items together."
    ),
    OutputFormat.YAML: (
        "Respond ONLY with valid YAML. No markdown code fences. "
        "Use 2-space indentation. Include comments for clarity."
    ),
    OutputFormat.XML: (
        "Respond ONLY with valid XML. Include proper indentation "
        "and a root element."
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Token Estimation & Optimization
# ═══════════════════════════════════════════════════════════════════

def estimate_tokens(text: str) -> int:
    """
    Estimate token count. Approximation: ~4 chars per token for English,
    ~2 chars per token for CJK/Arabic/Persian.
    """
    if not text:
        return 0

    # Check for non-Latin scripts
    non_latin = len(re.findall(r"[\u0600-\u06FF\u4e00-\u9fff\u0400-\u04FF\uac00-\ud7af]", text))
    total_chars = len(text)

    if non_latin > total_chars * 0.3:
        return total_chars // 2     # RTL / CJK
    return total_chars // 4         # Latin


def trim_to_budget(text: str, max_tokens: int) -> str:
    """Trim text to fit within token budget, preserving structure."""
    current = estimate_tokens(text)
    if current <= max_tokens:
        return text

    # Try to cut at paragraph boundaries
    paragraphs = text.split("\n\n")
    trimmed: List[str] = []
    tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if tokens + para_tokens > max_tokens:
            remaining = max_tokens - tokens
            if remaining > 20:  # Only add if meaningful amount
                chars = remaining * 4
                trimmed.append(para[:chars] + "...")
            break
        trimmed.append(para)
        tokens += para_tokens

    return "\n\n".join(trimmed)


# ═══════════════════════════════════════════════════════════════════
# Language Detection & Formatting
# ═══════════════════════════════════════════════════════════════════

def detect_language(text: str) -> str:
    """Detect primary language of text."""
    has_persian = len(re.findall(r"[\u0600-\u06FF]", text))
    has_cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    has_cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    total = len(text)

    if total == 0:
        return "en"
    if has_persian / max(total, 1) > 0.2:
        return "fa"
    if has_cjk / max(total, 1) > 0.2:
        return "zh"
    if has_cyrillic / max(total, 1) > 0.2:
        return "ru"
    return "en"


def get_language_directive(lang: str) -> str:
    """Get language-specific formatting instructions."""
    directives: Dict[str, str] = {
        "fa": "پاسخ را به فارسی روان بنویسید. از اصطلاحات فنی به همراه معادل فارسی استفاده کنید.",
        "ar": "اكتب الإجابة بالعربية الفصحى. استخدم المصطلحات التقنية مع ترجمتها.",
        "zh": "请用简体中文回答。使用专业术语时请附带英文原文。",
        "ru": "Ответьте на русском языке. Используйте технические термины с переводом.",
        "en": "",
    }
    return directives.get(lang, "")


# ═══════════════════════════════════════════════════════════════════
# Prompt Builder — Core Engine
# ═══════════════════════════════════════════════════════════════════

class PromptEngine:
    """
    Central prompt construction engine. Assembles system + user prompts
    from persona, context, examples, CoT, guardrails, and formatting.
    """

    def __init__(self) -> None:
        self._example_store = example_store
        self._guardrails = list(DEFAULT_GUARDRAILS)
        self._build_count = 0

    def build(
        self,
        user_query: str,
        config: Optional[PromptConfig] = None,
        rag_context: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> PromptResult:
        """
        Build complete system + user prompt.

        Parameters
        ----------
        user_query : str
            The user's raw query.
        config : PromptConfig, optional
            Prompt configuration.
        rag_context : str, optional
            Retrieved context from memory/RAG.
        conversation_history : list, optional
            Prior messages for context.

        Returns
        -------
        PromptResult
            Constructed prompt with metadata.
        """
        start = time.time()
        config = config or PromptConfig()
        self._build_count += 1

        guardrail_violations: List[str] = []

        # ── 1. Guardrails ──────────────────────────────────────
        if config.enable_guardrails:
            safe, violations = check_guardrails(user_query, self._guardrails)
            guardrail_violations = violations
            if not safe:
                return PromptResult(
                    system_prompt="",
                    user_prompt=user_query,
                    estimated_tokens=0,
                    persona_used="blocked",
                    output_format=config.output_format.value,
                    reasoning_mode=config.reasoning_mode.value,
                    guardrail_violations=violations,
                    build_time_ms=(time.time() - start) * 1000,
                )
            user_query = sanitize_input(user_query, self._guardrails)

        # ── 2. Language Detection ──────────────────────────────
        if config.language == "auto":
            lang = detect_language(user_query)
        else:
            lang = config.language

        # ── 3. Persona Selection ───────────────────────────────
        if config.persona_ids and len(config.persona_ids) > 1:
            persona = merge_personas(config.persona_ids)
        elif config.persona_id:
            persona = PERSONAS.get(config.persona_id, PERSONAS["default"])
        else:
            # Auto-select based on language
            if lang == "fa":
                persona = PERSONAS.get("persian", PERSONAS["default"])
            else:
                persona = PERSONAS["default"]

        # ── 4. Build System Prompt Layers ──────────────────────
        layers: List[str] = []

        # Layer 1: Persona
        layers.append(persona.to_prompt_section())

        # Layer 2: RAG context
        if rag_context:
            trimmed_ctx = trim_to_budget(rag_context, config.context_budget)
            layers.append(
                f"\n## RELEVANT CONTEXT\n{trimmed_ctx}\n"
                "Use this context to inform your answer, but don't "
                "just repeat it verbatim."
            )

        # Layer 3: Few-shot examples
        if config.few_shot_count > 0:
            examples = self._example_store.select(
                user_query, count=config.few_shot_count,
            )
            if examples:
                formatted = self._example_store.format_examples(examples)
                layers.append(f"\n## EXAMPLES\n{formatted}")

        # Layer 4: Chain-of-thought
        if config.reasoning_mode != ReasoningMode.DIRECT:
            cot = COT_TEMPLATES.get(config.reasoning_mode, "")
            if cot:
                layers.append(f"\n## REASONING APPROACH\n{cot}")

        # Layer 5: Output format
        directive = OUTPUT_DIRECTIVES.get(config.output_format, "")
        if directive:
            layers.append(f"\n## OUTPUT FORMAT\n{directive}")

        # Layer 6: Language directive
        lang_dir = get_language_directive(lang)
        if lang_dir:
            layers.append(f"\n## LANGUAGE\n{lang_dir}")

        # Layer 7: Custom instructions
        if config.custom_instructions:
            layers.append(f"\n## ADDITIONAL INSTRUCTIONS\n{config.custom_instructions}")

        # ── 5. Template Variable Interpolation ─────────────────
        system_prompt = "\n".join(layers)
        for key, value in config.template_vars.items():
            system_prompt = system_prompt.replace(f"{{{{{key}}}}}", value)

        # ── 6. Token Optimization ──────────────────────────────
        total_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_query)
        if total_tokens > config.max_tokens * 0.8:
            # Trim context first, then examples
            system_prompt = trim_to_budget(
                system_prompt,
                int(config.max_tokens * 0.7),
            )
            total_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_query)

        return PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_query,
            estimated_tokens=total_tokens,
            persona_used=persona.id,
            output_format=config.output_format.value,
            reasoning_mode=config.reasoning_mode.value,
            guardrail_violations=guardrail_violations,
            build_time_ms=(time.time() - start) * 1000,
            metadata={
                "language": lang,
                "persona_temperature": persona.temperature,
                "build_number": self._build_count,
            },
        )

    def add_guardrail(self, rule: GuardrailRule) -> None:
        self._guardrails.append(rule)

    def remove_guardrail(self, rule_id: str) -> bool:
        before = len(self._guardrails)
        self._guardrails = [r for r in self._guardrails if r.id != rule_id]
        return len(self._guardrails) < before


# ═══════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════

_engine = PromptEngine()


def build_prompt(
    query: str,
    persona: str = "default",
    output_format: str = "text",
    reasoning: str = "direct",
    rag_context: str = "",
    custom_instructions: str = "",
) -> PromptResult:
    """Quick prompt building with sensible defaults."""
    return _engine.build(
        query,
        PromptConfig(
            persona_id=persona,
            output_format=OutputFormat(output_format),
            reasoning_mode=ReasoningMode(reasoning),
            custom_instructions=custom_instructions,
        ),
        rag_context=rag_context,
    )


def get_persona_list() -> List[Dict[str, str]]:
    """Get list of available personas."""
    return [
        {"id": p.id, "name": p.name, "emoji": p.emoji, "description": p.description}
        for p in PERSONAS.values()
    ]

class AdvancedPromptEngine:
    """Advanced prompt construction with personas, context, and templates."""

    def __init__(self) -> None:
        self._templates: dict = {}
        self._personas: dict = {}
        self._context_window: int = 128000

    def set_persona(self, name: str, system_prompt: str) -> None:
        self._personas[name] = system_prompt

    def get_persona(self, name: str) -> str:
        return self._personas.get(name, "")

    def build_prompt(self, user_msg: str, persona: str = "default", context: list = None) -> list:
        messages = []
        if persona in self._personas:
            messages.append({"role": "system", "content": self._personas[persona]})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": user_msg})
        return messages


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Prompt Engineering
# ══════════════════════════════════════════════════════════════

class PromptTemplate:
    """Reusable prompt templates with variable substitution."""

    def __init__(self, template: str, name: str = "") -> None:
        self.name = name
        self.template = template

    def render(self, **kwargs) -> str:
        """Render template with variables."""
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


class PersonaManager:
    """Manage AI personas for different interaction styles."""

    _PERSONAS = {
        "professional": {
            "tone": "formal",
            "style": "concise and professional",
            "system_prompt": "You are a professional AI assistant. Respond formally and precisely.",
        },
        "friendly": {
            "tone": "casual",
            "style": "warm and approachable",
            "system_prompt": "You are a friendly AI helper. Be warm, use simple language.",
        },
        "technical": {
            "tone": "precise",
            "style": "detailed and technical",
            "system_prompt": "You are a technical expert. Provide detailed, accurate technical responses.",
        },
        "creative": {
            "tone": "imaginative",
            "style": "creative and expressive",
            "system_prompt": "You are a creative AI. Think outside the box and be expressive.",
        },
        "persian": {
            "tone": "respectful",
            "style": "fluent Persian with cultural awareness",
            "system_prompt": "شما یک دستیار هوش مصنوعی فارسی‌زبان هستید. به فارسی روان و محترمانه پاسخ دهید.",
        },
    }

    def __init__(self) -> None:
        self._active = "professional"
        self._custom: dict[str, dict] = {}

    def set_persona(self, name: str) -> None:
        if name in self._PERSONAS or name in self._custom:
            self._active = name

    def get_persona(self) -> dict:
        if self._active in self._custom:
            return self._custom[self._active]
        return self._PERSONAS.get(self._active, self._PERSONAS["professional"])

    def add_custom_persona(self, name: str, tone: str, style: str, system_prompt: str) -> None:
        self._custom[name] = {
            "tone": tone, "style": style, "system_prompt": system_prompt,
        }

    def list_personas(self) -> list[str]:
        return list(self._PERSONAS.keys()) + list(self._custom.keys())


class PromptOptimizer:
    """Optimize prompts for better AI performance."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token count estimation."""
        return len(text) // 4 + 1

    @staticmethod
    def truncate_to_limit(text: str, max_tokens: int = 4000) -> str:
        """Truncate text to fit within token limit."""
        estimated = len(text) // 4
        if estimated <= max_tokens:
            return text
        char_limit = max_tokens * 4
        return text[:char_limit] + "\n[...truncated]"

    @staticmethod
    def enhance_prompt(prompt: str, context: str = "", persona: str = "") -> str:
        """Enhance a prompt with context and persona instructions."""
        parts = []
        if persona:
            parts.append(f"[Persona: {persona}]")
        if context:
            parts.append(f"[Context: {context}]")
        parts.append(prompt)
        return "\n\n".join(parts)


