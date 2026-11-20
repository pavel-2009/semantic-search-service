"""Integration tests for loading and indexing movie JSONL data."""

import json
from pathlib import Path

import pytest

import src.services.indexer.indexer as indexer_module
from src.core.config import settings
from src.core.contracts import EnrichedMovie, MovieIndexData
from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.indexer import Indexer


@pytest.fixture
def indexer(
    qdrant_repo: QdrantRepository,
    fake_embedder,
    monkeypatch: pytest.MonkeyPatch,
) -> Indexer:
    monkeypatch.setattr(settings, "QDRANT_COLLECTION", qdrant_repo.collection_name)
    monkeypatch.setattr(indexer_module, "MovieEmbedder", lambda **_: fake_embedder)
    return Indexer()


def test_indexer_reads_validates_and_stores_jsonl(
    tmp_path: Path,
    indexer: Indexer,
    qdrant_repo: QdrantRepository,
) -> None:
    movie = EnrichedMovie(
        id=42,
        title="Космическое путешествие",
        year=2024,
        description="История о путешествии к далёкой планете.",
        genres=["фантастика"],
        indexing=MovieIndexData(
            plot="История о путешествии к далёкой планете.",
            vibe="захватывающий",
            entities="планета. космическое путешествие",
        ),
    )
    filepath = tmp_path / "movies.jsonl"
    jsonl = json.dumps(movie.model_dump(mode="json"), ensure_ascii=False) + "\n"
    filepath.write_text(jsonl, encoding="utf-8")

    loaded_movies = list(indexer.load_movies(filepath))
    assert len(loaded_movies) == 1
    assert isinstance(loaded_movies[0], EnrichedMovie)
    assert loaded_movies[0].indexing.plot == movie.indexing.plot

    indexer.index_movies(filepath, batch_size=1, force_recreate=True)

    assert indexer.get_stats().points_count == 1
    stored = qdrant_repo.client.retrieve(
        collection_name=qdrant_repo.collection_name,
        ids=[movie.id],
        with_payload=True,
    )
    assert len(stored) == 1
    assert stored[0].payload is not None
    assert stored[0].payload["title"] == movie.title
    assert stored[0].payload["year"] == movie.year
    assert "indexing" not in stored[0].payload
