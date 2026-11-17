"""Tests for the indexer module."""

import random
from pathlib import Path
from types import SimpleNamespace

from httpx import Headers
import pytest
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.contracts import IndexerStats, Movie
from src.core.qdrant_client import QdrantClientSingleton
import src.services.indexer.embedder as embedder_module
from src.services.indexer.config import config
from src.services.indexer.indexer import Indexer
from src.services.indexer.schemas import SparseVectorData
from src.services.search_service.embedder.schemas import EmbedderResponse
from src.services.search_service.parsing import ParsedText


def make_movie_card(movie_id: int = 1, title: str = "Movie") -> Movie:
    """Create a valid Movie instance for tests."""
    return Movie(
        id=movie_id,
        title=title,
        description=f"Description for {title} that is long enough",
        year=2024,
        rating=8.0,
        genres=["драма"],
        countries=["Россия"],
    )


@pytest.fixture
def create_jsonl_file_with_200_movies_for_batching(tmp_path: Path) -> Path:
    """Create a JSONL file with 200 movie entries for testing."""
    filepath = tmp_path / "movies.jsonl"
    with filepath.open("w", encoding="utf-8") as f:
        for i in range(200):
            movie = make_movie_card(movie_id=i, title=f"Movie {i}")
            f.write(movie.model_dump_json() + "\n")
    return filepath


class MockQdrantClient:
    """Keep Qdrant collections and points in memory for unit tests."""

    def __init__(self) -> None:
        self.collections: dict[str, dict[int | str, models.PointStruct]] = {}
        self.vector_configs: dict[str, object] = {}
        self.sparse_vector_configs: dict[str, object] = {}
        self.payload_indexes: dict[str, dict[str, object]] = {}
        self.fail_upsert = False
        self.fail_point_id: int | None = None
        self.last_query: dict[str, object] | None = None

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def get_collections(self) -> SimpleNamespace:
        return SimpleNamespace(
            collections=[
                SimpleNamespace(name=name) for name in self.collections
            ]
        )

    def create_collection(
        self,
        collection_name: str,
        vectors_config: object = None,
        sparse_vectors_config: object = None,
    ) -> bool:
        self.collections[collection_name] = {}
        self.vector_configs[collection_name] = vectors_config
        self.sparse_vector_configs[collection_name] = sparse_vectors_config
        self.payload_indexes[collection_name] = {}
        return True

    def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_schema: object,
    ) -> bool:
        self.payload_indexes.setdefault(collection_name, {})[field_name] = field_schema
        return True

    def upsert(
        self,
        collection_name: str,
        points: list[models.PointStruct],
        wait: bool = True,
    ) -> None:
        if self.fail_upsert:
            raise UnexpectedResponse(
                status_code=503,
                reason_phrase="Service Unavailable",
                content=b"Qdrant is unavailable",
                headers=Headers(),
            )
        collection = self.collections[collection_name]
        for point in points:
            if point.id == self.fail_point_id:
                raise UnexpectedResponse(
                    status_code=503,
                    reason_phrase="Service Unavailable",
                    content=b"Qdrant rejected this point",
                    headers=Headers(),
                )
            collection[point.id] = point

    def get_collection(self, collection_name: str) -> SimpleNamespace:
        points = self.collections[collection_name]
        return SimpleNamespace(points_count=len(points), status="green")

    def query_points(self, **kwargs: object) -> SimpleNamespace:
        self.last_query = kwargs
        return SimpleNamespace(points=[])

    def delete_collection(self, collection_name: str) -> bool:
        self.collections.pop(collection_name, None)
        return True


class MockDenseMatrix:
    def __init__(self, rows: list[list[float]]) -> None:
        self._rows = rows

    def tolist(self) -> list[list[float]]:
        return self._rows


