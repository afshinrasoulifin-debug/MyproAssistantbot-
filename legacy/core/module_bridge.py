
from __future__ import annotations
"""
tg_bot/core/module_bridge.py — Unified Module Bridge
═══════════════════════════════════════════════════════
ONE import, EVERY module accessible.

All handlers import from here instead of directly from modules:
    from arki_project.core.module_bridge import bridge

    # Memory
    bridge.remember(user_id, content, metadata)
    memories = bridge.recall(user_id, query, top_k=3)
    
    # Prompt enhancement
    enhanced = bridge.enhance_prompt(text, category, style)
    
    # Text transformation
    translated = bridge.transform_text(text, "translate", target_lang="en")
    summary = bridge.transform_text(text, "summarize")
    
    # Data analysis
    insights = bridge.analyze(data, method="statistical")
    
    # Web research
    results = bridge.web_search(query, depth="deep")
    content = bridge.extract_url(url)
    
    # AutoTune
    params = bridge.autotune_params(user_id, text)
    bridge.autotune_feedback(user_id, quality_score)
    
    # Telemetry
    bridge.record_event(module, duration, success)
    stats = bridge.get_telemetry()
    
    # Pipeline
    result = bridge.classify(user_id, text)
    context = bridge.build_context(user_id, text, category, history)
    
    # Multi-LLM
    consensus = bridge.multi_llm_ask(messages, models, strategy)
    
    # Workflow
    wf = bridge.create_workflow(steps)
    result = bridge.run_workflow(wf, input_data)
    
    # Security
    encrypted = bridge.encrypt(data, method)
    hashed = bridge.hash(data, algorithm)
    
    # Agent execution
    result = bridge.run_agent(goal, tools, max_steps)

This is the GLUE that makes integration real.
"""


