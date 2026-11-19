"""Tests for ranking documents retrieved from Qdrant."""

from qdrant_client.models import ScoredPoint

import src.services.search_service.ranking.ranking as ranking_module
from src.services.search_service.ranking.ranking import RerankingService
from src.services.search_service.ranking.schemas import RerankingRequest


class MockCrossEncoder:
    def __init__(self, model_name: str, *, device: str | None = None) -> None:
        self.configuration = model_name, device
        self.inputs: list[tuple[str, str]] = []

    def predict(self, inputs: list[tuple[str, str]]) -> list[float]:
        self.inputs = inputs
        return [0.95 for _ in inputs]


def test_rerank_builds_labeled_text_and_returns_structured_point_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(ranking_module, "CrossEncoder", MockCrossEncoder)
    service = RerankingService()
    point = ScoredPoint(
        id=42,
        version=1,
        score=0.7,
        payload={
            "id": 42,
            "title": "Интерстеллар",
            "year": 2014,
            "countries": ["США", "Великобритания"],
            "genres": ["фантастика", "драма"],
            "moods": ["эпичный"],
            "rating": 8.6,
            "description": "Экспедиция в космос ради спасения человечества.",
        },
    )

    response = service.rerank(
        RerankingRequest(query="космическое путешествие", documents=[point])
    )

    assert service.model.inputs == [
        (
            "космическое путешествие",
            "Название: Интерстеллар. Год: 2014. Страны: США, Великобритания. "
            "Жанры: фантастика, драма. Настроение: эпичный. Рейтинг: 8.6. "
            "Сюжет: Экспедиция в космос ради спасения человечества.",
        )
    ]
    assert response.reranked_documents == [
        {
            "id": 42,
            "title": "Интерстеллар",
            "year": 2014,
            "countries": ["США", "Великобритания"],
            "genres": ["фантастика", "драма"],
            "moods": ["эпичный"],
            "rating": 8.6,
            "description": "Экспедиция в космос ради спасения человечества.",
            "score": 0.95,
        }
    ]


def test_document_from_point_omits_empty_fields_but_keeps_zero_rating() -> None:
    document, text = RerankingService._document_from_point(
        ScoredPoint(
            id=1,
            version=1,
            score=0.0,
            payload={"title": "Фильм", "year": None, "genres": [], "rating": 0},
        )
    )

    assert document["id"] == 1
    assert text == "Название: Фильм. Рейтинг: 0"
