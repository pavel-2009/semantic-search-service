"""Tests for OpenTelemetry initialization and service metrics."""

from unittest.mock import Mock

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

from src.core import telemetry
from src.services.search_service.schemas import SearchQuery
from src.services.search_service.search_service import SearchService


def test_init_and_shutdown_telemetry() -> None:
    telemetry.init_telemetry(service_name="test-api", service_version="0.1.0")
    assert isinstance(metrics.get_meter_provider(), MeterProvider)
    assert isinstance(trace.get_tracer_provider(), TracerProvider)
    telemetry.shutdown_telemetry()


def test_search_service_records_pipeline_metrics(monkeypatch) -> None:
    requests_counter = Mock()
    stage_histogram = Mock()
    results_histogram = Mock()

    monkeypatch.setattr("src.services.search_service.search_service.search_requests_total", requests_counter)
    monkeypatch.setattr("src.services.search_service.search_service.search_stage_duration_ms", stage_histogram)
    monkeypatch.setattr("src.services.search_service.search_service.search_results_count", results_histogram)

    parser = Mock()
    parser.parse.return_value = Mock(filter=None)
    embedder = Mock()
    qdrant_repo = Mock()
    qdrant_repo.get_points.return_value = Mock(response=[])
    reranker = Mock()
    reranker.rerank.return_value = Mock(reranked_documents=[{"id": 1}, {"id": 2}])

    service = SearchService(
        parser=parser,
        embedder=embedder,
        qdrant_repo=qdrant_repo,
        reranker=reranker,
    )
    service.search(SearchQuery(text="космос", top_k=5))

    requests_counter.add.assert_called_once_with(1, {"status": "ok"})
    results_histogram.record.assert_called_once_with(2)
    stages = [call.args[1]["stage"] for call in stage_histogram.record.call_args_list]
    assert stages == ["parse", "embed", "retrieve", "rerank", "total"]