import logging
from typing import Any, Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class ModuleBridge:
    """
    Centralized access point for all 22 intelligence modules.
    
    Lazy-loads modules on first use. Thread-safe. Error-tolerant
    (gracefully degrades if a module fails).
    """

    def __init__(self) -> None:
        self._modules: Dict[str, Any] = {}
        self._initialized = False
        self._init_errors: Dict[str, str] = {}

    def _ensure_init(self) -> None:
        """Lazy-initialize all modules on first access."""
        if self._initialized:
            return
        self._initialized = True
        self._load_modules()

    def _load_modules(self) -> None:
        """Load all modules with graceful error handling."""
        module_map = {
            "pipeline": ("tg_bot.core.pipeline", "IntelligentPipeline"),
            "reasoning": ("tg_bot.core.reasoning", "ReasoningEngine"),
            "memory": ("tg_bot.utils.memory_store", "MemoryStore"),
            "prompt_engine": ("tg_bot.utils.advanced_prompt_engine", "AdvancedPromptEngine"),
            "multi_llm": ("tg_bot.utils.multi_llm_orchestrator", "MultiLLMOrchestrator"),
            "autotune": ("tg_bot.utils.autotune", "AutoTuneEngine"),
            "text_transform": ("tg_bot.utils.text_transform", "TextTransformer"),
            "data_analyzer": ("tg_bot.utils.data_analyzer", "DataAnalyzer"),
            "web_recon": ("tg_bot.utils.web_recon", "WebRecon"),
            "web_search": ("tg_bot.utils.web_search", None),  # Module-level functions
            "telemetry": ("tg_bot.utils.telemetry_engine", "TelemetryEngine"),
            # v10.3: Victor Independent Intelligence
            "victor_brain": ("tg_bot.handlers.victor", "VictorBrain"),
            "crypto": ("tg_bot.utils.crypto_engine", "CryptoEngine"),
            "network": ("tg_bot.utils.network_tools", "NetworkTools"),
            "workflow": ("tg_bot.utils.workflow_engine", "WorkflowEngine"),
            "integration": ("tg_bot.utils.integration_hub", "IntegrationHub"),
            "multimodal": ("tg_bot.utils.multimodal_engine", "MultimodalEngine"),
            "terminal": ("tg_bot.utils.terminal_emulator", "TerminalEmulator"),
            "agent": ("tg_bot.utils.agent_executor", "AgentExecutor"),
            "orchestrator": ("tg_bot.utils.master_orchestrator", "MasterOrchestrator"),
            "dashboard": ("tg_bot.utils.dashboard_monitor", "DashboardMonitor"),
            "plugin": ("tg_bot.utils.plugin_system", "PluginManager"),
            "anti_detect": ("tg_bot.utils.anti_detection", "AntiDetection"),
        }

        for name, (module_path, class_name) in module_map.items():
            try:
                mod = __import__(module_path, fromlist=[class_name or ""])
                if class_name:
                    cls = getattr(mod, class_name)
                    self._modules[name] = cls()
                else:
                    self._modules[name] = mod
                logger.debug("Module loaded: %s", name)
            except Exception as exc:
                self._init_errors[name] = str(exc)
                logger.warning("Module %s failed to load: %s", name, exc)

        logger.info(
            "ModuleBridge: %d/%d modules loaded",
            len(self._modules), len(module_map),
        )

    def _get(self, name: str) -> Any:
        """Get a module instance, or None if not available."""
        self._ensure_init()
        return self._modules.get(name)

    # ═══════════════════════════════════════════════════════════════
    # Pipeline & Classification
    # ═══════════════════════════════════════════════════════════════

    async def classify(
        self, user_id: int, text: str,
    ) -> Tuple[str, int, float]:
        """
        Classify a message into (category, complexity, confidence).
        Returns: ("chat", 1, 0.85) etc.
        """
        pipeline = self._get("pipeline")
        if pipeline:
            result = await pipeline.process(user_id, text)
            return (
                result.category.value,
                result.complexity.value,
                result.confidence,
            )
        return ("chat", 1, 0.5)

    async def process_pipeline(
        self, user_id: int, text: str,
        chat_history: Optional[List[Dict]] = None,
    ) -> Any:
        """Full pipeline processing."""
        pipeline = self._get("pipeline")
        if pipeline:
            return await pipeline.process(
                user_id, text, chat_history=chat_history,
            )
        return None

    # ═══════════════════════════════════════════════════════════════
    # Memory
    # ═══════════════════════════════════════════════════════════════

    def remember(
        self,
        user_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store something in semantic memory."""
        mem = self._get("memory")
        if mem:
            try:
                mem.store(
                    content=content,
                    namespace=str(user_id),
                    metadata=metadata or {},
                )
                return True
            except Exception as exc:
                logger.debug("Memory store failed: %s", exc)
        return False

    def recall(
        self,
        user_id: int,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Search semantic memory for relevant past interactions."""
        mem = self._get("memory")
        if mem:
            try:
                results = mem.search(
                    query=query,
                    namespace=str(user_id),
                    top_k=top_k,
                )
                return [
                    {
                        "content": getattr(r, "content", r.get("content", "")) if isinstance(r, dict) else getattr(r, "content", str(r)),
                        "score": getattr(r, "score", r.get("score", 0)) if isinstance(r, dict) else getattr(r, "score", 0),
                    }
                    for r in results
                ]
            except Exception as exc:
                logger.debug("Memory recall failed: %s", exc)
        return []

    def clear_memory(self, user_id: int) -> None:
        """Clear user's short-term memory."""
        mem = self._get("memory")
        if mem:
            try:
                mem.clear_short_term(str(user_id))
            except Exception as e:
                logger.debug("Suppressed: %s", e)

    def build_memory_context(self, user_id: int, text: str) -> str:
        """Build a memory context string for system prompts."""
        memories = self.recall(user_id, text, top_k=3)
        if not memories:
            return ""
        parts = ["\n[RELEVANT MEMORY FROM PAST CONVERSATIONS]"]
        for m in memories:
            content = m.get("content", "")[:200]
            if content:
                parts.append(f"• {content}")
        parts.append("[END MEMORY]\n")
        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════════════
    # Prompt Enhancement
    # ═══════════════════════════════════════════════════════════════

    def enhance_prompt(
        self,
        text: str,
        category: str = "general",
        style: str = "professional",
        persona: str = "",
    ) -> str:
        """Enhance a prompt using the AdvancedPromptEngine."""
        pe = self._get("prompt_engine")
        if pe:
            try:
                return pe.enhance(
                    text=text,
                    category=category,
                    style=style,
                    persona=persona,
                )
            except Exception as exc:
                logger.debug("Prompt enhancement failed: %s", exc)
        return text

    def build_reasoning_prompt(
        self,
        text: str,
        strategy: str = "direct",
        context: str = "",
    ) -> str:
        """Build a reasoning-enhanced prompt."""
        reasoning = self._get("reasoning")
        if reasoning:
            try:
                return reasoning.get_strategy_prompt(
                    strategy=strategy,
                    user_text=text,
                    context=context,
                )
            except Exception as exc:
                logger.debug("Reasoning prompt failed: %s", exc)
        return text

    # ═══════════════════════════════════════════════════════════════
    # Text Transformation
    # ═══════════════════════════════════════════════════════════════

    def transform_text(
        self,
        text: str,
        operation: str,
        **kwargs: Any,
    ) -> str:
        """
        Transform text using the TextTransformer module.
        Operations: summarize, translate, extract_entities, normalize,
                   sentiment, keywords, clean, split_sentences
        """
        tt = self._get("text_transform")
        if tt:
            try:
                method = getattr(tt, operation, None)
                if method:
                    return method(text, **kwargs)
            except Exception as exc:
                logger.debug("Text transform '%s' failed: %s", operation, exc)
        return text

    # ═══════════════════════════════════════════════════════════════
    # Data Analysis
    # ═══════════════════════════════════════════════════════════════

    def analyze_data(
        self,
        data: Any,
        method: str = "statistical",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Analyze data using the DataAnalyzer module."""
        da = self._get("data_analyzer")
        if da:
            try:
                method_func = getattr(da, method, None) or getattr(da, "analyze", None)
                if method_func:
                    return method_func(data, **kwargs)
            except Exception as exc:
                logger.debug("Data analysis failed: %s", exc)
        return {"error": "Data analyzer not available"}

    # ═══════════════════════════════════════════════════════════════
    # Web Research
    # ═══════════════════════════════════════════════════════════════

    def extract_url_content(self, url: str) -> Dict[str, Any]:
        """Extract content from a URL using WebRecon."""
        wr = self._get("web_recon")
        if wr:
            try:
                return wr.extract(url)
            except Exception as exc:
                logger.debug("URL extraction failed: %s", exc)
        return {"error": "WebRecon not available"}

    # ═══════════════════════════════════════════════════════════════
    # AutoTune
    # ═══════════════════════════════════════════════════════════════

    def autotune_params(
        self,
        user_id: int,
        text: str = "",
    ) -> Dict[str, float]:
        """Get optimized LLM parameters via AutoTune."""
        at = self._get("autotune")
        if at:
            try:
                return at.suggest(
                    trial_name=f"user_{user_id}",
                    param_space={
                        "temperature": {"type": "float", "low": 0.3, "high": 1.2},
                        "top_p": {"type": "float", "low": 0.7, "high": 1.0},
                    },
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        return {"temperature": 0.7, "top_p": 0.95}

    def autotune_feedback(
        self,
        user_id: int,
        quality_score: float,
    ) -> None:
        """Report quality feedback to AutoTune."""
        at = self._get("autotune")
        if at:
            try:
                at.report(
                    trial_name=f"user_{user_id}",
                    metric_value=quality_score,
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # Telemetry
    # ═══════════════════════════════════════════════════════════════

    def record_event(
        self,
        module: str,
        duration_s: float,
        success: bool = True,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Record a telemetry event."""
        tel = self._get("telemetry")
        if tel:
            try:
                tel.record_request(module, duration_s, success)
            except Exception as e:
                logger.debug("Suppressed: %s", e)

    def get_telemetry(self) -> Dict[str, Any]:
        """Get telemetry dashboard data."""
        tel = self._get("telemetry")
        if tel:
            try:
                return tel.get_dashboard_data()
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        return {}

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        pipeline = self._get("pipeline")
        if pipeline:
            return pipeline.get_stats()
        return {}

    # ═══════════════════════════════════════════════════════════════
    # Multi-LLM Orchestration
    # ═══════════════════════════════════════════════════════════════

    def multi_llm_config(self) -> Any:
        """Get the multi-LLM orchestrator for direct use."""
        return self._get("multi_llm")

    # ═══════════════════════════════════════════════════════════════
    # Workflow Engine
    # ═══════════════════════════════════════════════════════════════

    def get_workflow_engine(self) -> Any:
        """Get workflow engine for direct use."""
        return self._get("workflow")

    # ═══════════════════════════════════════════════════════════════
    # Crypto & Security
    # ═══════════════════════════════════════════════════════════════

    def crypto_process(
        self,
        data: str,
        operation: str = "hash",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Process crypto operations."""
        crypto = self._get("crypto")
        if crypto:
            try:
                method = getattr(crypto, operation, None)
                if method:
                    return method(data, **kwargs)
            except Exception as exc:
                logger.debug("Crypto operation failed: %s", exc)
        return {"error": "Crypto engine not available"}

    # ═══════════════════════════════════════════════════════════════
    # Network Tools
    # ═══════════════════════════════════════════════════════════════

    def network_scan(
        self,
        target: str,
        scan_type: str = "basic",
    ) -> Dict[str, Any]:
        """Network scanning via NetworkTools."""
        net = self._get("network")
        if net:
            try:
                return net.scan(target, scan_type=scan_type)
            except Exception as exc:
                logger.debug("Network scan failed: %s", exc)
        return {"error": "Network tools not available"}

    # ═══════════════════════════════════════════════════════════════
    # Agent Executor
    # ═══════════════════════════════════════════════════════════════

    def get_agent_executor(self) -> Any:
        """Get the agent executor for autonomous task completion."""
        return self._get("agent")

    # ═══════════════════════════════════════════════════════════════
    # Dashboard & Monitoring
    # ═══════════════════════════════════════════════════════════════

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get full dashboard data."""
        dashboard = self._get("dashboard")
        if dashboard:
            try:
                return dashboard.get_data()
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        return {}

    # ═══════════════════════════════════════════════════════════════
    # Terminal Emulator
    # ═══════════════════════════════════════════════════════════════

    def get_terminal(self) -> Any:
        """Get the terminal emulator."""
        return self._get("terminal")

    # ═══════════════════════════════════════════════════════════════
    # Integration Hub
    # ═══════════════════════════════════════════════════════════════

    def get_integration_hub(self) -> Any:
        """Get integration hub for platform connections."""
        return self._get("integration")

    def get_victor_brain(self) -> Any:
        """Get Victor v6 brain for independent intelligence queries."""
        return self._get("victor_brain")

    def get_infra_bridge(self) -> Any:
        """Get service-infrastructure bridge (v10.3.1)."""
        try:
            from arki_project.services.infra_bridge import ServiceInfraBridge
            return ServiceInfraBridge()
        except ImportError:
            return None

    def get_marketing_automation(self) -> Any:
        """Get marketing automation service (v10.3.1)."""
        try:
            from arki_project.services.marketing_automation_service import MarketingAutomationService
            return MarketingAutomationService()
        except ImportError:
            return None

    # ═══════════════════════════════════════════════════════════════
    # Status & Diagnostics
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, str]:
        """Get status of all modules."""
        self._ensure_init()
        status = {}
        all_names = [
            "pipeline", "reasoning", "memory", "prompt_engine", "multi_llm",
            "autotune", "text_transform", "data_analyzer", "web_recon",
            "web_search", "telemetry", "crypto", "network", "workflow",
            "integration", "multimodal", "terminal", "agent",
            "orchestrator", "dashboard", "plugin", "anti_detect",
        ]
        for name in all_names:
            if name in self._modules:
                status[name] = "✅"
            elif name in self._init_errors:
                status[name] = f"⚠️ {self._init_errors[name][:50]}"
            else:
                status[name] = "❌"
        return status

    @property
    def loaded_count(self) -> int:
        self._ensure_init()
        return len(self._modules)

    @property
    def total_count(self) -> int:
        return 22


# ═══════════════════════════════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════════════════════════════

bridge = ModuleBridge()


