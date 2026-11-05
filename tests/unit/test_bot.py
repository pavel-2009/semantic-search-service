"""Unit tests for Telegram bot routers."""

from importlib import import_module
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Bot
from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, Message

from backend.schemas import MovieResult, SearchRequest
from bot.main import start

info_router = import_module("bot.routers.info_router")
search_router = import_module("bot.routers.search_router")


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
        director="Кристофер Нолан",
        actors=["Мэттью Макконахи"],
        description="Путешествие через космос и время.",
        score=0.95,
    )


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
    service = Mock()
    service.search.return_value = [movie]
    monkeypatch.setattr(search_router, "get_search_service", lambda: service)

    command = CommandObject(args="  фильмы про космос  ")
    await search_router.search_movies(mock_message, command)

    service.search.assert_called_once_with(
        SearchRequest(query="фильмы про космос", top_k=10, filters=None)
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
    service = Mock()
    if raises:
        service.search.side_effect = RuntimeError("search failed")
    else:
        service.search.return_value = results
    monkeypatch.setattr(search_router, "get_search_service", lambda: service)
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
    service = Mock()
    service.get_by_id.return_value = movie
    monkeypatch.setattr(info_router, "get_service", lambda: service)
    callback = Mock(spec=CallbackQuery)
    callback.data = "movie:42"
    callback.message = mock_message
    callback.answer = AsyncMock()

    await info_router.show_movie_details(callback)

    service.get_by_id.assert_called_once_with(42)
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
    service = Mock()
    service.get_by_id.return_value = result
    monkeypatch.setattr(info_router, "get_service", lambda: service)
    callback = Mock(spec=CallbackQuery)
    callback.data = callback_data
    callback.message = mock_message
    callback.answer = AsyncMock()

    await info_router.show_movie_details(callback)

    callback.answer.assert_awaited_once()
    assert expected_text in callback.answer.await_args.args[0]
    mock_bot.send_message.assert_not_awaited()
