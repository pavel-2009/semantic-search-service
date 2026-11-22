"""OpenTelemetry tracing and metrics initialization and instruments."""

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

meter = metrics.get_meter("semantic-search-service")

http_requests_total = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="1",
)
http_request_duration_ms = meter.create_histogram(
    name="http_request_duration_ms",
    description="HTTP request latency in milliseconds",
    unit="ms",
)
search_requests_total = meter.create_counter(
    name="search_requests_total",
    description="Total number of search pipeline executions",
    unit="1",
)
search_stage_duration_ms = meter.create_histogram(
    name="search_stage_duration_ms",
    description="Duration of search pipeline stages in milliseconds",
    unit="ms",
)
search_results_count = meter.create_histogram(
    name="search_results_count",
    description="Number of documents returned by search",
    unit="1",
)


def init_telemetry(
    service_name: str,
    service_version: str,
    otlp_endpoint: str | None = None,
    console_export: bool = False,
    trace_endpoint: str | None = None,
) -> None:
    """Initialize OpenTelemetry tracing and metrics collection."""
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
        }
    )

    trace_provider = TracerProvider(resource=resource)
    if trace_endpoint:
        trace_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=trace_endpoint))
        )
    trace.set_tracer_provider(trace_provider)

    readers: list[MetricReader] = []
    if otlp_endpoint:
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint)))
    elif console_export:
        readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))

    meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(meter_provider)


def shutdown_telemetry() -> None:
    """Flush and shut down active OpenTelemetry providers."""
    meter_provider = metrics.get_meter_provider()
    if isinstance(meter_provider, MeterProvider):
        meter_provider.shutdown()

    tracer_provider = trace.get_tracer_provider()
    if isinstance(tracer_provider, TracerProvider):
        tracer_provider.shutdown()


def get_tracer(service_name: str = "semantic-search-service") -> trace.Tracer:
    """Get or create a tracer."""
    return trace.get_tracer(service_name)
