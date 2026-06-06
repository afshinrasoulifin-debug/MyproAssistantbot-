
from __future__ import annotations
"""
utils/consensus_engine.py — Multi-Model Consensus Engine v26.0
═══════════════════════════════════════════════════════════════════
Runs multiple models in parallel and selects the best response.

Strategies:
  RACE     — First complete response wins (for Fast tier)
  BEST_OF  — Run N models, pick highest quality (for Pro tier)
  CONSENSUS — Run N models, evaluate all, synthesize best (for Ultra tier)

Scoring:
  - Length adequacy (30%) — Not too short, not padded
  - Coherence (25%) — Well-structured, consistent
  - Relevance (25%) — Addresses the actual question
  - Speed bonus (20%) — Faster responses get a boost
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List

logger = logging.getLogger("arki.consensus")


class ConsensusStrategy(str, Enum):
    RACE = "race"          # First response wins
    BEST_OF = "best_of"    # Best quality from N
    CONSENSUS = "consensus" # Evaluate + synthesize


@dataclass
class ModelResponse:
    """A single model's response with metadata."""
    model_key: str
    model_id: str
    text: str
    latency_ms: float
    success: bool
    error: str = ""
    quality_score: float = 0.0


@dataclass
class ConsensusResult:
    """Final consensus result."""
    text: str
    strategy: ConsensusStrategy
    winning_model: str
    total_models_queried: int
    responses_received: int
    latency_ms: float
    quality_score: float
    model_scores: Dict[str, float] = field(default_factory=dict)
    synthesis_used: bool = False