class MockBGEM3FlagModel:
    """Lightweight mock replacing BGEM3FlagModel in unit tests."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def encode(
        self,
        texts: list[str],
        batch_size: int = 64,
        return_dense: bool = True,
        return_sparse: bool = False,
        return_colbert_vecs: bool = False,
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        if return_dense:
            result["dense_vecs"] = MockDenseMatrix(
                [[float(len(text))] * config.dense_dim for text in texts]
            )
        if return_sparse:
            result["lexical_weights"] = [
                {"1": 0.5, "2": 0.05} for _ in texts
            ]
        return result


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
        embedder_module,
        "BGEM3FlagModel",
        MockBGEM3FlagModel,
    )
    return Indexer()


def test_index_movies_with_force_reindex_removes_existing_collection(
    tmp_path: Path,
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    movie = make_movie_card(movie_id=1, title="Movie")
    filepath = tmp_path / "movies.jsonl"
    filepath.write_text(movie.model_dump_json() + "\n", encoding="utf-8")

    # First indexing
    indexer.index_movies(filepath)
    assert indexer.get_stats().points_count == 1

    # Second indexing with force_recreate=True
    indexer.index_movies(filepath, force_recreate=True)
    stats: IndexerStats = indexer.get_stats()
    assert stats.points_count == 1  # Should still be 1 after reindexing


def test_embed_request_generates_plot_vibe_and_sparse_embeddings(
    indexer: Indexer,
) -> None:
    response = indexer.embedder.embed_request(
        ParsedText(
            plot="A detective investigates",
            vibe="dark and tense",
            entities="Sherlock Holmes",
        )
    )

    assert response.embedding_names == ["plot", "vibe"]
    assert response.embeddings == [
        [float(len("A detective investigates"))] * config.dense_dim,
        [float(len("dark and tense"))] * config.dense_dim,
    ]
    assert response.sparse_vector is not None
    assert response.sparse_vector.indices == [1]
    assert response.sparse_vector.values == [0.5]
    assert response.year_range == (0, 0)
    assert response.rating_range == (0.0, 0.0)


def test_embed_request_passes_year_and_rating_filters(indexer: Indexer) -> None:
    response = indexer.embedder.embed_request(
        ParsedText(
            plot="A detective investigates",
            vibe=None,
            entities=None,
            filter={
                "year_gte": 1990,
                "rating_gte": 7.5,
                "rating_lte": 9.0,
            },
        )
    )

    assert response.year_range == (1990, 0)
    assert response.rating_range == (7.5, 9.0)


def test_get_points_does_not_apply_unset_filters(
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    response = EmbedderResponse(
        embeddings=[],
        model="test",
        sparse_vector=SparseVectorData(indices=[1], values=[0.5]),
    )

    indexer.repo.get_points(response)

    assert qdrant_client.last_query is not None
    assert qdrant_client.last_query["query_filter"] is None


def test_get_points_applies_only_year_and_rating_bounds(
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    response = EmbedderResponse(
        embeddings=[],
        model="test",
        sparse_vector=SparseVectorData(indices=[1], values=[0.5]),
        year_range=(1990, 0),
        rating_range=(0.0, 8.5),
    )

    indexer.repo.get_points(response)

    assert qdrant_client.last_query is not None
    query_filter = qdrant_client.last_query["query_filter"]
    assert isinstance(query_filter, models.Filter)
    assert query_filter.must is not None
    assert [
        (condition.key, condition.range.gte, condition.range.lte)
        for condition in query_filter.must
    ] == [("year", 1990, None), ("rating", None, 8.5)]


def test_embed_request_without_text_returns_empty_vectors(indexer: Indexer) -> None:
    response = indexer.embedder.embed_request(
        ParsedText(plot=None, vibe=None, entities=None)
    )

    assert response.embeddings == []
    assert response.embedding_names == []
    assert response.sparse_vector is not None
    assert response.sparse_vector.indices == []
    assert response.sparse_vector.values == []


def test_create_collection_with_existing_collection_does_not_fail(
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    # Create collection first time
    indexer.create_collection()
    assert indexer.get_stats().points_count == 0
    assert set(qdrant_client.payload_indexes["movies"]) == {"year", "rating"}

    # Create collection again, should not fail
    indexer.create_collection()
    assert indexer.get_stats().points_count == 0


def test_indexing_with_unexisting_file_raises_exception(
    indexer: Indexer,
) -> None:
    non_existent_file = Path("non_existent_file.jsonl")
    with pytest.raises(FileNotFoundError):
        indexer.index_movies(non_existent_file)


def test_indexing_with_invalid_jsonl_file_raises_exception(
    tmp_path: Path,
    indexer: Indexer,
) -> None:
    invalid_jsonl_file = tmp_path / "invalid.jsonl"
    invalid_jsonl_file.write_text("invalid json\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        indexer.index_movies(invalid_jsonl_file)


def test_indexing_raises_when_qdrant_returns_server_error(
    tmp_path: Path,
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    movie = make_movie_card(movie_id=1, title="Movie")
    filepath = tmp_path / "movies.jsonl"
    filepath.write_text(movie.model_dump_json() + "\n", encoding="utf-8")
    qdrant_client.fail_upsert = True

    with pytest.raises(RuntimeError, match="Failed to index 1 of 1 movies"):
        indexer.index_movies(filepath)

    assert qdrant_client.collections[indexer.collection_name] == {}


def test_indexing_isolates_qdrant_error_for_random_point(
    tmp_path: Path,
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    movies = [
        make_movie_card(movie_id=movie_id, title=f"Movie {movie_id}")
        for movie_id in range(4)
    ]
    filepath = tmp_path / "movies.jsonl"
    filepath.write_text(
        "".join(movie.model_dump_json() + "\n" for movie in movies),
        encoding="utf-8",
    )
    failed_point_id = random.randint(0, len(movies) - 1)
    qdrant_client.fail_point_id = failed_point_id

    with pytest.raises(RuntimeError, match="Failed to index 1 of 4 movies"):
        indexer.index_movies(filepath, batch_size=len(movies))

    stored_ids = set(qdrant_client.collections[indexer.collection_name])
    assert stored_ids == {movie.id for movie in movies} - {
        failed_point_id
    }


def test_batch_indexing_with_large_file(
    create_jsonl_file_with_200_movies_for_batching: Path,
    indexer: Indexer,
    qdrant_client: MockQdrantClient,
) -> None:
    filepath = create_jsonl_file_with_200_movies_for_batching
    indexer.index_movies(filepath)
    stats: IndexerStats = indexer.get_stats()
    assert stats.points_count == 200
