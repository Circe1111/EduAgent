import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME


OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "eduagent-backend")


class NoopSpanProcessor:
    """No-op span processor when OTEL is not configured."""

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        pass


def setup_telemetry() -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry tracing.
    Returns a tracer if configured, otherwise returns None (no-op).
    """
    resource = Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    if OTEL_EXPORTER_OTLP_ENDPOINT:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            # Fallback to no-op if exporter not installed
            provider.add_span_processor(NoopSpanProcessor())  # type: ignore[arg-type]
    else:
        provider.add_span_processor(NoopSpanProcessor())  # type: ignore[arg-type]

    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)
