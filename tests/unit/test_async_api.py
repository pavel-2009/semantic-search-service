"""Unit tests for blocking work in asynchronous API routes."""

from threading import get_ident
from types import SimpleNamespace

import pytest

from backend.api.info_router import get_movie, get_stats, health_check
from backend.api.search_router import search
from backend.schemas import MovieResult, SearchRequest, StatsResponse


@pytest.mark.asyncio
async def test_sync_service_calls_run_outside_event_loop_thread():
    event_loop_thread = get_ident()
    worker_threads: set[int] = set()

    def operation(result):
        def run(*_args):
            worker_threads.add(get_ident())
            return result

        return run

    stats = StatsResponse(
        collection="movies",
        total_points=1,
        status="green",
        model="test-model",
        embedding_dim=384,
    )
    movie = MovieResult(id=1, title="Movie", score=0.0)
    service = SimpleNamespace(
        collection_name="movies",
        search=operation([]),
        get_stats=operation(stats),
        get_by_id=operation(movie),
    )

    await search(SearchRequest(query="movie"), service)
    await health_check(service)
    await get_movie(1, service)
    await get_stats(service)

    assert worker_threads
    assert event_loop_thread not in worker_threads
