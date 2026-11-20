"""Integration tests for the QdrantRepository class."""

from src.core.contracts import Movie
from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.schemas import IndexedMoviePoint, SparseVectorData


def test_create_collection(qdrant_repo: QdrantRepository) -> None:
    """Verify that the collection has the expected named-vector configuration."""
    qdrant_repo.create_collection()

    collection_info = qdrant_repo.client.get_collection(qdrant_repo.collection_name)
    vectors = collection_info.config.params.vectors

    assert collection_info.status.value == "green"
    assert vectors["plot"].size == qdrant_repo.dense_dim
    assert vectors["vibe"].size == qdrant_repo.dense_dim


def test_recreate_collection(qdrant_repo: QdrantRepository) -> None:
    """Verify that recreating a collection removes its existing points."""
    point = IndexedMoviePoint(
        point_id=1,
        plot_vector=[1.0] + [0.0] * (qdrant_repo.dense_dim - 1),
        sparse_vector=SparseVectorData(indices=[1], values=[1.0]),
        payload=Movie(id=1, title="Test movie"),
    )
    assert qdrant_repo.upsert_points([point]) == (1, 0)
    assert qdrant_repo.client.retrieve(
        collection_name=qdrant_repo.collection_name,
        ids=[point.point_id],
    )

    qdrant_repo.recreate_collection()

    assert qdrant_repo.client.retrieve(
        collection_name=qdrant_repo.collection_name,
        ids=[point.point_id],
    ) == []
