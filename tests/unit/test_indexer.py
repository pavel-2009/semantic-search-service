"""Unit tests for Indexer."""

from pathlib import Path
from unittest.mock import ANY, Mock

import pytest

from core.config import settings
from scraper.schemas import Movie
from services.indexer import Indexer


def test_initialization(mock_qdrant_client, mock_embedding_model):
    indexer = Indexer()
    assert indexer.collection_name == settings.QDRANT_COLLECTION
    assert indexer.embedding_dim == settings.EMBEDDING_DIM
    assert indexer.qdrant is mock_qdrant_client
    assert indexer.model is mock_embedding_model


@pytest.mark.parametrize(
    ("movie", "expected"),
    [
        (
            Movie(
                id=1,
                title="Inception",
                description="A thief who steals corporate secrets",
                director="Christopher Nolan",
                country="USA",
                year=2010,
                rating=8.8,
                actors=["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
                genres=["sci-fi", "thriller"],
            ),
            [
                "название: inception", "описание: a thief who steals corporate secrets",
                "режиссёр: christopher nolan", "страна: usa", "год: 2010",
                "рейтинг: 8.8", "актёры: leonardo dicaprio", "жанры: sci-fi",
            ],
        ),
        (Movie(id=1, title="Unknown"), ["название unknown"]),
        (Movie(id=1), ["фильм без описания"]),
    ],
)
def test_prepare_text(movie, expected):
    text = Indexer().prepare_text(movie).lower()
    assert all(fragment in text for fragment in expected)


def test_normalize_movie_accepts_legacy_contract():
    movie = Movie.model_validate(
        {"id": 1, "name": "Inception", "country": "USA, UK", "tags": ["sci-fi", "thriller"]}
    )
    normalized = Indexer()._normalize_movie(movie)
    assert normalized.title == "Inception"
    assert normalized.genres == ["sci-fi", "thriller"]


def test_load_movies(temp_json_file):
    movies = Indexer().load_movies(temp_json_file)
    assert [movie.id for movie in movies] == [1, 2]


def test_index_movies_upserts_existing_movie_with_updated_fields(
    tmp_path, mock_qdrant_client, mock_embedding_model
):
    path = tmp_path / "movies.json"
    path.write_text(
        '[{"id": 1, "title": "Inception", "description": "Updated description"}]',
        encoding="utf-8",
    )

    Indexer().index_movies(path, batch_size=1)

    points = mock_qdrant_client.upsert.call_args.kwargs["points"]
    assert len(points) == 1
    assert points[0].id == 1
    assert points[0].payload["description"] == "Updated description"
    mock_qdrant_client.scroll.assert_not_called()
    mock_embedding_model.encode.assert_called_once()


def test_index_movies_continues_after_movie_processing_failure(
    tmp_path, mock_qdrant_client, mock_embedding_model
):
    path = tmp_path / "movies.json"
    path.write_text('[{"id": 1}, {"id": 2}]', encoding="utf-8")
    mock_embedding_model.encode.side_effect = [
        RuntimeError("embedding failed"),
        mock_embedding_model.encode.return_value,
    ]

    with pytest.raises(RuntimeError, match="Failed to index 1 of 2 movies"):
        Indexer().index_movies(path, batch_size=1)

    mock_qdrant_client.upsert.assert_called_once()
    assert mock_qdrant_client.upsert.call_args.kwargs["points"][0].id == 2


def test_index_movies_retries_failed_batch_per_movie(
    tmp_path, mock_qdrant_client
):
    path = tmp_path / "movies.json"
    path.write_text('[{"id": 1}, {"id": 2}]', encoding="utf-8")
    mock_qdrant_client.upsert.side_effect = [
        RuntimeError("batch failed"),
        None,
        RuntimeError("movie failed"),
    ]

    with pytest.raises(RuntimeError, match="Failed to index 1 of 2 movies"):
        Indexer().index_movies(path, batch_size=2)

    assert [
        [point.id for point in call.kwargs["points"]]
        for call in mock_qdrant_client.upsert.call_args_list
    ] == [[1, 2], [1], [2]]


def test_load_movies_file_not_found():
    with pytest.raises(FileNotFoundError):
        Indexer().load_movies(Path("/nonexistent/file.json"))


def test_load_movies_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"not": "a list"}')
    with pytest.raises(ValueError):
        Indexer().load_movies(path)


def test_create_collection_new(mock_qdrant_client):
    mock_qdrant_client.get_collections.return_value.collections = []
    Indexer().create_collection()
    mock_qdrant_client.create_collection.assert_called_once()


def test_create_collection_exists(mock_qdrant_client):
    collection_mock = Mock()
    collection_mock.name = settings.QDRANT_COLLECTION
    mock_qdrant_client.get_collections.return_value.collections = [collection_mock]
    Indexer().create_collection()
    mock_qdrant_client.create_collection.assert_not_called()


def test_create_collection_force_recreate(mock_qdrant_client):
    collection_mock = Mock()
    collection_mock.name = settings.QDRANT_COLLECTION
    mock_qdrant_client.get_collections.return_value.collections = [collection_mock]
    Indexer().create_collection(force_recreate=True)
    mock_qdrant_client.delete_collection.assert_called_once_with(settings.QDRANT_COLLECTION)
    mock_qdrant_client.create_collection.assert_called_once_with(
        collection_name=settings.QDRANT_COLLECTION, vectors_config=ANY
    )


def test_clear_collection(mock_qdrant_client):
    Indexer().clear_collection()
    mock_qdrant_client.delete_collection.assert_called_once_with(settings.QDRANT_COLLECTION)


def test_get_stats(mock_qdrant_client):
    stats = Indexer().get_stats()
    assert stats.collection == settings.QDRANT_COLLECTION
    assert stats.points_count == 100
    assert stats.status == "green"
