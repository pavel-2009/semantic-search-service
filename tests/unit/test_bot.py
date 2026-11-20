"""Unit tests for Telegram bot routers."""

from importlib import import_module
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Bot
from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, Message

from src.backend.schemas import MovieResult
from src.bot.api_client import SearchApiClient
from src.bot.main import start

info_router = import_module("src.bot.routers.info_router")
search_router = import_module("src.bot.routers.search_router")


@pytest.fixture
def mock_bot() -> AsyncMock:
    """Provide a bot mock for verifying messages sent by handlers."""
    return AsyncMock(spec=Bot)


@pytest.fixture
def mock_message(mock_bot: AsyncMock) -> AsyncMock:
    message = AsyncMock(spec=Message)
    message.answer = mock_bot.send_message
    return message


@pytest.fixture
def movie() -> MovieResult:
    return MovieResult(
        id=42,
        title="Интерстеллар",
        year=2014,
        rating=8.7,
        genres=["фантастика", "драма"],
        countries=["США", "Великобритания"],
        description="Путешествие через космос и время.",
        score=0.95,
    )


@pytest.mark.asyncio
async def test_bot_api_client_search_parses_api_results(movie: MovieResult) -> None:
    response = Mock()
    response.json.return_value = {"results": [movie.model_dump()]}
    response.raise_for_status = Mock()
    http_client = Mock()
    http_client.post = AsyncMock(return_value=response)

    client = SearchApiClient(http_client=http_client)

    results = await client.search("фильмы про космос", top_k=10)

    assert results == [movie]
    http_client.post.assert_awaited_once_with(
        "/api/v1/search",
        json={"query": "фильмы про космос", "top_k": 10},
    )
    response.raise_for_status.assert_called_once_with()


@pytest.mark.asyncio
async def test_bot_api_client_returns_none_for_missing_movie() -> None:
    response = Mock(status_code=404)
    http_client = Mock()
    http_client.get = AsyncMock(return_value=response)

    client = SearchApiClient(http_client=http_client)

    assert await client.get_movie(999) is None
    http_client.get.assert_awaited_once_with("/api/v1/movies/999")


@pytest.mark.asyncio
async def test_start_sends_welcome_message(
    mock_bot: AsyncMock, mock_message: AsyncMock
) -> None:
    await start(mock_message)

    mock_bot.send_message.assert_awaited_once()
    sent_text = mock_bot.send_message.await_args.args[0]
    assert "Семантический поиск фильмов" in sent_text


@pytest.mark.asyncio
async def test_search_command_sends_results_and_detail_buttons(
    mock_bot: AsyncMock,
    mock_message: AsyncMock,
    movie: MovieResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    client.search = AsyncMock(return_value=[movie])
    monkeypatch.setattr(search_router, "api_client", client)

    command = CommandObject(args="  фильмы про космос  ")
    await search_router.search_movies(mock_message, command)

    client.search.assert_awaited_once_with(
        query="фильмы про космос",
        top_k=10,
    )
    mock_bot.send_message.assert_awaited_once()
    sent = mock_bot.send_message.await_args.kwargs
    assert "Интерстеллар" in sent["text"]
    assert sent["reply_markup"].inline_keyboard[0][0].callback_data == "movie:42"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_text"),
    [
        (" ", "Слишком короткий запрос"),
        ("x" * 501, "Слишком длинный запрос"),
    ],
)
async def test_search_rejects_invalid_query_length(
    query: str,
    expected_text: str,
    mock_bot: AsyncMock,
    mock_message: AsyncMock,
) -> None:
    mock_message.text = query

    await search_router.search_by_text(mock_message)

    mock_bot.send_message.assert_awaited_once()
    assert expected_text in mock_bot.send_message.await_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("results", "raises", "expected_text"),
    [
        ([], False, "Ничего не найдено"),
        (None, True, "Не удалось выполнить поиск"),
    ],
)
async def test_search_handles_empty_results_and_service_errors(
    results: list[MovieResult] | None,
    raises: bool,
    expected_text: str,
    mock_bot: AsyncMock,
    mock_message: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    if raises:
        client.search = AsyncMock(side_effect=RuntimeError("search failed"))
    else:
        client.search = AsyncMock(return_value=results)
    monkeypatch.setattr(search_router, "api_client", client)
    mock_message.text = "космос"

    await search_router.search_by_text(mock_message)

    mock_bot.send_message.assert_awaited_once()
    assert expected_text in mock_bot.send_message.await_args.args[0]


@pytest.mark.asyncio
async def test_movie_details_callback_sends_movie_information(
    mock_bot: AsyncMock,
    mock_message: AsyncMock,
    movie: MovieResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    client.get_movie = AsyncMock(return_value=movie)
    monkeypatch.setattr(info_router, "api_client", client)
    callback = Mock(spec=CallbackQuery)
    callback.data = "movie:42"
    callback.message = mock_message
    callback.answer = AsyncMock()

    await info_router.show_movie_details(callback)

    client.get_movie.assert_awaited_once_with(42)
    callback.answer.assert_awaited_once_with()
    mock_bot.send_message.assert_awaited_once()
    assert "Интерстеллар" in mock_bot.send_message.await_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_data", "result", "expected_text"),
    [
        ("movie:invalid", None, "Некорректный идентификатор"),
        ("movie:99", None, "Фильм не найден"),
    ],
)
async def test_movie_details_callback_reports_invalid_or_missing_movie(
    callback_data: str,
    result: MovieResult | None,
    expected_text: str,
    mock_bot: AsyncMock,
    mock_message: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    client.get_movie = AsyncMock(return_value=result)
    monkeypatch.setattr(info_router, "api_client", client)
    callback = Mock(spec=CallbackQuery)
    callback.data = callback_data
    callback.message = mock_message
    callback.answer = AsyncMock()

    await info_router.show_movie_details(callback)

    callback.answer.assert_awaited_once()
    assert expected_text in callback.answer.await_args.args[0]
    mock_bot.send_message.assert_not_awaited()
