"""Integration tests for indexing and search with real Qdrant."""

from backend.schemas import RatingFilter, SearchFilters, SearchRequest, YearFilter
from backend.services.search_service import SearchService
from services.indexer import Indexer


def test_index_and_search_roundtrip(indexed_integration):
    """Indexing makes movies available for semantic search."""
    client, collection_name = indexed_integration
    service = SearchService()

    results = service.search(SearchRequest(query="dream technology", top_k=2))

    assert results
    assert results[0].title == "Inception"
    assert client.get_collection(collection_name).points_count == 3


def test_search_with_filters(indexed_integration):
    """Search respects year and rating filters."""
    indexed_integration
    service = SearchService()
    request = SearchRequest(
        query="space",
        top_k=3,
        filters=SearchFilters(
            year=YearFilter(gte=2010),
            rating=RatingFilter(gte=8.5),
        ),
    )

    results = service.search(request)

    assert results
    assert all(movie.year >= 2010 and movie.rating >= 8.5 for movie in results)


def test_get_movie_by_id(indexed_integration):
    """Indexed movies can be retrieved by ID."""
    indexed_integration
    service = SearchService()

    movie = service.get_by_id(1)

    assert movie is not None
    assert movie.id == 1
    assert movie.title == "Inception"
    assert movie.year == 2010
    assert movie.director == "Christopher Nolan"
    assert service.get_by_id(999) is None


def test_indexer_stats(indexed_integration):
    """Indexer reports the state of the indexed collection."""
    _, collection_name = indexed_integration
    indexer = Indexer()

    stats = indexer.get_stats()

    assert stats["collection"] == collection_name
    assert stats["points_count"] == 3
    assert stats["status"] == "green"
