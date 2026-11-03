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




def test_index_movies_stores_points_in_mock_qdrant(
    tmp_path: Path,
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    movie = Movie(id=42, title="Фильм", description="Описание")
    filepath = tmp_path / "movies.jsonl"
    filepath.write_text(movie.model_dump_json() + "\n", encoding="utf-8")

    indexer.index_movies(filepath)
    stats: IndexerStats = indexer.get_stats()
    point = qdrant_client.collections[indexer.collection_name][movie.id]
    payload = MoviePayload.model_validate(point.payload)

    assert stats.points_count == 1
    expected_vector = [float(len(indexer.prepare_text(movie)))] * settings.EMBEDDING_DIM
    assert point.vector == expected_vector
    assert payload.id == movie.id
    assert payload.title == movie.title


def test_index_movies_with_force_reindex_removes_existing_collection(
    tmp_path: Path,
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    movie = Movie(id=1, title="Movie", description="Description")
    filepath = tmp_path / "movies.jsonl"
    filepath.write_text(movie.model_dump_json() + "\n", encoding="utf-8")

    # First indexing
    indexer.index_movies(filepath)
    assert indexer.get_stats().points_count == 1

    # Second indexing with force_reindex=True
    indexer.index_movies(filepath, force_recreate=True)
    stats: IndexerStats = indexer.get_stats()
    assert stats.points_count == 1  # Should still be 1 after reindexing
