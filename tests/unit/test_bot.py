"""Tests for Telegram bot handlers with a mocked search service."""

import importlib
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup

from backend.schemas import MovieResult, SearchRequest

search_handlers = importlib.import_module("bot.routers.search_router")
info_handlers = importlib.import_module("bot.routers.info_router")


@pytest.fixture
def movie() -> MovieResult:
    return MovieResult(
        id=42,
        title="Интерстеллар <тест>",
        year=2014,
        rating=8.7,
        genres=["фантастика", "драма"],
        countries=["США", "Великобритания"],
        director="Кристофер Нолан",
        actors=["Мэттью Макконахи"],
        description="Путешествие через космос и время.",
        score=0.95,
    )


@pytest.fixture
def search_service(monkeypatch: pytest.MonkeyPatch) -> Mock:
    service = Mock()
    monkeypatch.setattr(search_handlers, "get_search_service", lambda: service)
    monkeypatch.setattr(info_handlers, "get_service", lambda: service)
    return service


@pytest.mark.asyncio
async def test_search_by_text_returns_formatted_results(
    movie: MovieResult,
    search_service: Mock,
) -> None:
    search_service.search.return_value = [movie]
    message = Mock(text="  фильмы про космос  ")
    message.answer = AsyncMock()

    await search_handlers.search_by_text(message)

    search_service.search.assert_called_once_with(
        SearchRequest(query="фильмы про космос", top_k=10, filters=None)
    )
    message.answer.assert_awaited_once()
    answer = message.answer.await_args.kwargs
    assert "Результаты поиска" in answer["text"]
    assert "Интерстеллар &lt;тест&gt;" in answer["text"]
    assert answer["parse_mode"] == ParseMode.HTML
    assert isinstance(answer["reply_markup"], InlineKeyboardMarkup)
    assert answer["reply_markup"].inline_keyboard[0][0].callback_data == "movie:42"


@pytest.mark.asyncio
async def test_search_returns_message_for_no_results(search_service: Mock) -> None:
    search_service.search.return_value = []
    message = Mock(text="неизвестный фильм")
    message.answer = AsyncMock()

    await search_handlers.search_by_text(message)

    message.answer.assert_awaited_once_with(
        "🔎 <b>Ничего не найдено.</b>\nПопробуй изменить запрос.",
        parse_mode=ParseMode.HTML,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_text"),
    [
        (" ", "❌ Слишком короткий запрос. Напиши хотя бы 2 символа."),
        ("x" * 501, "❌ Слишком длинный запрос. Максимум 500 символов."),
    ],
)
async def test_search_rejects_invalid_query(
    query: str,
    expected_text: str,
    search_service: Mock,
) -> None:
    message = Mock(text=query)
    message.answer = AsyncMock()

    await search_handlers.search_by_text(message)

    search_service.search.assert_not_called()
    message.answer.assert_awaited_once_with(expected_text, parse_mode=ParseMode.HTML)


@pytest.mark.asyncio
async def test_search_returns_error_message_when_service_fails(search_service: Mock) -> None:
    search_service.search.side_effect = RuntimeError("search failed")
    message = Mock(text="фильм")
    message.answer = AsyncMock()

    await search_handlers.search_by_text(message)

    message.answer.assert_awaited_once_with(
        "❌ <b>Не удалось выполнить поиск.</b>\nПопробуй ещё раз.",
        parse_mode=ParseMode.HTML,
    )


def test_search_results_keyboard_contains_movie_callback(movie: MovieResult) -> None:
    keyboard = search_handlers.search_results_keyboard([movie])

    assert keyboard.inline_keyboard[0][0].text == "Подробнее · 1"
    assert keyboard.inline_keyboard[0][0].callback_data == "movie:42"


@pytest.mark.asyncio
async def test_movie_callback_returns_formatted_details(
    movie: MovieResult,
    search_service: Mock,
) -> None:
    search_service.get_by_id.return_value = movie
    callback = Mock(data="movie:42", message=Mock())
    callback.answer = AsyncMock()
    callback.message.answer = AsyncMock()

    await info_handlers.show_movie_details(callback)

    search_service.get_by_id.assert_called_once_with(42)
    callback.answer.assert_awaited_once_with()
    callback.message.answer.assert_awaited_once()
    answer = callback.message.answer.await_args
    assert "Интерстеллар &lt;тест&gt;" in answer.args[0]
    assert "Кристофер Нолан" in answer.args[0]
    assert answer.kwargs["parse_mode"] == ParseMode.HTML


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_data", "service_result", "expected_text"),
    [
        ("movie:invalid", None, "Некорректный идентификатор фильма."),
        ("movie:999", None, "Фильм не найден."),
    ],
)
async def test_movie_callback_returns_alert_for_invalid_or_missing_movie(
    callback_data: str,
    service_result: MovieResult | None,
    expected_text: str,
    search_service: Mock,
) -> None:
    search_service.get_by_id.return_value = service_result
    callback = Mock(data=callback_data, message=Mock(answer=AsyncMock()))
    callback.answer = AsyncMock()

    await info_handlers.show_movie_details(callback)

    callback.answer.assert_awaited_once_with(
        expected_text,
        show_alert=True,
        parse_mode=ParseMode.HTML,
    )
    callback.message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_movie_callback_returns_alert_when_service_fails(search_service: Mock) -> None:
    search_service.get_by_id.side_effect = RuntimeError("lookup failed")
    callback = Mock(data="movie:42", message=Mock())
    callback.answer = AsyncMock()

    await info_handlers.show_movie_details(callback)

    callback.answer.assert_awaited_once_with(
        "Не удалось получить информацию о фильме.",
        show_alert=True,
        parse_mode=ParseMode.HTML,
    )
