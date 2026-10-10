"""Redacted OpenTelemetry export; no workflow/input/provider payload export."""
from datetime import datetime

SAFE_DETAILS = {'status', 'node_id', 'outcome', 'approval_id', 'error_code', 'correlation_id', 'trace_reference'}


class OpenTelemetryObserver:
    def __init__(self, tracer):
        self.tracer = tracer

    def export(self, event):
        # Only application identifiers/status are sent to the configured tracer.
        attributes = {key: event[key] for key in ('event_id', 'run_id', 'workflow_id', 'workflow_version', 'source', 'event_type')}
        attributes.update({key: value for key, value in event.get('details', {}).items()
                           if key in SAFE_DETAILS and isinstance(value, (str, int, bool))})
        instant = int(datetime.fromisoformat(event['timestamp']).timestamp() * 1_000_000_000)
        span = self.tracer.start_span(event['event_type'], attributes=attributes, start_time=instant)
        span.end(end_time=instant)


def otlp_observer(endpoint, headers=None):
    """Use an operator-configured OTel or Langfuse-compatible OTLP endpoint.

    The application supplies credentials as headers directly to the exporter;
    they are never span attributes or runtime storage. No global tracer changes.
    """
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers or {}, timeout=5)))
    observer = OpenTelemetryObserver(provider.get_tracer('agentic-ai-builder.runtime'))
    observer.provider = provider
    return observer
