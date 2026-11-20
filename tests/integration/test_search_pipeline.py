"""Integration tests for the search pipeline."""

from src.core.contracts import Movie
from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.schemas import IndexedMoviePoint, SparseVectorData
from src.services.search_service.parsing.text_parser import TextParser
from src.services.search_service.schemas import SearchQuery
from src.services.search_service.search_service import SearchService


def test_search_runs_parser_qdrant_and_reranker(
    qdrant_repo: QdrantRepository,
    fake_embedder,
    fake_reranker,
) -> None:
    movie = Movie(
        id=42,
        title="Космическое путешествие",
        year=2024,
        description="История о путешествии к далёкой планете.",
        genres=["фантастика"],
    )
    point = IndexedMoviePoint(
        point_id=movie.id,
        plot_vector=[1.0] + [0.0] * (qdrant_repo.dense_dim - 1),
        sparse_vector=SparseVectorData(indices=[0], values=[1.0]),
        payload=movie,
    )
    assert qdrant_repo.upsert_points([point]) == (1, 0)

    service = SearchService(
        parser=TextParser(),
        embedder=fake_embedder,
        qdrant_repo=qdrant_repo,
        reranker=fake_reranker,
    )

    response = service.search(SearchQuery(text="фильм про космос", top_k=5))

    assert len(response.documents) == 1
    assert response.documents[0]["id"] == movie.id
    assert response.documents[0]["title"] == movie.title
    assert response.documents[0]["score"] == 1.0
