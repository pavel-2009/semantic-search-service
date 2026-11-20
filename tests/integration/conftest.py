from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from src.backend.main import app
from src.core.contracts import EnrichedMovie, Movie
from src.core.dependencies import get_qdrant_repository, get_search_service
from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.schemas import IndexedMoviePoint, SparseVectorData
from src.services.search_service.embedder.schemas import EmbedderResponse
from src.services.search_service.parsing.text_parser import ParsedText, TextParser
from src.services.search_service.ranking.schemas import RerankingRequest, RerankingResponse
from src.services.search_service.search_service import SearchService


class FakeEmbedder:
    """Return deterministic vectors without loading BGE-M3."""

    def __init__(self, dense_dim: int = 1024) -> None:
        self.dense_dim = dense_dim

    def embed_cards(self, cards: list[EnrichedMovie]) -> list[IndexedMoviePoint]:
        dense_vector = [1.0] + [0.0] * (self.dense_dim - 1)
        return [
            IndexedMoviePoint(
                point_id=card.id,
                plot_vector=dense_vector.copy() if card.indexing.plot else None,
                vibe_vector=dense_vector.copy() if card.indexing.vibe else None,
                sparse_vector=SparseVectorData(indices=[0], values=[1.0]),
                payload=card.to_movie_payload(),
            )
            for card in cards
        ]

    def embed_request(self, parsed_query: ParsedText) -> EmbedderResponse:
        dense_names = [
            name
            for name, text in (("plot", parsed_query.plot), ("vibe", parsed_query.vibe))
            if text and text.strip()
        ]
        dense_vector = [1.0] + [0.0] * (self.dense_dim - 1)
        filters = parsed_query.filter or {}
        sparse_vector = (
            SparseVectorData(indices=[0], values=[1.0])
            if parsed_query.entities
            else SparseVectorData(indices=[], values=[])
        )

        return EmbedderResponse(
            embeddings=[dense_vector.copy() for _ in dense_names],
            embedding_names=dense_names,
            sparse_vector=sparse_vector,
            model="fake-embedder",
            year_range=(
                int(filters.get("year_gte", 0)),
                int(filters.get("year_lte", 0)),
            ),
            rating_range=(
                float(filters.get("rating_gte", 0)),
                float(filters.get("rating_lte", 0)),
            ),
        )


class FakeReranker:
    """Assign predictable scores without loading a CrossEncoder."""

    def rerank(self, request: RerankingRequest, top_k: int) -> RerankingResponse:
        documents = []
        for index, point in enumerate(request.documents):
            document = dict(point.payload or {})
            document.setdefault("id", point.id)
            document["score"] = float(len(request.documents) - index)
            documents.append(document)
        return RerankingResponse(reranked_documents=documents[:top_k])


@pytest.fixture
def fake_embedder(qdrant_repo: QdrantRepository) -> FakeEmbedder:
    """Provide deterministic embeddings sized for the test collection."""
    return FakeEmbedder(dense_dim=qdrant_repo.dense_dim)


@pytest.fixture
def fake_reranker() -> FakeReranker:
    """Provide deterministic reranking without loading a CrossEncoder."""
    return FakeReranker()


@pytest.fixture
def api_dependencies(
    qdrant_repo: QdrantRepository,
    fake_embedder: FakeEmbedder,
    fake_reranker: FakeReranker,
    monkeypatch: pytest.MonkeyPatch,
) -> SearchService:
    """Override API dependencies with the in-memory repository and fake models."""
    fake_service = SearchService(
        parser=TextParser(),
        embedder=fake_embedder,
        qdrant_repo=qdrant_repo,
        reranker=fake_reranker,
    )
    monkeypatch.setitem(app.dependency_overrides, get_qdrant_repository, lambda: qdrant_repo)
    monkeypatch.setitem(app.dependency_overrides, get_search_service, lambda: fake_service)
    monkeypatch.setattr("src.backend.main.get_qdrant_repository", lambda: qdrant_repo)
    return fake_service


@pytest.fixture
def seeded_movie(qdrant_repo: QdrantRepository) -> Movie:
    """Insert one representative movie for API and bot end-to-end tests."""
    movie = Movie(
        id=42,
        title="Космическое путешествие",
        year=2024,
        rating=8.4,
        genres=["фантастика", "приключения"],
        countries=["Россия"],
        description="История о путешествии к далёкой планете.",
    )
    point = IndexedMoviePoint(
        point_id=movie.id,
        plot_vector=[1.0] + [0.0] * (qdrant_repo.dense_dim - 1),
        sparse_vector=SparseVectorData(indices=[0], values=[1.0]),
        payload=movie,
    )
    assert qdrant_repo.upsert_points([point]) == (1, 0)
    return movie


@pytest.fixture(scope="session")
def qdrant_client() -> Iterator[QdrantClient]:
    """Provide an in-memory Qdrant client shared by integration tests."""
    client = QdrantClient(":memory:")
    yield client
    client.close()


@pytest.fixture
def qdrant_repo(
    qdrant_client: QdrantClient,
    monkeypatch: pytest.MonkeyPatch,
) -> QdrantRepository:
    """Create an isolated test collection backed by the in-memory client."""
    monkeypatch.setattr(
        "src.core.qdrant_client.QdrantClientSingleton.get_client",
        lambda: qdrant_client,
    )
    repository = QdrantRepository(collection_name="test_movies", dense_dim=1024)
    repository.recreate_collection()
    return repository


@pytest.fixture
def api_client(
    api_dependencies: SearchService,
) -> Iterator[TestClient]:
    """Provide a test API client with model-free search dependencies."""
    with TestClient(app) as client:
        yield client
