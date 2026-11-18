"""Tests for reranking service."""

import numpy as np

from src.services.search_service.ranking.ranking import RerankingService
from src.services.search_service.ranking.schemas import RerankingRequest


class MockEmbeddingModel:
    """Small embedding model for reranking tests."""

    def encode(self, texts: str | list[str], convert_to_numpy: bool = True) -> np.ndarray:
        del convert_to_numpy
        if isinstance(texts, str):
            return np.array([1.0, 0.0], dtype=np.float32)

        if texts == ["другой фильм", "лучший фильм"]:
            return np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
        return np.zeros((len(texts), 2), dtype=np.float32)


def test_rerank_uses_downloaded_model_loader(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.search_service.ranking.ranking.ModelLoader.get_model",
        lambda: MockEmbeddingModel(),
    )
    service = RerankingService()

    response = service.rerank(
        RerankingRequest(
            query="фильм",
            documents=[
                {"text": "другой фильм", "id": 1},
                {"text": "лучший фильм", "id": 2},
            ],
        )
    )

    assert [doc["id"] for doc in response.reranked_documents] == [2, 1]
