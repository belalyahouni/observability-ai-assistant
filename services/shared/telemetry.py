"""Shared OpenTelemetry setup for all microservices."""

import logging
import os

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def setup_telemetry(app, service_name: str):
    """Initialize OpenTelemetry tracing, metrics, and logging for a FastAPI app."""

    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    resource = Resource.create({SERVICE_NAME: service_name})

    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_exporter = OTLPMetricExporter(endpoint=otel_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Inject trace/span IDs into log records
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '{"timestamp":"%(asctime)s","service":"'
            + service_name
            + '","level":"%(levelname)s","message":"%(message)s",'
            '"trace_id":"%(otelTraceID)s","span_id":"%(otelSpanID)s"}'
        ),
    )

    return trace.get_tracer(service_name), metrics.get_meter(service_name)