def _score_response(response: str, query: str, latency_ms: float) -> float:
    """
    Score a response on 0-1 scale.

    Dimensions:
      - Length adequacy (0.30): Ideal 100-2000 chars for most queries
      - Coherence (0.25): Structure, paragraphs, no repetition
      - Relevance (0.25): Query terms appear in response
      - Speed (0.20): Faster is better (0-30s range)
    """
    if not response or not response.strip():
        return 0.0

    score = 0.0
    text = response.strip()

    # ── Length adequacy (30%) ──
    char_count = len(text)
    query_len = len(query.strip())

    if query_len < 20:  # Short question
        ideal_min, ideal_max = 50, 800
    elif query_len < 100:  # Medium question
        ideal_min, ideal_max = 100, 2000
    else:  # Long/complex question
        ideal_min, ideal_max = 200, 4000

    if ideal_min <= char_count <= ideal_max:
        length_score = 1.0
    elif char_count < ideal_min:
        length_score = max(0.1, char_count / ideal_min)
    else:
        # Penalize padding but don't over-penalize long detailed responses
        length_score = max(0.5, 1.0 - (char_count - ideal_max) / (ideal_max * 3))
    score += length_score * 0.30

    # ── Coherence (25%) ──
    coherence = 0.5  # Base
    # Has structure (headers, bullets, paragraphs)
    if any(m in text for m in ["\n\n", "\n- ", "\n• ", "\n1.", "\n* ", "**", "##"]):
        coherence += 0.2
    # No excessive repetition
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 10]
    if sentences:
        unique_ratio = len(set(sentences)) / len(sentences)
        coherence += unique_ratio * 0.3
    else:
        coherence += 0.15
    score += min(coherence, 1.0) * 0.25

    # ── Relevance (25%) ──
    query_words = set(query.lower().split())
    # Remove stop words
    stop_words = {"و", "از", "به", "در", "که", "را", "با", "این", "برای", "آن",
                  "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                  "to", "for", "of", "with", "by", "it", "i", "you", "we", "they"}
    query_words -= stop_words
    if query_words:
        response_lower = text.lower()
        matches = sum(1 for w in query_words if w in response_lower)
        relevance = min(1.0, matches / max(1, len(query_words)))
    else:
        relevance = 0.5
    score += relevance * 0.25

    # ── Speed (20%) ──
    # 0ms → 1.0, 30000ms → 0.0
    speed_score = max(0.0, 1.0 - (latency_ms / 30000))
    score += speed_score * 0.20

    return round(score, 4)


class ConsensusEngine:
    """
    Multi-model consensus engine for Pro/Ultra tiers.

    Usage:
        engine = get_consensus_engine()
        result = await engine.run(
            query="...",
            models=["model1", "model2", "model3"],
            call_fn=ai_client._call_single_model,
            strategy=ConsensusStrategy.CONSENSUS,
        )
    """

    def __init__(self) -> None:
        self._history: List[Dict] = []

    async def run(
        self,
        query: str,
        messages: List[Dict[str, str]],
        models: List[str],
        call_fn: Callable[..., Coroutine],
        strategy: ConsensusStrategy = ConsensusStrategy.BEST_OF,
        timeout_seconds: float = 45.0,
        temperature: float = 0.7,
        max_tokens: int = 65536,
    ) -> ConsensusResult:
        """
        Run multi-model consensus.

        Args:
            query: Original user query
            messages: Full message list (with system prompt)
            models: List of model_keys to query
            call_fn: Async function(msgs, model_key, temperature, max_tokens) → str
            strategy: RACE, BEST_OF, or CONSENSUS
            timeout_seconds: Max wait time
        """
        t0 = time.monotonic()
        logger.info(
            "Consensus[%s] starting with %d models: %s",
            strategy.value, len(models), models,
        )

        if strategy == ConsensusStrategy.RACE:
            return await self._run_race(query, messages, models, call_fn, timeout_seconds, temperature, max_tokens, t0)
        elif strategy == ConsensusStrategy.BEST_OF:
            return await self._run_best_of(query, messages, models, call_fn, timeout_seconds, temperature, max_tokens, t0)
        else:  # CONSENSUS
            return await self._run_consensus(query, messages, models, call_fn, timeout_seconds, temperature, max_tokens, t0)

    async def _call_model_safe(
        self,
        model_key: str,
        messages: List[Dict],
        call_fn: Callable,
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        """Call a model with error handling."""
        t0 = time.monotonic()
        try:
            result = await call_fn(messages, model_key, temperature=temperature, max_tokens=max_tokens)
            latency = (time.monotonic() - t0) * 1000
            return ModelResponse(
                model_key=model_key,
                model_id=model_key,
                text=result if isinstance(result, str) else str(result),
                latency_ms=latency,
                success=True,
            )
        except Exception as e:
            latency = (time.monotonic() - t0) * 1000
            logger.warning("Consensus model %s failed: %s", model_key, e)
            return ModelResponse(
                model_key=model_key,
                model_id=model_key,
                text="",
                latency_ms=latency,
                success=False,
                error=str(e),
            )

    async def _run_race(self, query: str, messages: list, models: list, call_fn: Any, timeout: int, temp: Any, max_tok: Any, t0: Any) -> ConsensusResult:
        """RACE strategy: first complete response wins."""
        tasks = {
            model: asyncio.create_task(
                self._call_model_safe(model, messages, call_fn, temp, max_tok)
            )
            for model in models
        }

        done = set()
        winner = None

        try:
            # Wait for first successful result
            while tasks and not winner:
                completed, _ = await asyncio.wait(
                    tasks.values(),
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in completed:
                    resp = task.result()
                    done.add(resp.model_key)
                    if resp.success and resp.text.strip():
                        winner = resp
                        break
                if not completed:
                    break  # Timeout
        finally:
            # Cancel remaining tasks
            for model, task in tasks.items():
                if model not in done:
                    task.cancel()

        if winner:
            latency = (time.monotonic() - t0) * 1000
            return ConsensusResult(
                text=winner.text,
                strategy=ConsensusStrategy.RACE,
                winning_model=winner.model_key,
                total_models_queried=len(models),
                responses_received=len(done),
                latency_ms=latency,
                quality_score=_score_response(winner.text, query, winner.latency_ms),
            )

        # All failed — return error
        return ConsensusResult(
            text="⚠️ تمام مدل‌ها با خطا مواجه شدند. لطفاً دوباره تلاش کنید.",
            strategy=ConsensusStrategy.RACE,
            winning_model="none",
            total_models_queried=len(models),
            responses_received=0,
            latency_ms=(time.monotonic() - t0) * 1000,
            quality_score=0.0,
        )

    async def _run_best_of(self, query: str, messages: list, models: list, call_fn: Any, timeout: int, temp: Any, max_tok: Any, t0: Any) -> ConsensusResult:
        """BEST_OF strategy: run all, pick highest quality."""
        tasks = [
            self._call_model_safe(model, messages, call_fn, temp, max_tok)
            for model in models
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses: List[ModelResponse] = []
        for r in responses:
            if isinstance(r, ModelResponse) and r.success and r.text.strip():
                r.quality_score = _score_response(r.text, query, r.latency_ms)
                valid_responses.append(r)

        if not valid_responses:
            return ConsensusResult(
                text="⚠️ تمام مدل‌ها با خطا مواجه شدند. لطفاً دوباره تلاش کنید.",
                strategy=ConsensusStrategy.BEST_OF,
                winning_model="none",
                total_models_queried=len(models),
                responses_received=0,
                latency_ms=(time.monotonic() - t0) * 1000,
                quality_score=0.0,
            )

        # Sort by quality
        valid_responses.sort(key=lambda r: r.quality_score, reverse=True)
        winner = valid_responses[0]

        model_scores = {r.model_key: r.quality_score for r in valid_responses}
        latency = (time.monotonic() - t0) * 1000

        return ConsensusResult(
            text=winner.text,
            strategy=ConsensusStrategy.BEST_OF,
            winning_model=winner.model_key,
            total_models_queried=len(models),
            responses_received=len(valid_responses),
            latency_ms=latency,
            quality_score=winner.quality_score,
            model_scores=model_scores,
        )

    async def _run_consensus(self, query: str, messages: list, models: list, call_fn: Any, timeout: int, temp: Any, max_tok: Any, t0: Any) -> ConsensusResult:
        """CONSENSUS strategy: evaluate all, synthesize if needed."""
        tasks = [
            self._call_model_safe(model, messages, call_fn, temp, max_tok)
            for model in models
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        valid_responses: List[ModelResponse] = []
        for r in responses:
            if isinstance(r, ModelResponse) and r.success and r.text.strip():
                r.quality_score = _score_response(r.text, query, r.latency_ms)
                valid_responses.append(r)

        if not valid_responses:
            return ConsensusResult(
                text="⚠️ تمام مدل‌ها با خطا مواجه شدند. لطفاً دوباره تلاش کنید.",
                strategy=ConsensusStrategy.CONSENSUS,
                winning_model="none",
                total_models_queried=len(models),
                responses_received=0,
                latency_ms=(time.monotonic() - t0) * 1000,
                quality_score=0.0,
            )

        valid_responses.sort(key=lambda r: r.quality_score, reverse=True)
        best = valid_responses[0]
        model_scores = {r.model_key: r.quality_score for r in valid_responses}

        # If top response is significantly better, use it directly
        if len(valid_responses) == 1 or best.quality_score > 0.85:
            return ConsensusResult(
                text=best.text,
                strategy=ConsensusStrategy.CONSENSUS,
                winning_model=best.model_key,
                total_models_queried=len(models),
                responses_received=len(valid_responses),
                latency_ms=(time.monotonic() - t0) * 1000,
                quality_score=best.quality_score,
                model_scores=model_scores,
                synthesis_used=False,
            )

        # If scores are close, synthesize: take the best and append unique insights from others
        synthesis_parts = [best.text]
        for resp in valid_responses[1:]:
            if resp.quality_score > 0.5:
                # Check if this response has unique content not in the best
                resp_sentences = set(s.strip() for s in resp.text.split(".") if len(s.strip()) > 20)
                best_text_lower = best.text.lower()
                unique_insights = [
                    s for s in resp_sentences
                    if s.lower() not in best_text_lower and len(s) > 30
                ]
                if unique_insights:
                    synthesis_parts.append("\n\n💡 *نکات تکمیلی:*")
                    for insight in unique_insights[:3]:  # Max 3 additional insights
                        synthesis_parts.append(f"• {insight}")
                    break  # Only add from one additional model

        final_text = "\n".join(synthesis_parts)
        latency = (time.monotonic() - t0) * 1000
        
        # Re-score the synthesis
        final_score = _score_response(final_text, query, latency)

        return ConsensusResult(
            text=final_text,
            strategy=ConsensusStrategy.CONSENSUS,
            winning_model=best.model_key,
            total_models_queried=len(models),
            responses_received=len(valid_responses),
            latency_ms=latency,
            quality_score=max(best.quality_score, final_score),
            model_scores=model_scores,
            synthesis_used=len(synthesis_parts) > 1,
        )


    async def run_streaming(
        self,
        query: str,
        messages: list,
        models: list,
        call_fn: Any,
        strategy: ConsensusStrategy = ConsensusStrategy.BEST_OF,
        timeout_seconds: float = 60.0,
        temperature: float = 0.7,
        max_tokens: int = 65536,
    ) -> None:
        """v26.1: Streaming consensus — yields partial results as models complete.
        
        Yields ConsensusResult objects as each model responds.
        First yield = fastest model result (best UX).
        Final yield = best/synthesized result.
        
        Usage:
            async for partial_result in ce.run_streaming(...):
                await update_telegram_message(partial_result.text)
        """
        import asyncio

        results = {}
        pending = set()

        async def _call_one(model: str) -> Any:
            try:
                t0 = __import__("time").monotonic()
                resp = await asyncio.wait_for(
                    call_fn(messages, model, temperature=temperature, max_tokens=max_tokens),
                    timeout=timeout_seconds,
                )
                elapsed = __import__("time").monotonic() - t0
                results[model] = {"text": resp, "latency": elapsed}
            except Exception as e:
                logger.debug("Streaming consensus: %s failed: %s", model, e)
                results[model] = None

        # Launch all models concurrently
        tasks = {model: asyncio.create_task(_call_one(model)) for model in models}
        pending = set(tasks.values())

        yielded_count = 0
        best_text = ""
        best_model = ""
        best_quality = 0.0

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                # Find which model completed
                completed_model = None
                for m, t in tasks.items():
                    if t is task:
                        completed_model = m
                        break
                
                if not completed_model or not results.get(completed_model):
                    continue

                result_data = results[completed_model]
                text = result_data["text"]
                latency = result_data["latency"]

                # Simple quality heuristic for streaming (fast)
                quality = min(1.0, len(text) / 500) * 0.5 + 0.5

                if quality > best_quality or yielded_count == 0:
                    best_text = text
                    best_model = completed_model
                    best_quality = quality

                yielded_count += 1
                yield ConsensusResult(
                    text=best_text,
                    strategy=strategy,
                    winning_model=best_model,
                    total_models_queried=len(models),
                    responses_received=yielded_count,
                    quality_score=best_quality,
                    latency_ms=latency * 1000,
                    synthesis_used=False,
                )

        # Final yield with synthesis for CONSENSUS strategy
        if strategy == ConsensusStrategy.CONSENSUS and len(results) >= 2:
            valid = {m: r["text"] for m, r in results.items() if r}
            if len(valid) >= 2:
                # Simple synthesis: pick longest + most detailed
                sorted_by_len = sorted(valid.items(), key=lambda x: len(x[1]), reverse=True)
                best_text = sorted_by_len[0][1]
                best_model = sorted_by_len[0][0]
                yield ConsensusResult(
                    text=best_text,
                    strategy=strategy,
                    winning_model=best_model,
                    total_models_queried=len(models),
                    responses_received=len(valid),
                    quality_score=best_quality,
                    latency_ms=max(r["latency"] for r in results.values() if r) * 1000,
                    synthesis_used=True,
                )

    def get_stats(self) -> Dict:
        """Return consensus engine statistics."""
        return {
            "history_size": len(self._history),
        }


# ═══════════════════ SINGLETON ═══════════════════

_consensus_engine: ConsensusEngine | None = None

def get_consensus_engine() -> ConsensusEngine:
    """Get or create singleton ConsensusEngine."""
    global _consensus_engine
    if _consensus_engine is None:
        _consensus_engine = ConsensusEngine()
    return _consensus_engine


