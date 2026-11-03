"""Tests for the indexer module."""

from types import SimpleNamespace
from pathlib import Path

import pytest
from qdrant_client.http import models

from core.config import settings
from core.contracts import IndexerStats, MoviePayload
from core.model_loader import ModelLoader
from core.qdrant_client import QdrantClientSingleton
from scraper.schemas import Movie
from services.indexer import Indexer


class MockQdrantClient:
    """Keep Qdrant collections and points in memory for unit tests."""

    def __init__(self) -> None:
        self.collections: dict[str, dict[int | str, models.PointStruct]] = {}
        self.vector_configs: dict[str, models.VectorParams] = {}

    def get_collections(self) -> SimpleNamespace:
        return SimpleNamespace(
            collections=[
                SimpleNamespace(name=name) for name in self.collections
            ]
        )

    def create_collection(
        self,
        collection_name: str,
        vectors_config: models.VectorParams,
    ) -> bool:
        self.collections[collection_name] = {}
        self.vector_configs[collection_name] = vectors_config
        return True

    def upsert(
        self,
        collection_name: str,
        points: list[models.PointStruct],
    ) -> None:
        collection = self.collections[collection_name]
        for point in points:
            collection[point.id] = point

    def get_collection(self, collection_name: str) -> SimpleNamespace:
        points = self.collections[collection_name]
        return SimpleNamespace(points_count=len(points), status="green")

    def delete_collection(self, collection_name: str) -> bool:
        self.collections.pop(collection_name, None)
        return True


class MockEmbedding:
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def tolist(self) -> list[float]:
        return self._vector


class MockEmbeddingModel:
    def encode(self, text: str) -> MockEmbedding:
        return MockEmbedding([float(len(text))] * settings.EMBEDDING_DIM)


@pytest.fixture
def qdrant_client() -> MockQdrantClient:
    return MockQdrantClient()


@pytest.fixture
def indexer(
    monkeypatch: pytest.MonkeyPatch,
    qdrant_client: MockQdrantClient,
) -> Indexer:
    monkeypatch.setattr(
        QdrantClientSingleton,
        "get_client",
        staticmethod(lambda: qdrant_client),
    )
    monkeypatch.setattr(
        ModelLoader,
        "get_model",
        staticmethod(lambda: MockEmbeddingModel()),
    )
    return Indexer()
