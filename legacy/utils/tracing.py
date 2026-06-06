
from __future__ import annotations
"""
tg_bot/utils/tracing.py — Distributed Tracing v9.3
OpenTelemetry integration for distributed tracing.
"""
import logging
import os
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

_tracer = None


def setup_tracing(service_name: str = "arki-engine") -> None:
    """Initialize OpenTelemetry tracing."""
    global _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        # Export to OTLP if endpoint configured
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(__name__)
        logger.info("OpenTelemetry tracing initialized")
    except ImportError:
        logger.debug("OpenTelemetry not installed, tracing disabled")
    except Exception as e:
        logger.warning("Tracing setup failed: %s", e)


def get_tracer() -> None:
    """Get the active tracer (or a no-op)."""
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer(__name__)
        except ImportError:
            # Return a no-op tracer
            class NoOpTracer:
                def start_as_current_span(self, name: str, **kwargs) -> None:
                    return _noop_context()
            _tracer = NoOpTracer()
    return _tracer


@asynccontextmanager
async def trace_span(name: str, attributes: dict = None) -> None:
    """Async context manager for creating trace spans."""
    tracer = get_tracer()
    try:
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span
    except Exception:
        yield None


from contextlib import contextmanager

# ── TITANIUM v29.0 Integration ──


@contextmanager
def _noop_context() -> None:
    yield None


