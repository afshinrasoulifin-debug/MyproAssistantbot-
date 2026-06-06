
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.types import Message
from arki_project.utils.safe_send import safe_edit_text

logger = logging.getLogger(__name__)

class ThinkingAgentPro:
    """
    Advanced Thinking Agent for Arki v10.
    Manages the 'Internal Monologue' and visual feedback in Telegram.
    """
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        initial_message: Message,
        total_steps: int = 1,
        update_interval_seconds: int = 2,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        fallback_models: Optional[List[str]] = None,
        timeout_per_step: int = 60,
    ):
        self.bot = bot
        self.chat_id = chat_id
        self.initial_message = initial_message
        self.message_id = initial_message.message_id
        self.update_interval = timedelta(seconds=update_interval_seconds)
        self.last_update_time: Optional[datetime] = None
        self.current_thought: str = ""
        self.status_emoji: str = "🧠"
        self.active_model: str = "N/A"
        self.start_time: datetime = datetime.now()
        self.current_step_index: int = 0
        self.total_steps: int = total_steps
        self.steps: List[Dict[str, Any]] = [
            {"description": f"گام {i+1}", "status": "pending"}
            for i in range(total_steps)
        ]
        self.self_correction_log: List[str] = []
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.fallback_models = fallback_models if fallback_models is not None else []
        self.timeout_per_step = timeout_per_step
        self.current_model_key: str = "N/A"
        
        # v10.5: Advanced Reasoning & State
        self.scratchpad: List[Dict[str, Any]] = []
        self.recursive_depth: int = 0
        self.max_recursive_depth: int = 3
        self.history: List[Dict[str, Any]] = []

    async def _send_typing_action(self):
        try:
            await self.bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug(f"Could not send chat action: {e}")

    def _generate_progress_bar(self) -> str:
        if self.total_steps <= 0: return ""
        progress = (self.current_step_index / self.total_steps)
        bar_length = 10
        filled_length = int(round(bar_length * progress))
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        percentage = int(round(progress * 100))
        return f"`[{bar}] {percentage}%`"

    def _generate_steps_list(self) -> str:
        step_lines = []
        for i, step in enumerate(self.steps):
            status = step["status"]
            if status == "completed":
                emoji = "✅"
            elif status == "in_progress":
                emoji = "⏳"
            elif status == "failed":
                emoji = "❌"
            elif status == "self_correcting":
                emoji = "🔄"
            else:
                emoji = "⚪" # Pending
            step_lines.append(f"{emoji} {step['description']}")
        return "\n".join(step_lines)

    def _generate_self_correction_display(self) -> str:
        if not self.self_correction_log: return ""
        log_display = "\n".join([f"  `⚠️ {msg}`" for msg in self.self_correction_log[-2:]])
        return f"\n\n*گزارش خود-اصلاحی:*\n{log_display}"

    def _generate_scratchpad_display(self) -> str:
        if not self.scratchpad: return ""
        latest = self.scratchpad[-1]
        return f"\n\n*دفترچه استدلال ({latest['type']}):*\n`> {latest['content']}`"

    async def _update_telegram_message(self, force: bool = False):
        now = datetime.now()
        if not force and (self.last_update_time is None or (now - self.last_update_time) < self.update_interval):
            return

        elapsed_time = now - self.start_time
        elapsed_str = str(elapsed_time).split('.')[0].split(':')[-2:] # MM:SS
        elapsed_str = ":".join(elapsed_str)

        full_text = (
            f"{self.status_emoji} *ایجنت در حال تفکر...* (`{elapsed_str}`)\n\n"
            f"{self._generate_progress_bar()}\n"
            f"*مدل فعال:* `{self.current_model_key}`\n"
            f"*ذهن ایجنت:* {self.current_thought}\n\n"
            f"*گام‌های عملیاتی:*\n{self._generate_steps_list()}"
            f"{self._generate_scratchpad_display()}"
            f"{self._generate_self_correction_display()}"
        )

        # Use Arki's safe_edit_text for consistency and error handling
        await safe_edit_text(self.initial_message, full_text, parse_mode="Markdown")
        self.last_update_time = now

    async def set_total_steps(self, total_steps: int, step_descriptions: Optional[List[str]] = None):
        self.total_steps = total_steps
        if step_descriptions and len(step_descriptions) == total_steps:
            self.steps = [
                {"description": desc, "status": "pending"}
                for desc in step_descriptions
            ]
        else:
            self.steps = [
                {"description": f"گام {i+1}", "status": "pending"}
                for i in range(total_steps)
            ]
        await self._update_telegram_message(force=True)

    async def update_thought(self, thought: str, status_emoji: str = "🧠", active_model: Optional[str] = None, log_level: str = "info"):
        self.current_thought = thought
        if status_emoji: self.status_emoji = status_emoji
        if active_model: self.current_model_key = active_model
        
        # Real-world Network Strategy Decision
        if "ارسال" in thought or "دریافت" in thought or "نفوذ" in thought:
            try:
                from arki_project.orchestration.stealth_commander import stealth_commander
                # Dynamically adjust stealth strategy based on the current thought
                stealth_commander.report_status(f"thinking_agent:{thought}")
            except ImportError:
                pass

        await self._update_telegram_message()
        await self._send_typing_action()
        
        log_msg = f"[{self.chat_id}] Thought: {thought} (Model: {self.current_model_key})"
        if log_level == "info":
            logger.info(log_msg)
        elif log_level == "warning":
            logger.warning(log_msg)
        elif log_level == "error":
            logger.error(log_msg)
        elif log_level == "critical":
            logger.critical(log_msg)

    async def start_step(self, step_index: int, description: Optional[str] = None):
        if 0 <= step_index < self.total_steps:
            self.current_step_index = step_index
            self.steps[step_index]["status"] = "in_progress"
            if description: self.steps[step_index]["description"] = description
            await self.update_thought(f"شروع: {self.steps[step_index]['description']}", status_emoji="⏳")

    async def complete_step(self, step_index: int, success: bool = True):
        if 0 <= step_index < self.total_steps:
            self.steps[step_index]["status"] = "completed" if success else "failed"
            # Auto-advance progress bar visually
            if success and self.current_step_index == step_index:
                self.current_step_index += 1
            await self._update_telegram_message(force=True)

    async def log_self_correction(self, message: str, log_level: str = "warning"):
        self.self_correction_log.append(message)
        if 0 <= self.current_step_index < self.total_steps:
            self.steps[self.current_step_index]["status"] = "self_correcting"
        await self.update_thought(f"خود-اصلاحی: {message}", status_emoji="🔄", log_level=log_level)

    async def log_resilience_event(self, event_type: str, details: str, log_level: str = "info"):
        """Log resilience events like retries or fallbacks."""
        message = f"[{event_type}] {details}"
        self.self_correction_log.append(message)
        await self.update_thought(message, status_emoji="⚠️", log_level=log_level)

    async def add_reasoning_step(self, step_type: str, content: str):
        """Adds a reasoning step to the scratchpad."""
        self.scratchpad.append({"type": step_type, "content": content, "timestamp": datetime.now()})
        await self.update_thought(f"استدلال: {step_type}", status_emoji="🧩")

    async def recursive_review(self, failure_reason: str):
        """Reviews the current state and decides on a new strategy."""
        self.recursive_depth += 1
        if self.recursive_depth > self.max_recursive_depth:
            raise Exception("حداکثر عمق بازبینی مجدد فراتر رفت.")
            
        review_msg = f"بازبینی استراتژی (عمق {self.recursive_depth}): {failure_reason}"
        await self.log_self_correction(review_msg, log_level="warning")
        await self.add_reasoning_step("REVIEW", f"تغییر استراتژی به دلیل: {failure_reason}")

    async def execute_with_resilience(
        self,
        func,
        *args,
        step_index: int,
        primary_model_key: str,
        **kwargs,
    ):
        current_model_keys = [primary_model_key] + self.fallback_models
        for attempt in range(self.max_retries + 1):
            for model_key in current_model_keys:
                try:
                    if attempt > 0:
                        backoff_delay = self.initial_backoff * (2 ** (attempt - 1))
                        await self.log_self_correction(
                            f"تلاش مجدد {attempt}/{self.max_retries} با مدل {model_key} (تاخیر {backoff_delay:.1f} ثانیه)",
                            log_level="warning"
                        )
                        await asyncio.sleep(backoff_delay)
                    elif model_key != primary_model_key:
                        await self.log_self_correction(
                            f"سوئیچ به مدل جایگزین {model_key}",
                            log_level="warning"
                        )

                    await self.update_thought(
                        f"در حال اجرای گام {step_index+1} با مدل {model_key}...",
                        active_model=model_key
                    )
                    
                    # Execute the function with a timeout
                    result = await asyncio.wait_for(func(*args, model_key=model_key, **kwargs), timeout=self.timeout_per_step)
                    return result
                except asyncio.TimeoutError:
                    await self.log_self_correction(
                        f"گام {step_index+1} با مدل {model_key} به دلیل تایم‌اوت ({self.timeout_per_step} ثانیه) شکست خورد.",
                        log_level="error"
                    )
                except Exception as e:
                    await self.log_self_correction(
                        f"گام {step_index+1} با مدل {model_key} شکست خورد: {e.__class__.__name__} ({str(e)}).",
                        log_level="error"
                    )
            # If all models failed for this attempt, log and continue to next attempt
            if attempt < self.max_retries:
                await self.log_self_correction(
                    f"تمام مدل‌ها در تلاش {attempt+1}/{self.max_retries+1} شکست خوردند. تلاش مجدد...",
                    log_level="error"
                )
            else:
                await self.log_self_correction(
                    f"تمام تلاش‌ها ({self.max_retries+1}) با تمام مدل‌ها شکست خوردند.",
                    log_level="critical"
                )
        raise Exception("تمام تلاش‌ها برای اجرای گام با شکست مواجه شد.")

    async def end_thinking(self, final_result_text: str, success: bool = True):
        emoji = "✅" if success else "❌"
        elapsed_time = datetime.now() - self.start_time
        elapsed_str = str(elapsed_time).split('.')[0].split(':')[-2:]
        elapsed_str = ":".join(elapsed_str)

        final_status_text = (
            f"{emoji} *پایان پردازش* (`{elapsed_str}`)\n\n"
            f"{final_result_text}"
        )
        await safe_edit_text(self.initial_message, final_status_text, parse_mode="Markdown")
        logger.info(f"ThinkingAgentPro finished for chat {self.chat_id}")

    async def __aenter__(self):
        # Initial status update
        await self._update_telegram_message(force=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"ThinkingAgentPro error: {exc_val}")
            await self.end_thinking(f"⚠️ خطای سیستمی: {exc_val}", success=False)


