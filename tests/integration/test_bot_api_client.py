"""Integration tests for bot handlers calling the in-process API."""

from importlib import import_module
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from aiogram.types import CallbackQuery, Message

from src.backend.main import app
from src.core.contracts import Movie
from src.bot.api_client import SearchApiClient

info_router = import_module("src.bot.routers.info_router")
search_router = import_module("src.bot.routers.search_router")


@pytest.mark.asyncio
async def test_bot_handlers_use_the_fastapi_router(
    api_dependencies,
    seeded_movie: Movie,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as http_client:
        bot_api_client = SearchApiClient(http_client=http_client)
        monkeypatch.setattr(search_router, "api_client", bot_api_client)
        monkeypatch.setattr(info_router, "api_client", bot_api_client)

        message = AsyncMock(spec=Message)
        message.text = "фильм про космос"
        message.answer = AsyncMock()
        await search_router.search_by_text(message)

        message.answer.assert_awaited_once()
        search_reply = message.answer.await_args.kwargs
        assert seeded_movie.title in search_reply["text"]
        assert search_reply["reply_markup"].inline_keyboard[0][0].callback_data == (
            f"movie:{seeded_movie.id}"
        )

        details_message = AsyncMock(spec=Message)
        details_message.answer = AsyncMock()
        callback = Mock(spec=CallbackQuery)
        callback.data = f"movie:{seeded_movie.id}"
        callback.message = details_message
        callback.answer = AsyncMock()

        await info_router.show_movie_details(callback)

        callback.answer.assert_awaited_once_with()
        details_message.answer.assert_awaited_once()
        assert seeded_movie.title in details_message.answer.await_args.args[0]
        assert seeded_movie.description in details_message.answer.await_args.args[0]
